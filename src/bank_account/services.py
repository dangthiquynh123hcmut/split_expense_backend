from uuid import UUID

from exceptions.account import AccountNotFound
from utils.exceptions import UpdatedIsDenied
from utils.types import User

from .queries import Query
from .schemas.requests import BankAccountRequest


class Service:
    def __init__(self) -> None:
        self.query = Query()

    def get_bank_account(self, user: User):
        return self.query.get_bank_account(user=user)

    def create_bank_account(self, user: User, payload: BankAccountRequest):
        return self.query.create_bank_account(user=user, payload=payload)

    def update_bank_account(self, uid: UUID, user: User, payload: BankAccountRequest):
        bank_account = self.query.get_bank_account_by_uid(uid=uid, user=user)
        if bank_account is None:
            raise UpdatedIsDenied
        return self.query.update_bank_account(
            bank_account=bank_account, payload=payload
        )

    def delete_bank_account(self, uid: UUID, user: User):
        bank_account = self.query.get_bank_account_by_uid(uid=uid, user=user)
        if bank_account is None:
            raise AccountNotFound
        return self.query.delete_bank_account(bank_account=bank_account)
