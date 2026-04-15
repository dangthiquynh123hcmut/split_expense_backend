from uuid import uuid4

from django.conf import settings
from django.db import models

from utils.enums import CurrencyEnum, StatusEnum
from utils.functions.remove_accents import remove_accents
from utils.models import BaseModel


class Group(BaseModel):
    name = models.CharField(max_length=255)
    name_no_accent = models.TextField(blank=True, editable=False)
    leader = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        to_field="uid",
        db_column="leader_uid",
        related_name="group_fk_leader",
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
    avatar_url = models.ForeignKey(
        to="attachment.Attachment",
        on_delete=models.SET_NULL,
        to_field="uid",
        db_column="avatar_url_uid",
        related_name="group_fk_avatar_url",
        db_constraint=True,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.name:
            self.name_no_accent = remove_accents(self.name)
        return super().save(*args, **kwargs)


class GroupMember(BaseModel):
    group = models.ForeignKey(
        to="group.Group",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="group_uid",
        related_name="group_member_fk_group",
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
        related_name="group_member_fk_user",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    last_read_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=StatusEnum.choices,
        default=StatusEnum.ACTIVE,
    )
    joined_at = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        unique_together = (("user", "group"),)
        indexes = [
            models.Index(fields=["user", "group"]),
        ]


class GroupMemberBalance(BaseModel):
    group = models.ForeignKey(
        to="group.Group",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="group_uid",
        related_name="group_member_balance_fk_group",
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
        related_name="group_member_balance_fk_user",
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
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)


class RestructureDebt(BaseModel):
    group = models.ForeignKey(
        to="group.Group",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="group_uid",
        related_name="restructure_debt_fk_group",
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
        related_name="restructure_debt_fk_debtor",
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
        related_name="restructure_debt_fk_creditor",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    currency = models.CharField(
        max_length=20,
        choices=CurrencyEnum.choices,
        default=CurrencyEnum.VND,
    )


class TransferConfirmToken(models.Model):
    uid = models.UUIDField(default=uuid4, unique=True, editable=False, primary_key=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_used = models.BooleanField(default=False)
    to_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="to_user_uid",
        related_name="transfer_confirm_token_fk_to_user",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    from_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="from_user_uid",
        related_name="transfer_confirm_token_fk_from_user",
        db_constraint=True,
        null=False,
        blank=False,
    )
    group = models.ForeignKey(
        to="group.Group",
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="group_uid",
        related_name="transfer_confirm_token_fk_group",
        db_constraint=True,
        null=False,
        blank=False,
    )
