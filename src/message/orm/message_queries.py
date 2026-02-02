from datetime import timedelta
from typing import Optional
from uuid import UUID

from channels.db import database_sync_to_async
from django.db.models import Count, Max, OuterRef, Q, Subquery
from django.utils import timezone

from attachment.models import Attachment
from group.models import Group
from message.models import Message, MessageAttachment
from message.schemas.request import MessageFilter, MessageIn
from utils.enums import StatusEnum, StatusMessageEnum
from utils.functions.get_last_month import get_last_month
from utils.types import TUser


class MessageORM:
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

    @staticmethod
    def message_management():
        start_last_month, end_last_month = get_last_month(timezone.now())
        start_this_month = timezone.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return Message.objects.filter(
            created_at__gte=start_this_month
        ).count(), Message.objects.filter(
            created_at__gte=start_last_month, created_at__lte=end_last_month
        ).count()

    @staticmethod
    def total_messages_today():
        today = timezone.now().date()
        return Message.objects.filter(
            created_at__date=today
        ).count(), Message.objects.filter(
            created_at__date=today - timedelta(days=1)
        ).count()

    @staticmethod
    def total_attachments():
        start_last_month, end_last_month = get_last_month(timezone.now())
        start_this_month = timezone.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return MessageAttachment.objects.filter(
            created_at__gte=start_this_month,
        ).count(), MessageAttachment.objects.filter(
            created_at__gte=start_last_month, created_at__lte=end_last_month
        ).count()

    @staticmethod
    def list_messages_group():
        # Get the last message for each group
        last_message_subquery = (
            Message.objects.filter(
                group=OuterRef("pk"),
                status=StatusEnum.ACTIVE,
            )
            .order_by("-created_at")
            .values("content")[:1]
        )

        return (
            Group.objects.annotate(
                total_members=Count(
                    "group_member_fk_group",
                    filter=Q(group_member_fk_group__status=StatusEnum.ACTIVE),
                ),
                total_messages=Count(
                    "message_fk_group",
                    filter=Q(message_fk_group__status=StatusEnum.ACTIVE),
                ),
                total_messages_unread=Count(
                    "message_fk_group",
                    filter=Q(message_fk_group__status=StatusEnum.ACTIVE),
                ),
                last_message_content=Subquery(last_message_subquery),
                last_message=Max("message_fk_group__created_at"),
            )
            .filter(status=StatusEnum.ACTIVE)
            .order_by("-last_message")
        )

    @staticmethod
    def get_messages_in_group(group_uid: UUID, filter: Optional[MessageFilter] = None):
        queryset = Message.objects.filter(
            group__uid=group_uid, status=StatusEnum.ACTIVE
        )
        if filter:
            queryset = queryset.filter(filter.get_filter_expression())
        return queryset.order_by("-created_at")
