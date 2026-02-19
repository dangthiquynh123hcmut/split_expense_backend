from datetime import timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from django.db.models import CharField, F, Q, Value
from django.utils.timezone import now

from authenticate.models import User
from group.models import Group
from utils.functions.get_last_month import get_last_month
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

    @staticmethod
    def total_transactions_today():
        today = now().date()
        return Transaction.objects.filter(
            created_at__date=today
        ).count(), Transaction.objects.filter(
            created_at__date=today - timedelta(days=1)
        ).count()

    @staticmethod
    def count_transactions():
        start_last_month, end_last_month = get_last_month(now())
        start_this_month = now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return Transaction.objects.filter(
            created_at__gte=start_this_month
        ).count(), Transaction.objects.filter(
            created_at__gte=start_last_month, created_at__lte=end_last_month
        ).count()

    @staticmethod
    def list_transactions_withdraws_and_deposits(userName: Optional[str] = None):
        query = Transaction.objects.all()
        if userName:
            query = query.filter(
                Q(from_user__full_name__icontains=userName)
                | Q(to_user__full_name__icontains=userName)
            )
        return query.annotate(
            type=Value("transaction", output_field=CharField())
        ).select_related("from_user", "to_user", "group")
