import uuid

from django.db import models

from utils.enums import CurrencyEnum
from utils.functions.generate_code_transfer import generate_code_transfer
from utils.models import BaseModel


class Transaction(BaseModel):
    group = models.ForeignKey(
        to="group.Group",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="group_uid",
        related_name="transaction_fk_group",
        db_constraint=True,
        db_index=True,
        null=True,
        blank=True,
    )
    from_user = models.ForeignKey(
        to="authenticate.User",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="from_user_uid",
        related_name="transaction_fk_from_user",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    to_user = models.ForeignKey(
        to="authenticate.User",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="to_user_uid",
        related_name="transaction_fk_to_user",
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

    event = models.ForeignKey(
        to="event.Event",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="event_uid",
        related_name="transaction_fk_event",
        db_constraint=True,
        db_index=True,
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_code_transfer(user=self.from_user)
        super().save(*args, **kwargs)


class WalletDeposit(BaseModel):
    user = models.ForeignKey(
        to="authenticate.User",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="user_uid",
        related_name="wallet_deposit_fk_user",
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
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    code = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_code_transfer(user=self.user)
        return super().save(*args, **kwargs)


class TransferToken(BaseModel):
    user = models.ForeignKey(
        to="authenticate.User",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="user_uid",
        related_name="transfer_token_fk_user",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    token = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        editable=False,
        default=uuid.uuid4,
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        null=False,
        blank=False,
    )


class Withdraw(models.Model):
    uid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
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
    user = models.ForeignKey(
        to="authenticate.User",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="user_uid",
        related_name="bank_account_withdraw_fk_user",
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
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_code_transfer(user=self.user)
        return super().save(*args, **kwargs)
