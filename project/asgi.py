
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path
from apps.realtime.consumers import ProgressConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter([re_path(r"^ws/progress$", ProgressConsumer.as_asgi())])
    ),
})
