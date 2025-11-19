from django.urls import re_path

from utils.services.websocket.consumers import MultiGroupChatConsumer


websocket_urlpatterns = [
    re_path(r"ws/chat/$", MultiGroupChatConsumer.as_asgi()),
]
