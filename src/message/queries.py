from uuid import UUID

from channels.db import database_sync_to_async
from django.utils import timezone

from attachment.models import Attachment
from group.models import Group
from message.models import Message
from message.schemas.request import MessageFilter, MessageIn
from utils.enums import StatusEnum, StatusMessageEnum
from utils.types import TUser

from .models import MessageAttachment


class Query:
    @staticmethod
    @database_sync_to_async
    def create_message(user: TUser, group: Group, message: MessageIn):
        return Message.objects.create(
            content=message.content, user=user, group=group, status=StatusEnum.ACTIVE
        )

    @staticmethod
    def list_messages(group: Group, filters: MessageFilter):
        queryset = Message.objects.filter(group=group)

        if filters and filters.search:
            queryset = queryset.filter(filters.filter_search(filters.search))
        return queryset

    @staticmethod
    @database_sync_to_async
    def get_message(message_uid: UUID):
        return Message.objects.select_related("group").filter(uid=message_uid).first()

    @staticmethod
    @database_sync_to_async
    def update_message(message: Message, data: MessageIn):
        message.content = data.content
        message.updated_at = timezone.now()
        message.status = StatusMessageEnum.EDITED
        message.save()
        return message

    @staticmethod
    @database_sync_to_async
    def delete_message(message: Message):
        message.status = StatusEnum.DELETED
        message.content = "message deleted"
        message.updated_at = timezone.now()
        message.save()
        return

    @staticmethod
    @database_sync_to_async
    def add_attachment(message: Message, attachment: Attachment):
        MessageAttachment.objects.create(message=message, attachment=attachment)
        return
