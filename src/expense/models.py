from django.conf import settings
from django.db import models

from event.models import Event
from utils.enums import CurrencyEnum, SplitTypeEnum, StatusEnum
from utils.models import BaseModel


class Expense(BaseModel):
    name = models.CharField(max_length=255)
    ordinal = models.IntegerField(null=False, blank=False)

    event = models.ForeignKey(
        to=Event,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="event_uid",
        related_name="expense_fk_event",
        db_constraint=True,
        null=False,
        blank=False,
    )
    currency = models.CharField(
        max_length=20,
        choices=CurrencyEnum.choices,
        default=CurrencyEnum.USD,
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    paid_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        to_field="uid",
        db_column="paid_by_uid",
        related_name="expense_fk_paid_by",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        to_field="uid",
        db_column="creator_uid",
        related_name="expense_fk_creator",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    split_type = models.CharField(
        max_length=20,
        choices=SplitTypeEnum.choices,
        default=SplitTypeEnum.EQUAL,
    )
    expense_date = models.DateField(null=False, blank=False)
    remaind_at = models.DateTimeField(null=False, blank=False)
    receipt_url = models.URLField(max_length=500, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class UserParticipatesInExpense(BaseModel):
    event = models.ForeignKey(
        to="event.Event",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="event_uid",
        related_name="expense_participant_fk_event",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    ordinal = models.IntegerField(null=False, blank=False, default=0)
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="user_uid",
        related_name="expense_participant_fk_user",
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
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=False, blank=False
    )
    paid_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=False, blank=False
    )
    paid_at = models.DateTimeField(null=True, blank=True)
