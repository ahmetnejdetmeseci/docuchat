
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.core.urls')),
    path('api/', include('apps.uploads.urls')),
    path('api/', include('apps.rag.urls')),
    path('api/', include('apps.uploads.urls')),
]
