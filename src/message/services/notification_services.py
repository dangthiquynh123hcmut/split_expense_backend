from group.queries import Query as GroupQuery
from message.orm.notification_queries import NotificationORM
from utils.types import TUser


class NotificationService:
    def __init__(self):
        self.notification_orm = NotificationORM()
        self.group_query = GroupQuery()

    def list_notifications(self, user: TUser):
        return self.notification_orm.list_notifications(user=user)
