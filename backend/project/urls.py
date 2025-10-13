from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def health(_):
    return JsonResponse({"ok": True})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health", health),
    path("api/", include("apps.uploads.urls")),
    path("api/", include("apps.rag.urls")),
    path("api/", include("apps.agent.urls")),
]
