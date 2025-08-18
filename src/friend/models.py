from django.conf import settings
from django.db import models

from utils.enums import FriendStatusEnum
from utils.models import BaseModel


class Friend(BaseModel):
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="user_uid",
        related_name="friend_fk_user",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    friend = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="friend_uid",
        related_name="friend_fk_friend",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    status = models.CharField(
        max_length=20,
        choices=FriendStatusEnum.choices,
        default=FriendStatusEnum.PENDING,
    )
