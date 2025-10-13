from django.urls import path
from .views import ask, llm_health

urlpatterns = [
    path("chat/ask", ask),
    path("llm/health", llm_health),
]
