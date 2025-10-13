import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from apps.agent.consumers import AgentConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django_app = get_asgi_application()

websocket_urlpatterns = [
    path("ws/agent/<str:group>/", AgentConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "http": django_app,
    "websocket": URLRouter(websocket_urlpatterns),
})
