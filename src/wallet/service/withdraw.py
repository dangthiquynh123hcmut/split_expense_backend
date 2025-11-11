from uuid import UUID

from django.db import transaction

from authenticate.models import User
from bank_account.queries import Query as BankAccountQuery
from exceptions.wallet import BankAccountNotFound
from user.queries import Query as UserQuery
from utils.services.fcm_service import FCMService
from wallet.orm.withdraw import WithdrawORM
from wallet.schemas.request import WithdrawRequest


class WithdrawService:
    def __init__(self):
        self.query = WithdrawORM()
        self.bank_account_query = BankAccountQuery()
        self.user_query = UserQuery()
        self.fcm_service = FCMService()

    @transaction.atomic
    def withdraw(self, user: User, payload: WithdrawRequest):
        bank_account = self.bank_account_query.get_bank_account_by_account_number(
            account_number=payload.account_number,
            user=user,
            bank_name=payload.bank_name,
        )
        if not bank_account:
            raise BankAccountNotFound
        self.user_query.update_balance(user=user, amount=-payload.amount)
        self.fcm_service.send_notification(
            token=user.fcm_token,
            title="Withdrawal Request",
            body=f"You have requested to withdraw {payload.amount} from your bank account.",
        )
        return self.query.withdraw(
            user=user, bank_account=bank_account[0], amount=payload.amount
        )

    def withdraw_history(self, user: User):
        return self.query.withdraw_history(user=user)

    def withdraw_detail(self, user: User, withdraw_uid: UUID):
        return self.query.withdraw_detail(user=user, withdraw_uid=withdraw_uid)
