from django.urls import re_path

from . import consumers


websocket_urlpatterns = [
    re_path(r"chat/group/(?P<group_uid>[^/]+)/$", consumers.ChatConsumer.as_asgi()),
]
