from decimal import Decimal
from typing import Optional
from uuid import UUID

from django.db.models import CharField, F, Q, Value

from authenticate.models import User
from group.models import Group
from utils.schemas.filter_and_order_by import (
    FilterCodeSchema,
    FilterDateAndAmountSchema,
    FilterGroupSchema,
)
from wallet.models import Transaction, WalletDeposit, Withdraw


class TransactionORM:
    @staticmethod
    def get_external_transaction_history(
        user: User, filter_code: FilterCodeSchema, filter: FilterDateAndAmountSchema
    ):
        deposits = (
            WalletDeposit.objects.filter(user=user)
            .annotate(type=Value("deposit", output_field=CharField()))
            .values("uid", "type", "amount", "currency", "code", "created_at")
        )
        withdraws = (
            Withdraw.objects.filter(user=user)
            .annotate(
                type=Value("withdraw", output_field=CharField()),
                currency=Value(user.currency, output_field=CharField()),
            )
            .values("uid", "type", "amount", "currency", "code", "created_at")
        )
        if filter_code:
            deposits = deposits.filter(filter_code.get_filter_expression())
            withdraws = withdraws.filter(filter_code.get_filter_expression())
        if filter:
            deposits = deposits.filter(filter.get_filter_expression())
            withdraws = withdraws.filter(filter.get_filter_expression())
        return deposits.union(withdraws).order_by("-created_at")

    @staticmethod
    def create_transaction(
        from_user: User,
        to_user: User,
        amount: Decimal,
        description: str,
        group: Optional[Group] = None,
    ):
        return Transaction.objects.create(
            from_user=from_user,
            to_user=to_user,
            amount=amount,
            currency=from_user.currency,
            description=description,
            group=group,
        )

    @staticmethod
    def list_transactions(
        user: User,
        filter: FilterGroupSchema,
        filter_date_and_amount: FilterDateAndAmountSchema,
    ):
        queryset = Transaction.objects.filter(Q(from_user=user) | Q(to_user=user))
        if filter:
            queryset = queryset.filter(filter.get_filter_expression())
        if filter_date_and_amount:
            queryset = queryset.filter(filter_date_and_amount.get_filter_expression())
        return queryset.order_by("-created_at")

    @staticmethod
    def update_balance_in_wallet(uid: UUID, amount: Decimal):
        return User.objects.filter(uid=uid).update(balance=F("balance") + amount)

    @staticmethod
    def get_transactions_in_group(group: Group):
        return Transaction.objects.filter(group=group).order_by("-created_at")

    @staticmethod
    def get_total_transactions(user: User):
        return Transaction.objects.filter(Q(from_user=user) | Q(to_user=user)).count()

    @staticmethod
    def get_latest_transactions(user: User):
        return (
            Transaction.objects.filter(Q(from_user=user) | Q(to_user=user))
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )
