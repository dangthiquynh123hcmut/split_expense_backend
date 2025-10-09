import uuid
from enum import unique

from django.db import models

from utils.types import User


@unique
class AttachmentType(models.TextChoices):
    GROUP = "GROUP", "Group"
    USER = "USER", "User"
    EXPENSE = "EXPENSE", "Expense"
    MESSAGE = "MESSAGE", "Message"
    OTHER = "OTHER", "Other"


class Attachment(models.Model):
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    type = models.CharField(
        max_length=255,
        choices=AttachmentType.choices,
        null=False,
        blank=False,
        default=AttachmentType.OTHER,
    )

    # Metadata
    original_name = models.TextField()
    hashed_name = models.TextField()

    size = models.IntegerField()
    content_type = models.CharField(max_length=255)

    # Storage
    bucket = models.CharField(max_length=255)
    directory = models.TextField()

    is_public = models.BooleanField(default=True)
    public_url = models.URLField()

    created_at = models.DateTimeField(auto_now_add=True)

    is_completed = models.BooleanField(default=False)

    owner = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        to_field="uid",
        db_column="owner_uid",
        related_name="attachment_fk_owner",
        db_constraint=True,
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        self.directory = self.type.lower()
        return super().save(*args, **kwargs)
