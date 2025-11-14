import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from group.models import Group, GroupMember
from message.models import Message
from utils.enums import StatusEnum, StatusMessageEnum
from utils.services.firebase_cm.fcm_service import FCMService


logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_uid = None
        self.group_name = None
        self.user = None
        self.fcm_service = FCMService()

    async def connect(self):
        try:
            self.group_uid = self.scope["url_route"]["kwargs"]["group_uid"]
            self.room_group_name = f"chat_{self.group_uid}"
            self.user = self.scope.get("user")

            if not self.user or not getattr(self.user, "is_authenticated", False):
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
            and getattr(self.user, "is_authenticated", False)
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

    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming messages from client."""
        if not text_data:
            return
        try:
            payload = json.loads(text_data)
        except ValueError:
            return

        msg_type = payload.get("type", "message")
        content = (payload.get("content") or payload.get("text") or "").strip()
        if msg_type != "message" or not content:
            return

        # Persist message
        message_obj = await self.save_message(content)

        message_data = {
            "id": str(message_obj.uid),
            "content": message_obj.content,
            "user": {
                "uid": str(self.user.uid),
                "full_name": self.user.full_name,
            },
            "group_uid": self.group_uid,
            "created_at": message_obj.created_at.isoformat(),
            "status": message_obj.status,
        }

        # Broadcast to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat_message", "message": message_data},
        )

        # Send FCM notification to offline members
        device_tokens = await self.get_recipient_device_tokens(
            exclude_user_uid=str(self.user.uid)
        )
        if device_tokens:
            self.fcm_service.send_chat_message_notification(
                device_tokens=device_tokens,
                title=f"{self.user.full_name}",
                body=content[:60],
                data={
                    "group_uid": self.group_uid,
                    "message_id": str(message_obj.uid),
                    "type": "chat_message",
                },
            )

    async def system_message(self, event):
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
        await self.send(text_data=json.dumps({"type": "message", **event["message"]}))

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
            content=content,
            user=self.user,
            group=group,
            status=StatusMessageEnum.ACTIVE,
        )

    @database_sync_to_async
    def get_recipient_device_tokens(self, exclude_user_uid: str):
        group = Group.objects.get(uid=self.group_uid)
        member_qs = (
            GroupMember.objects.filter(group=group, status=StatusEnum.ACTIVE)
            .exclude(user_id=exclude_user_uid)
            .select_related("user")
        )
        tokens = [
            m.user.fcm_token for m in member_qs if getattr(m.user, "fcm_token", None)
        ]
        return list(dict.fromkeys(tokens))  # de-duplicate while preserving order
