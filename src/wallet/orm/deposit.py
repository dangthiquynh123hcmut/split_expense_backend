from datetime import timedelta
from typing import Optional
from uuid import UUID

from django.db.models import CharField, Sum, Value
from django.utils.timezone import now

from utils.functions.get_last_month import get_last_month
from utils.types import TUser
from wallet.models import WalletDeposit


class DepositORM:
    @staticmethod
    def add_deposit_history(user: TUser, amount: float, currency: str):
        return WalletDeposit.objects.create(
            user=user,
            amount=amount,
            currency=currency,
        )

    @staticmethod
    def deposit_detail(user: TUser, deposit_uid: UUID):
        return WalletDeposit.objects.get(user=user, uid=deposit_uid)

    @staticmethod
    def get_total_deposit(user: TUser):
        return WalletDeposit.objects.filter(user=user).count()

    @staticmethod
    def total_deposit_today():
        today = now().date()
        return WalletDeposit.objects.filter(
            created_at__date=today
        ).count(), WalletDeposit.objects.filter(
            created_at__date=today - timedelta(days=1)
        ).count()

    @staticmethod
    def get_latest_deposits(user: TUser):
        return (
            WalletDeposit.objects.filter(user=user)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )

    @staticmethod
    def total_deposit_money_today():
        today = now().date()
        total_deposits_today = (
            WalletDeposit.objects.filter(created_at__date=today).aggregate(
                total_amount=Sum("amount")
            )["total_amount"]
            or 0
        )
        total_deposits_yesterday = (
            WalletDeposit.objects.filter(
                created_at__date=today - timedelta(days=1)
            ).aggregate(total_amount=Sum("amount"))["total_amount"]
            or 0
        )
        return total_deposits_today, total_deposits_yesterday

    def count_deposits(self):
        start_last_month, end_last_month = get_last_month(now())
        start_this_month = now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return WalletDeposit.objects.filter(
            created_at__gte=start_this_month
        ).count(), WalletDeposit.objects.filter(
            created_at__gte=start_last_month, created_at__lte=end_last_month
        ).count()

    def list_deposits(self, userName: Optional[str] = None):
        query = WalletDeposit.objects.all()
        if userName:
            query = query.filter(user__full_name__icontains=userName)
        return query.annotate(
            type=Value("deposit", output_field=CharField())
        ).select_related("user")
