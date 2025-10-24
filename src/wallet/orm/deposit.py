from uuid import UUID

from utils.types import TUser
from wallet.models import WalletDeposit


class DepositORM:
    @staticmethod
    def add_deposit_history(user: TUser, amount: float, currency: str):
        WalletDeposit.objects.create(
            user=user,
            amount=amount,
            currency=currency,
        )

    @staticmethod
    def deposit_detail(user: TUser, deposit_uid: UUID):
        return WalletDeposit.objects.get(user=user, uid=deposit_uid)
