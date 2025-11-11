from uuid import UUID

from message.models import Notification
from utils.enums import NotificationTypeEnum
from utils.types import TUser


class NotificationORM:
    @staticmethod
    def create_notification(
        user: TUser,
        related_uid: UUID,
        content: str,
        type: NotificationTypeEnum,
        to_users: list[TUser],
    ):
        notification = Notification.objects.create(
            from_user=user, related_uid=related_uid, content=content, type=type
        )
        notification.to_users.add(*to_users)
        return notification

    @staticmethod
    def list_notifications(user: TUser):
        return Notification.objects.filter(to_users=user)
