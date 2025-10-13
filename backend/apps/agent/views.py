import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.http import HttpResponse
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from markdown_it import MarkdownIt

from apps.uploads.models import Task, Report
from apps.rag.views import retrieve, best_sentence_for_chunk

log = logging.getLogger("docuchat.agent")


def ws_group(tenant_name: str, task_id: int) -> str:
    return f"tenant_{tenant_name}_task_{task_id}"


def _summarize(chunks, question: str) -> str:
    lines = []
    for c in chunks:
        q = best_sentence_for_chunk(question, c.get("text") or "") or c.get("snippet") or ""
        if q:
            lines.append(f"- {q}")
    if not lines:
        lines.append("- No relevant chunks found in your tenant documents.")
    return "\n".join(lines)


@api_view(["POST"])
def create_task(request):
    tenant = request.tenant
    topic = (request.data.get("topic") or "").strip()
    if not topic:
        return Response({"error": "topic required"}, status=status.HTTP_400_BAD_REQUEST)

    # Task oluştur
    t = Task.objects.create(
        tenant=tenant,
        topic=topic,
        status="queued",
        group=ws_group(tenant.name, 0),
    )
    t.group = ws_group(tenant.name, t.id)
    t.save()

    ch = get_channel_layer()

    def send(tp, data):
        async_to_sync(ch.group_send)(
            t.group,
            {"type": "agent.message", "payload": {"type": tp, "data": data}},
        )

    # Adım 1: plan + search
    t.status = "running"
    t.save()
    send("status", {"status": "running"})
    send("plan", {"msg": "Step 1/3: Searching docs…"})
    chunks = retrieve(tenant, topic, top_k=int(getattr(settings, "TOP_K", 4)))
    t.steps.append({"type": "plan", "msg": f"retrieved chunks: {len(chunks)}"})
    t.save()

    # Adım 2: summarize
    send("plan", {"msg": "Step 2/3: Summarizing chunks…"})
    summary = _summarize(chunks, topic)
    t.steps.append({"type": "plan", "msg": "summarized"})
    t.save()

    # Adım 3: write report
    send("plan", {"msg": "Step 3/3: Writing Markdown report…"})
    report_md = f"# Research Report\n\n**Topic:** {topic}\n\n## Findings\n{summary}\n"
    rpt = Report.objects.create(
        tenant=tenant,
        title=f"Report: {topic}",
        content_md=report_md,
    )
    t.report = rpt
    t.status = "done"
    t.save()

    # Rapor URL'si
    report_url = f"/api/agent/tasks/{t.id}/report?tenant={tenant.name}"

    # WS 'done' içinde raporu ve linki de ilet
    send("done", {"status": "done", "report_md": report_md, "report_url": report_url})

    # HTTP cevapta da linki ver
    return Response(
        {"id": t.id, "group": t.group, "status": t.status, "report_url": report_url}
    )


@api_view(["GET"])
def get_task(request, task_id: int):
    tenant = request.tenant
    t = Task.objects.filter(tenant=tenant, id=task_id).select_related("report").first()
    if not t:
        return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(
        {
            "id": t.id,
            "topic": t.topic,
            "status": t.status,
            "group": t.group,
            "steps": t.steps,
            "report_md": t.report.content_md if t.report else "",
            "report_url": f"/api/agent/tasks/{t.id}/report?tenant={tenant.name}" if t.report else None,

        }
    )


# HTML olarak raporu render eden basit sayfa
def view_report(request, task_id: int):
    tenant = getattr(request, "tenant", None)
    t = Task.objects.filter(tenant=tenant, id=task_id).select_related("report").first()
    if not t or not t.report:
        return HttpResponse("<h1>Report not found</h1>", status=404)

    md = MarkdownIt()
    html = md.render(t.report.content_md or "")
    page = f"""<!doctype html><html><head><meta charset="utf-8">
      <title>Report {task_id}</title>
      <style>
        body{{font-family:ui-sans-serif,system-ui;margin:20px}}
        pre,code{{background:#f3f4f6;padding:2px 4px;border-radius:4px}}
        a{{text-decoration:none;color:#2563eb}}
      </style>
    </head><body>
      <a href="/">← Back</a>
      {html}
    </body></html>"""
    return HttpResponse(page)
