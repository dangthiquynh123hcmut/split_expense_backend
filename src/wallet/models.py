from django.conf import settings
from django.db import models

from utils.enums import CurrencyEnum
from utils.functions.generate_code_transfer import generate_code_transfer
from utils.models import BaseModel


class Wallet(BaseModel):
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="user_uid",
        related_name="wallet_fk_user",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        null=False,
        blank=False,
    )
    currency = models.CharField(
        max_length=20,
        choices=CurrencyEnum.choices,
        default=CurrencyEnum.VND,
    )
    account_number = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        unique=True,
    )

    @property
    def phone_number(self):
        return self.user.phone_number

    def save(self, *args, **kwargs):
        if not self.account_number:
            self.account_number = self.user.phone_number[-10:]
        super().save(*args, **kwargs)


class Transaction(BaseModel):
    from_wallet = models.ForeignKey(
        to="wallet.Wallet",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="from_wallet_uid",
        related_name="transaction_fk_from_wallet",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    to_wallet = models.ForeignKey(
        to="wallet.Wallet",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="to_wallet_uid",
        related_name="transaction_fk_to_wallet",
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
    description = models.CharField(
        max_length=127,
        blank=True,
        null=True,
    )
    currency = models.CharField(
        max_length=20,
        choices=CurrencyEnum.choices,
        default=CurrencyEnum.VND,
    )
    code = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_code_transfer(user=self.from_wallet.user)
        super().save(*args, **kwargs)


class WalletDeposit(BaseModel):
    wallet = models.ForeignKey(
        to="wallet.Wallet",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="wallet_uid",
        related_name="wallet_deposit_fk_wallet",
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
    currency = models.CharField(
        max_length=20,
        choices=CurrencyEnum.choices,
        default=CurrencyEnum.VND,
    )
    date = models.DateTimeField(
        auto_now_add=True,
    )
    code = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_code_transfer(user=self.wallet.user)
        return super().save(*args, **kwargs)
