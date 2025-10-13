from django.urls import path
from .views import upload, list_uploads, delete_upload

urlpatterns = [
    path("uploads/upload", upload),
    path("uploads/list", list_uploads),
    path("uploads/<int:doc_id>", delete_upload),
]
