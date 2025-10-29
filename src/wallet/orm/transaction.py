from decimal import Decimal
from typing import Optional
from uuid import UUID

from django.db.models import CharField, F, Q, Value

from authenticate.models import User
from group.models import Group
from utils.schemas.filter_and_order_by import FilterNameSchema
from wallet.models import Transaction, WalletDeposit, Withdraw


class TransactionORM:
    @staticmethod
    def get_external_transaction_history(user: User):
        deposits = (
            WalletDeposit.objects.filter(user=user)
            .annotate(type=Value("deposit", output_field=CharField()))
            .values("uid", "type", "amount", "currency", "code", "date")
        )

        withdraws = (
            Withdraw.objects.filter(user=user)
            .annotate(
                type=Value("withdraw", output_field=CharField()),
                currency=Value(user.currency, output_field=CharField()),
            )
            .values("uid", "type", "amount", "currency", "code", "date")
        )

        return deposits.union(withdraws).order_by("-date")

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
        user: User, filter: FilterNameSchema, group: Optional[Group] = None
    ):
        if not group:
            queryset = Transaction.objects.filter(Q(from_user=user) | Q(to_user=user))
        else:
            queryset = Transaction.objects.filter(
                Q(from_user=user) | Q(to_user=user), group=group
            )
        if filter:
            queryset = queryset.filter(filter.get_filter_expression())
        return queryset.order_by("-created_at")

    @staticmethod
    def update_balance_in_wallet(uid: UUID, amount: Decimal):
        return User.objects.filter(uid=uid).update(balance=F("balance") + amount)
