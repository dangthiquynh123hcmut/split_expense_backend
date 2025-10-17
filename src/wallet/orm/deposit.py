from uuid import UUID

from utils.types import User
from wallet.models import WalletDeposit


class DepositORM:
    @staticmethod
    def add_deposit_history(amount: float, user: User, currency: str):
        WalletDeposit.objects.create(
            user=user,
            amount=amount,
            currency=currency,
        )

    @staticmethod
    def deposit_history(user: User):
        return WalletDeposit.objects.filter(user=user).order_by("-created_at")

    @staticmethod
    def deposit_detail(user: User, deposit_uid: UUID):
        return WalletDeposit.objects.get(user=user, uid=deposit_uid)
