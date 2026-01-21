from datetime import timedelta
from uuid import UUID

from django.utils.timezone import now

from authenticate.models import User
from bank_account.models import BankAccount
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
    def total_withdrawals_today():
        today = now().date()
        return Withdraw.objects.filter(
            created_at__date=today
        ).count(), Withdraw.objects.filter(
            created_at__date=today - timedelta(days=1)
        ).count()
