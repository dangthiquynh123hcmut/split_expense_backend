import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from group.models import Group, GroupMember
from utils.enums import StatusEnum

from .models import Message


logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.group_uid = self.scope["url_route"]["kwargs"]["group_uid"]
            self.room_group_name = f"chat_{self.group_uid}"
            self.user = self.scope["user"]

            if not self.user.is_authenticated:
                await self.close(code=4003)
                return

            if not await self.is_group_member():
                await self.close(code=4003)
                return

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "system_message",
                    "message": f"{self.user.full_name} has joined the chat",
                    "user": {
                        "uid": str(self.user.uid),
                        "full_name": self.user.full_name,
                        "email": self.user.email,
                    },
                    "is_system": True,
                },
            )

        except Exception as e:
            logger.error(f"WebSocket connection error: {str(e)}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        if (
            hasattr(self, "room_group_name")
            and hasattr(self, "user")
            and self.user.is_authenticated
        ):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "system_message",
                    "message": f"{self.user.full_name} has left the chat",
                    "is_system": True,
                },
            )

            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def system_message(self, event):
        """Handle system join/leave notifications sent via group_send."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "system",
                    "message": event.get("message"),
                    "user": event.get("user"),
                    "is_system": True,
                }
            )
        )

    async def chat_message(self, event):
        await self._send_message("message", event["message"])

    async def message_updated(self, event):
        await self._send_message("message_updated", event["message"])

    async def message_deleted(self, event):
        await self._send_message("message_deleted", event["message"])

    async def _send_message(self, message_type: str, data: dict):
        await self.send(text_data=json.dumps({"type": message_type, **data}))

    @database_sync_to_async
    def is_group_member(self):
        group = Group.objects.get(uid=self.group_uid)
        return GroupMember.objects.filter(
            group=group, user=self.user, status=StatusEnum.ACTIVE
        ).exists()

    @database_sync_to_async
    def save_message(self, content: str):
        group = Group.objects.get(uid=self.group_uid)
        return Message.objects.create(
            content=content, user=self.user, group=group, status=StatusEnum.ACTIVE
        )
