
from django.urls import path
from .views import ask, llm_health
#llm is connected or not I just wnated to see it.
urlpatterns = [ path('chat/ask', ask),  path('llm/health', llm_health) ]
