from django.conf import settings
from django.db import models

from utils.enums import NotificationTypeEnum, StatusMessageEnum
from utils.models import BaseModel


class Message(BaseModel):
    content = models.CharField(null=True, blank=False)
    attachment = models.ManyToManyField(
        to="attachment.Attachment",
        through="message.MessageAttachment",
        related_name="message_fk_attachment",
        db_constraint=True,
        db_index=True,
        blank=True,
    )
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
        choices=StatusMessageEnum.choices,
        default=StatusMessageEnum.ACTIVE,
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

    class Meta:
        ordering = ["-created_at"]


class MessageAttachment(BaseModel):
    message = models.ForeignKey(
        to="message.Message",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="message_uid",
        related_name="message_attachment_fk_message",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    attachment = models.ForeignKey(
        to="attachment.Attachment",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="attachment_uid",
        related_name="message_attachment_fk_attachment",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )

    class Meta:
        indexes = [
            models.Index(fields=["message", "attachment"]),
        ]


class Notification(BaseModel):
    from_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="from_user_uid",
        related_name="notification_fk_from_user",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    content = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=NotificationTypeEnum.choices)
    related_uid = models.UUIDField(null=True, blank=True)
    to_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="received_notifications"
    )

    class Meta:
        ordering = ["-created_at"]
