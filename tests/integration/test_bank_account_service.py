"""
Integration tests for bank_account.services.Service.

Covers CRUD operations and ownership enforcement.
"""

import uuid

import pytest

from bank_account.models import BankAccount
from bank_account.schemas.requests import BankAccountRequest
from bank_account.services import Service
from exceptions.account import AccountNotFound
from utils.enums import BankEnum
from utils.exceptions import UpdatedIsDenied


def _make_service():
    return Service()


def _payload(**overrides):
    base = {
        "bank_name": BankEnum.VIETCOMBANK,
        "account_number": "9876543210",
        "currency": "VND",
    }
    base.update(overrides)
    return BankAccountRequest(**base)


@pytest.mark.django_db
class TestCreateBankAccount:
    def test_create_persists_record(self, user_a):
        service = _make_service()
        account = service.create_bank_account(user=user_a, payload=_payload())
        assert BankAccount.objects.filter(uid=account.uid).exists()

    def test_create_links_to_correct_user(self, user_a):
        service = _make_service()
        account = service.create_bank_account(user=user_a, payload=_payload())
        assert account.user == user_a

    def test_create_stores_correct_bank_name(self, user_a):
        service = _make_service()
        account = service.create_bank_account(
            user=user_a, payload=_payload(bank_name=BankEnum.BIDV)
        )
        assert account.bank_name == BankEnum.BIDV


@pytest.mark.django_db
class TestGetBankAccount:
    def test_get_returns_user_accounts(self, user_a):
        BankAccount.objects.create(
            user=user_a, bank_name=BankEnum.VIETCOMBANK, account_number="1111"
        )
        BankAccount.objects.create(
            user=user_a, bank_name=BankEnum.BIDV, account_number="2222"
        )
        service = _make_service()
        accounts = list(service.get_bank_account(user=user_a))
        assert len(accounts) == 2

    def test_get_does_not_return_other_users_accounts(self, user_a, user_b):
        BankAccount.objects.create(
            user=user_b, bank_name=BankEnum.VIETCOMBANK, account_number="3333"
        )
        service = _make_service()
        accounts = list(service.get_bank_account(user=user_a))
        assert len(accounts) == 0


@pytest.mark.django_db
class TestUpdateBankAccount:
    def test_owner_can_update(self, user_a):
        account = BankAccount.objects.create(
            user=user_a, bank_name=BankEnum.VIETCOMBANK, account_number="4444"
        )
        service = _make_service()
        updated = service.update_bank_account(
            uid=account.uid,
            user=user_a,
            payload=_payload(bank_name=BankEnum.TECHCOMBANK, account_number="5555"),
        )
        assert updated.bank_name == BankEnum.TECHCOMBANK
        assert updated.account_number == "5555"

    def test_non_owner_cannot_update(self, user_a, user_b):
        account = BankAccount.objects.create(
            user=user_a, bank_name=BankEnum.VIETCOMBANK, account_number="6666"
        )
        service = _make_service()
        with pytest.raises(UpdatedIsDenied):
            service.update_bank_account(
                uid=account.uid,
                user=user_b,
                payload=_payload(account_number="7777"),
            )


@pytest.mark.django_db
class TestDeleteBankAccount:
    def test_owner_can_delete(self, user_a):
        account = BankAccount.objects.create(
            user=user_a, bank_name=BankEnum.VIETCOMBANK, account_number="8888"
        )
        service = _make_service()
        service.delete_bank_account(uid=account.uid, user=user_a)
        assert not BankAccount.objects.filter(uid=account.uid).exists()

    def test_non_owner_cannot_delete(self, user_a, user_b):
        account = BankAccount.objects.create(
            user=user_a, bank_name=BankEnum.VIETCOMBANK, account_number="8889"
        )
        service = _make_service()
        with pytest.raises(AccountNotFound):
            service.delete_bank_account(uid=account.uid, user=user_b)

    def test_delete_nonexistent_raises(self, user_a):
        service = _make_service()
        with pytest.raises(AccountNotFound):
            service.delete_bank_account(uid=uuid.uuid4(), user=user_a)
