from uuid import UUID

from django.db import IntegrityError

from bank_account.models import BankAccount
from bank_account.schemas.requests import BankAccountRequest
from exceptions.account import BankAccountIsExists
from utils.types import User


class Query:
    @staticmethod
    def get_bank_account(user: User):
        return BankAccount.objects.filter(user=user)

    @staticmethod
    def get_bank_account_by_uid(uid: UUID, user: User):
        try:
            return BankAccount.objects.get(uid=uid, user=user)
        except BankAccount.DoesNotExist:
            return None

    @staticmethod
    def create_bank_account(user: User, payload: BankAccountRequest):
        try:
            return BankAccount.objects.create(user=user, **payload.dict())
        except IntegrityError:
            raise BankAccountIsExists

    @staticmethod
    def update_bank_account(bank_account: BankAccount, payload: BankAccountRequest):
        bank_account.account_number = payload.account_number
        bank_account.bank_name = payload.bank_name
        bank_account.currency = payload.currency
        bank_account.save()
        return bank_account

    @staticmethod
    def delete_bank_account(bank_account: BankAccount):
        bank_account.delete()
        return True

    @staticmethod
    def get_bank_account_by_account_number(
        account_number: str, user: User, bank_name: str
    ):
        return BankAccount.objects.filter(
            user=user, account_number=account_number, bank_name=bank_name
        )
