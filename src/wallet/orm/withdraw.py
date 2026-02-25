from datetime import timedelta
from typing import Optional
from uuid import UUID

from django.db.models import CharField, F, Sum, Value
from django.utils.timezone import now

from authenticate.models import User
from bank_account.models import BankAccount
from utils.functions.get_last_month import get_last_month
from wallet.models import Withdraw


class WithdrawORM:
    @staticmethod
    def withdraw(user: User, bank_account: BankAccount, amount: float):
        return Withdraw.objects.create(
            user=user, bank_account=bank_account, amount=amount
        )

    @staticmethod
    def withdraw_detail(user: User, withdraw_uid: UUID):
        return Withdraw.objects.get(user=user, uid=withdraw_uid)

    @staticmethod
    def get_total_withdraw(user: User):
        return Withdraw.objects.filter(user=user).count()

    @staticmethod
    def get_latest_withdrawals(user: User):
        return (
            Withdraw.objects.filter(user=user)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )

    @staticmethod
    def total_withdraw_today():
        today = now().date()
        return Withdraw.objects.filter(
            created_at__date=today
        ).count(), Withdraw.objects.filter(
            created_at__date=today - timedelta(days=1)
        ).count()

    @staticmethod
    def total_withdraw_money_today():
        today = now().date()
        total_withdrawals_today = (
            Withdraw.objects.filter(created_at__date=today).aggregate(
                total_amount=Sum("amount")
            )["total_amount"]
            or 0
        )
        total_withdrawals_yesterday = (
            Withdraw.objects.filter(
                created_at__date=today - timedelta(days=1)
            ).aggregate(total_amount=Sum("amount"))["total_amount"]
            or 0
        )
        return total_withdrawals_today, total_withdrawals_yesterday

    def count_withdrawals(self):
        start_last_month, end_last_month = get_last_month(now())
        start_this_month = now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return Withdraw.objects.filter(
            created_at__gte=start_this_month
        ).count(), Withdraw.objects.filter(
            created_at__gte=start_last_month, created_at__lte=end_last_month
        ).count()

    def list_withdraws(self, userName: Optional[str] = None):
        query = Withdraw.objects.all()
        if userName:
            query = query.filter(user__full_name__icontains=userName)
        return query.annotate(
            type=Value("withdraw", output_field=CharField())
        ).select_related("user")

    def cash_chart(self):
        return (
            Withdraw.objects.filter(
                created_at__date__lte=now().date(),
                created_at__date__gte=now().date() - timedelta(days=6),
            )
            .annotate(day=F("created_at__date"))
            .values("day")
            .annotate(total_amount=Sum("amount"))
            .order_by("day")
        )
