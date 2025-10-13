
import io, os
from django.views.decorators.csrf import csrf_exempt 
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from django.db import transaction
from .models import Document, Chunk
from pdfminer.high_level import extract_text
from markdown_it import MarkdownIt
from django.conf import settings
from rest_framework import status

####
import logging
log = logging.getLogger("docuchat.uploads")
####

@api_view(['GET'])
def list_uploads(request):
    """
    Son yüklenen belgeleri döndürür.
    İleride auth açarsan owner filtresi ekleyebilirsin.
    """
    qs = Document.objects.order_by('-id')[:200]  # son 200 kaydı getir
    data = [{
        "id": d.id,
        "filename": d.filename,
        "created_at": getattr(d, "created_at", None),  # alan yoksa None döner
        "size": getattr(d, "size", None),              # varsa doldurulur
    } for d in qs]
    return Response({"items": data})

@api_view(['DELETE'])
def delete_upload(request, doc_id: int):
    doc = Document.objects.filter(id=doc_id).first()
    if not doc:
        return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
    with transaction.atomic():
        Chunk.objects.filter(document=doc).delete()  # CASCADE varsa şart değil
        doc.delete()
    return Response({"status": "ok", "deleted": doc_id}, status=status.HTTP_200_OK)

def extract_text_from_file(fobj, name: str) -> str:
    ext = os.path.splitext(name.lower())[1]
    data = fobj.read()
    if not data:
        return ""
    if ext == '.pdf':
        return extract_text(io.BytesIO(data)) or ""
    elif ext in ['.md', '.markdown']:
        md = MarkdownIt()
        return md.render(data.decode('utf-8', 'ignore')) or ""
    else:
        return data.decode('utf-8', 'ignore') or ""

def chunk_text(text: str, size: int, overlap: int):
    chunks = []
    s = 0
    while s < len(text):
        e = min(len(text), s + size)
        chunks.append(text[s:e])
        s = e - overlap if e - overlap > s else e
    return chunks

@api_view(['POST'])    
@parser_classes([MultiPartParser])
def upload(request):
    files = request.FILES.getlist('files')
    log.info("Upload received count=%d names=%s", len(files), [f.name for f in files])#dosyalar geliyor mu bi bakalim yaw
    saved = []
    with transaction.atomic():
        for f in files:
            text = extract_text_from_file(f.file, f.name)
            doc = Document.objects.create(filename=f.name, text=text)
            saved.append(f.name)
            for idx, ch in enumerate(chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)):
                Chunk.objects.create(document=doc, index=idx, text=ch)
    return Response({"status": "ok", "files": saved})
