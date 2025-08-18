from django.conf import settings
from django.db import models

from utils.enums import CurrencyEnum, StatusEnum, TransactionTypeEnum
from utils.models import BaseModel


class Wallet(BaseModel):
    owner = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="owner_uid",
        related_name="wallet_fk_owner",
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
        default=CurrencyEnum.USD,
    )


class Transaction(BaseModel):
    wallet = models.ForeignKey(
        to="wallet.Wallet",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="wallet_uid",
        related_name="transaction_fk_wallet",
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
    type = models.CharField(
        max_length=20,
        choices=TransactionTypeEnum.choices,
        default=TransactionTypeEnum.DEPOSIT,
    )
    status = models.CharField(
        max_length=20,
        choices=StatusEnum.choices,
        default=StatusEnum.ACTIVE,
    )
    description = models.CharField(
        max_length=127,
        blank=True,
        null=True,
    )
