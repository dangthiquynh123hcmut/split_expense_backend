from django.conf import settings
from django.db import models

from event.models import Event
from utils.enums import CurrencyEnum, SplitTypeEnum, StatusEnum
from utils.functions.remove_accents import remove_accents
from utils.models import BaseModel


class Expense(BaseModel):
    name = models.CharField(max_length=255)
    name_no_accent = models.CharField(max_length=255, blank=True, editable=False)

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
    total_amount = models.FloatField(null=False, blank=False)

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
    updated_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        to_field="uid",
        db_column="updated_by_uid",
        related_name="expense_fk_updated_by",
        db_constraint=True,
        db_index=True,
        null=True,
        blank=True,
    )
    split_type = models.CharField(
        max_length=20,
        choices=SplitTypeEnum.choices,
        default=SplitTypeEnum.EQUAL,
    )
    note = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    expense_date = models.DateTimeField(null=False, blank=False)
    end_date = models.DateTimeField(null=True, blank=True)
    receipt_url = models.ManyToManyField(
        to="attachment.Attachment",
        through="expense.ExpenseAttachment",
        related_name="expense_fk_receipt_url",
        db_constraint=True,
        db_index=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=StatusEnum.choices,
        default=StatusEnum.ACTIVE,
    )

    def save(self, *args, **kwargs):
        if self.name:
            self.name_no_accent = remove_accents(self.name)
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class ExpenseAttachment(BaseModel):
    # relation 1:N
    expense = models.ForeignKey(
        to="expense.Expense",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="expense_uid",
        related_name="expense_attachment_fk_expense",
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
        related_name="expense_attachment_fk_attachment",
        db_constraint=True,
        db_index=True,
        blank=False,
    )

    class Meta:
        indexes = [
            models.Index(fields=["expense", "attachment"]),
        ]
        unique_together = (("expense", "attachment"),)


class UserSharesInExpense(BaseModel):
    expense = models.ForeignKey(
        to="expense.Expense",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="expense_uid",
        related_name="user_shares_in_expense_fk_expense",
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
        related_name="user_shares_in_expense_fk_user",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=False, blank=False
    )  # spending >0

    deleted = models.CharField(
        max_length=20,
        choices=StatusEnum.choices,
        default=StatusEnum.ACTIVE,
    )
    receiver_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, default=0
    )  # always >=0

    class Meta:
        indexes = [
            models.Index(fields=["expense", "user"]),
        ]
        unique_together = (("expense", "user"),)
