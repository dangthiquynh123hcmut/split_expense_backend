from uuid import UUID

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
