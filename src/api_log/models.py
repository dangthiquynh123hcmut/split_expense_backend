from django.conf import settings
from django.db import models

from utils.models import BaseModel


class ApiLog(BaseModel):
    path = models.CharField(max_length=255)
    method_type = models.CharField(max_length=10)
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        to_field="uid",
        db_column="user_uid",
        related_name="api_log_fk_user",
        db_constraint=True,
        db_index=True,
        null=True,
        blank=True,
    )
    status_code = models.IntegerField()
    response_time = models.FloatField()
    log_message = models.TextField(blank=True, null=True)
