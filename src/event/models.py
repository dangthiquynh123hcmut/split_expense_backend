from django.conf import settings
from django.db import models

from utils.enums import CurrencyEnum, EventStatusEnum, StatusEnum
from utils.functions.remove_accents import remove_accents
from utils.models import BaseModel


class Event(BaseModel):
    name = models.CharField(max_length=255)
    name_no_accent = models.TextField(max_length=255, blank=True, editable=False)
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
    group = models.ForeignKey(
        to="group.Group",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="group_uid",
        related_name="event_fk_group",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    description = models.TextField(blank=True, null=True)
    event_start = models.DateField(null=False, blank=False)
    event_end = models.DateField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=EventStatusEnum.choices,
        default=EventStatusEnum.ACTIVE,
    )

    def save(self, *args, **kwargs):
        if self.name:
            self.name_no_accent = remove_accents(self.name)
        return super().save(*args, **kwargs)


class EventMember(BaseModel):
    event = models.ForeignKey(
        to="event.Event",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="event_uid",
        related_name="event_member_fk_event",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        to_field="uid",
        db_column="user_uid",
        related_name="event_member_fk_user",
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

    class Meta:
        unique_together = ("event", "user")


class EventMemberBalance(BaseModel):
    event = models.ForeignKey(
        to="event.Event",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="event_uid",
        related_name="event_member_balance_fk_event",
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
        related_name="event_member_balance_fk_user",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    currency = models.CharField(
        max_length=20,
        choices=CurrencyEnum.choices,
        default=CurrencyEnum.VND,
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = (("event", "user", "currency"),)
        indexes = [
            models.Index(fields=["event", "user"]),
        ]


class EventRestructureDebt(BaseModel):
    event = models.ForeignKey(
        to="event.Event",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="event_uid",
        related_name="event_restructure_debt_fk_event",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    debtor = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="debtor_uid",
        related_name="event_restructure_debt_fk_debtor",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    creditor = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="creditor_uid",
        related_name="event_restructure_debt_fk_creditor",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(
        max_length=20,
        choices=CurrencyEnum.choices,
        default=CurrencyEnum.VND,
    )
