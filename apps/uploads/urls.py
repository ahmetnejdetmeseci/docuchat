
from django.urls import path
from .views import upload, list_uploads, delete_upload
urlpatterns = [ path('upload', upload), path('upload/list', list_uploads), path('upload/<int:doc_id>', delete_upload), ]
