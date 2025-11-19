from uuid import UUID

from channels.layers import get_channel_layer
from django.utils import timezone

from exceptions.group import GroupNotFound
from group.queries import Query as GroupQuery
from message.orm.message_queries import MessageORM
from message.schemas.request import MessageFilter, MessageIn
from utils.exceptions import GetIsDenied
from utils.types import TUser


class MessageService:
    def __init__(self):
        self.message_orm = MessageORM()
        self.group_query = GroupQuery()
        self.channel_layer = get_channel_layer()

    async def sent_message(self, user: TUser, group_uid: UUID, message: MessageIn):
        group = await self.group_query.get_group(group_uid=group_uid)
        result = await self.message_orm.create_message(
            user=user, group=group, message=message
        )

        if result:
            await self._send_ws_event(
                group_uid=group_uid,
                message_type="multi_chat_message",
                user=user,
                uid=result.uid,
                content=result.content,
                created_at=result.created_at,
            )
        return result

    def list_messages(self, user: TUser, group_uid: UUID, filters: MessageFilter):
        group = self.group_query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.group_query.get_group_has_user(user=user, group=group)
        if not member:
            raise GetIsDenied
        return self.message_orm.list_messages(group=group, filters=filters)

    async def update_message(self, user: TUser, message_uid: UUID, data: MessageIn):
        message = await self.message_orm.get_message(message_uid=message_uid)

        updated_message = await self.message_orm.update_message(
            message=message, data=data
        )
        await self._send_ws_event(
            group_uid=message.group.uid,
            message_type="multi_chat_message",
            user=user,
            uid=message_uid,
            content=data.content,
            updated_at=updated_message.updated_at,
        )
        return updated_message

    async def delete_message(self, user: TUser, message_uid: UUID):
        message = await self.message_orm.get_message(message_uid=message_uid)
        await self.message_orm.delete_message(message=message)
        await self._send_ws_event(
            group_uid=message.group.uid,
            message_type="multi_chat_message",
            user=user,
            uid=message_uid,
            content="message deleted",
            updated_at=timezone.now(),
        )
        return True

    # ---------------- SINGLE HELPER ---------------- #

    async def _send_ws_event(
        self,
        group_uid: UUID,
        message_type: str,
        user: TUser,
        uid: UUID,
        content: str,
        created_at=None,
        updated_at=None,
    ):
        payload = {
            "uid": str(uid),
            "user": {
                "uid": str(user.uid),
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
            },
        }
        if content is not None:
            payload["content"] = content
        if created_at is not None:
            payload["created_at"] = created_at.isoformat()
        if updated_at is not None:
            payload["updated_at"] = updated_at.isoformat()

        await self.channel_layer.group_send(
            f"chat_{group_uid}",
            {
                "type": message_type,
                "group_uid": str(group_uid),
                "message": payload,
            },
        )
