"""
ASGI config for split_expense project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os

import django
from django.core.asgi import get_asgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "split_expense_system.settings")
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.urls import re_path  # noqa: E402

from utils.services.websocket.consumers import ChatConsumer  # noqa: E402
from utils.services.websocket.middleware import WebSocketJWTAuthMiddleware  # noqa: E402


django_asgi_app = get_asgi_application()

websocket_urlpatterns = [
    re_path(r"ws/chat/group/(?P<group_uid>[^/]+)/$", ChatConsumer.as_asgi()),
]

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": WebSocketJWTAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
