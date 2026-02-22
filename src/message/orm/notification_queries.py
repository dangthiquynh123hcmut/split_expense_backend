from datetime import timedelta
from uuid import UUID

from django.utils.timezone import now

from message.models import Notification
from my_admin.schemas.request import FilterNotificationSchema
from utils.enums import NotificationTypeEnum
from utils.functions.get_last_month import get_last_month
from utils.types import TUser


class NotificationORM:
    @staticmethod
    def create_notification(
        from_user: TUser,
        related_uid: UUID,
        content: str,
        type: NotificationTypeEnum,
        to_users: list[TUser],
        is_broadcast: bool = False,
    ):
        notification = Notification.objects.create(
            from_user=from_user,
            related_uid=related_uid,
            content=content,
            type=type,
            is_broadcast=is_broadcast,
        )
        notification.to_users.add(*to_users)
        return notification

    @staticmethod
    def list_notifications(user: TUser):
        return Notification.objects.filter(to_users=user)

    @staticmethod
    def total_notifications():
        start_last_month, end_last_month = get_last_month(now())
        start_this_month = now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return Notification.objects.filter(
            created_at__gte=start_this_month
        ).count(), Notification.objects.filter(
            created_at__gte=start_last_month, created_at__lte=end_last_month
        ).count()

    @staticmethod
    def total_notifications_today():
        today = now().date()
        return Notification.objects.filter(
            created_at__date=today
        ).count(), Notification.objects.filter(
            created_at__date=today - timedelta(days=1)
        ).count()

    @staticmethod
    def list_notifications_admin(filter: FilterNotificationSchema):
        notifications = Notification.objects.all()
        if filter.search:
            notifications = notifications.filter(content__icontains=filter.search)
        if filter.type:
            notifications = notifications.filter(type=filter.type)
        return notifications

    @staticmethod
    def delete_notification(notification_uid: UUID):
        return Notification.objects.filter(uid=notification_uid).delete()
