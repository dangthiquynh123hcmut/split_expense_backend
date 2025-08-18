from django.conf import settings
from django.db import models

from utils.models import BaseModel


class Event(BaseModel):
    name = models.CharField(max_length=255)
    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        to_field="uid",
        db_column="creator_uid",
        related_name="event_fk_creator",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    description = models.TextField(blank=True, null=True)
    event_start = models.DateField(null=False, blank=False)
    event_end = models.DateField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
