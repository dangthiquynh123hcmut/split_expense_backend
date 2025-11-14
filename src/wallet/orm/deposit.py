from uuid import UUID

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
    def get_latest_deposits(user: TUser):
        return (
            WalletDeposit.objects.filter(user=user)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )
