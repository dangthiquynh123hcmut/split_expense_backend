import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache

from group.queries import Query as GroupQuery
from utils.services.firebase_cm.fcm_service import FCMService


logger = logging.getLogger(__name__)


class MultiGroupChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.group_query = GroupQuery()
        self.fcm_service = FCMService()

    @staticmethod
    def get_online_cache_key(user_uid: str) -> str:
        return f"user_online:{user_uid}"

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not getattr(self.user, "is_authenticated", False):
            await self.close(code=4003)
            return
        try:
            group_uids = await self.group_query.get_user_group_uids(self.user)

            for gid in group_uids:
                room = f"chat_{gid}"
                await self.channel_layer.group_add(room, self.channel_name)

            cache_key = self.get_online_cache_key(str(self.user.uid))
            cache.set(cache_key, True, timeout=None)

            await self.accept()

        except Exception as e:
            logger.error(f"MultiGroup connect error: {e}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        if self.user:
            cache_key = self.get_online_cache_key(str(self.user.uid))
            cache.delete(cache_key)

        group_uids = await self.group_query.get_user_group_uids(self.user)

        for gid in group_uids:
            room = f"chat_{gid}"
            await self.channel_layer.group_discard(room, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            payload = json.loads(text_data)
        except ValueError:
            return

        if payload.get("type") == "multi_chat_message":
            group_uid = payload.get("group_uid")
            content = (payload.get("content") or "").strip()
            groups = await self.group_query.get_user_group_uids(self.user)

            if not group_uid or not content:
                return
            group_uids = [str(gid.uid) for gid in groups]

            if str(group_uid) not in group_uids:
                return

            data = {
                "content": content,
                "user": {
                    "uid": str(self.user.uid),
                    "full_name": self.user.full_name,
                },
                "group_uid": group_uid,
            }
            await self.channel_layer.group_send(
                f"chat_{group_uid}", {"type": "multi_chat_message", "message": data}
            )

    async def multi_chat_message(self, event):
        await self.send(text_data=json.dumps({"type": "message", **event["message"]}))
