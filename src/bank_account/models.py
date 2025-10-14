import uuid

from django.db import models

from utils.enums import BankEnum, CurrencyEnum
from utils.functions.generate_code_transfer import generate_code_transfer


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


class BankAccountWithDraw(models.Model):
    bank_account = models.ForeignKey(
        to="bank_account.BankAccount",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="bank_account_uid",
        related_name="bank_account_withdraw_fk_bank_account",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    wallet = models.ForeignKey(
        to="wallet.Wallet",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="wallet_uid",
        related_name="bank_account_withdraw_fk_wallet",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        null=False,
        blank=False,
    )
    code = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )
    date = models.DateTimeField(
        auto_now_add=True,
    )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_code_transfer(user=self.bank_account.user)
        return super().save(*args, **kwargs)
