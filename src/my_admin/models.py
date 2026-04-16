from django.conf import settings
from django.db import models

from utils.models import BaseModel


class UserMonthlyActivity(BaseModel):
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="user_uid",
        related_name="user_monthly_activities",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    month = models.IntegerField(null=False)
    year = models.IntegerField(null=False)
    login_count = models.IntegerField(default=0, null=False)
    last_login_at = models.DateTimeField(null=True)

    class Meta:
        unique_together = ("user", "month", "year")


class RatingMonthly(BaseModel):
    user = models.OneToOneField(
        to="authenticate.User",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="user_uid",
        related_name="rating_monthlies",
        db_constraint=True,
        db_index=True,
        null=True,
        blank=True,
        unique=True,
    )
    rate = models.IntegerField(default=0, null=False)


class LoginHistory(BaseModel):
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="user_uid",
        related_name="login_histories",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    platform = models.CharField(max_length=50, null=True, blank=True)
    device_model = models.CharField(max_length=100, null=True, blank=True)
    os_version = models.CharField(max_length=50, null=True, blank=True)
    app_version = models.CharField(max_length=50, null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
