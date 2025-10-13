import uuid

from django.db import models

from utils.enums import BankEnum, CurrencyEnum


class BankAccount(models.Model):
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        to="authenticate.User",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="user_uid",
        related_name="bank_account_fk_user",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    bank_name = models.CharField(
        max_length=50, choices=BankEnum.choices, null=False, blank=False
    )
    account_number = models.CharField(max_length=30, null=False, blank=False)
    currency = models.CharField(
        max_length=20, choices=CurrencyEnum.choices, default=CurrencyEnum.VND
    )

    class Meta:
        unique_together = ("bank_name", "account_number")
