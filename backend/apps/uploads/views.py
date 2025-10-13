import io, os, logging
from django.db import transaction
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from pdfminer.high_level import extract_text
from markdown_it import MarkdownIt
from .models import Document, Chunk

log = logging.getLogger("docuchat.uploads")

def extract_text_from_file(fobj, name: str) -> str:
    ext = os.path.splitext(name.lower())[1]
    data = fobj.read()
    if not data:
        return ""
    if ext == ".pdf":
        return extract_text(io.BytesIO(data)) or ""
    elif ext in [".md", ".markdown"]:
        return data.decode("utf-8", "ignore")
    else:
        return data.decode("utf-8", "ignore")

def chunk_text(text: str, size: int, overlap: int):
    chunks = []
    s = 0
    n = len(text)
    if n == 0:
        return []
    while s < n:
        e = min(n, s + size)
        chunks.append(text[s:e])
        s = e - overlap if (e - overlap) > s else e
    return chunks

@api_view(["GET"])
def list_uploads(request):
    tenant = request.tenant
    qs = Document.objects.filter(tenant=tenant).order_by("-id")[:200]
    data = [{
        "id": d.id, "filename": d.filename,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "size": d.size
    } for d in qs]
    return Response({"items": data})

@api_view(["DELETE"])
def delete_upload(request, doc_id: int):
    tenant = request.tenant
    doc = Document.objects.filter(tenant=tenant, id=doc_id).first()
    if not doc:
        return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
    with transaction.atomic():
        Chunk.objects.filter(document=doc).delete()
        doc.delete()
    return Response({"status": "ok", "deleted": doc_id})

@api_view(["POST"])
@parser_classes([MultiPartParser])
def upload(request):
    tenant = request.tenant
    files = request.FILES.getlist("files")
    log.info("Upload received tenant=%s count=%d names=%s", tenant.name, len(files), [f.name for f in files])
    saved = []
    with transaction.atomic():
        for f in files:
            text = extract_text_from_file(f.file, f.name)
            doc = Document.objects.create(tenant=tenant, filename=f.name, text=text, size=f.size)
            saved.append(f.name)
            for idx, ch in enumerate(chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)):
                Chunk.objects.create(tenant=tenant, document=doc, index=idx, text=ch)
    return Response({"status": "ok", "files": saved})
