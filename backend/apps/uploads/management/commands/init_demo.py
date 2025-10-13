from django.core.management.base import BaseCommand
from apps.uploads.models import Tenant, Document, Chunk
from django.conf import settings

SEED_DOCS = {
    "python.md": "python version=3.11.x\nThis is a demo seed file for DocuChat.\nPython is commonly used for backend services.",
    "setup.txt": "Welcome to DocuChat Step 2 demo.\nYou can upload PDFs or Markdown files.",
}

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

class Command(BaseCommand):
    help = "Initialize demo tenant and seed docs if empty."

    def handle(self, *args, **kwargs):
        name = getattr(settings, "DEFAULT_TENANT", "demo")
        t, _ = Tenant.objects.get_or_create(name=name)
        if not Document.objects.filter(tenant=t).exists():
            for fn, content in SEED_DOCS.items():
                doc = Document.objects.create(tenant=t, filename=fn, text=content, size=len(content))
                for idx, ch in enumerate(chunk_text(content, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)):
                    Chunk.objects.create(tenant=t, document=doc, index=idx, text=ch)
            self.stdout.write(self.style.SUCCESS(f"Seeded {len(SEED_DOCS)} docs for tenant '{name}'"))
        else:
            self.stdout.write(self.style.WARNING(f"Tenant '{name}' already has documents; skipping seeding."))
