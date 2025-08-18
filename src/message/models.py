from django.conf import settings
from django.db import models

from utils.enums import StatusEnum
from utils.models import BaseModel


class Message(BaseModel):
    content = models.CharField(null=True, blank=False)
    ordinal = models.IntegerField(null=False, blank=False, default=0)
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="user_uid",
        related_name="message_fk_user",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    status = models.CharField(
        max_length=20,
        choices=StatusEnum.choices,
        default=StatusEnum.ACTIVE,
    )
    group = models.ForeignKey(
        to="group.Group",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="group_uid",
        related_name="message_fk_group",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
