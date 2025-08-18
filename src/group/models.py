from django.conf import settings
from django.db import models

from utils.enums import StatusEnum
from utils.models import BaseModel


class Group(BaseModel):
    name = models.CharField(max_length=255)
    leader = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        to_field="uid",
        db_column="leader_uid",
        related_name="group_fk_leader",
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
    avatar_url = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class GroupMember(BaseModel):
    group = models.ForeignKey(
        to="group.Group",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="group_uid",
        related_name="group_member_fk_group",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="user_uid",
        related_name="group_member_fk_user",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    joined_at = models.DateTimeField(auto_now=True, auto_now_add=False)
