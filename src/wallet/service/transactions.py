from django.db import transaction

from authenticate.models import User
from authenticate.queries import Query as AuthQuery
from exceptions.group import GroupNotFound
from exceptions.users import BalanceNotEnough, UserNotFound
from exceptions.wallet import InvalidTokenOrAmountIncorrect, PinIncorrect, PinNotSet
from expense.queries import Query as ExpenseQuery
from group.queries import Query as GroupQuery
from user.schemas.response import UserResponse
from utils.functions.transfer_token import (
    generate_transfer_token,
    verify_transfer_token,
)
from utils.schemas.filter_and_order_by import (
    FilterCodeSchema,
    FilterDateAndAmountSchema,
    FilterGroupSchema,
)
from wallet.orm.transaction import TransactionORM
from wallet.schemas.request import TransferRequest, VerifyPinRequest
from wallet.schemas.response import ListTransactionResponse, TransactionResponse


class TransactionService:
    def __init__(self):
        self.query = TransactionORM()
        self.auth_query = AuthQuery()
        self.group_query = GroupQuery()
        self.expense_query = ExpenseQuery()

    def get_external_transaction_history(
        self,
        user: User,
        filter_code: FilterCodeSchema,
        filter: FilterDateAndAmountSchema,
    ):
        query = self.query.get_external_transaction_history(
            user=user, filter_code=filter_code, filter=filter
        )
        return query

    def verify_pin(self, user: User, payload: VerifyPinRequest):
        if (
            user.check_pin(raw_pin=payload.pin) == "NO_PIN"
            or user.check_pin(raw_pin=payload.pin) == "NO_CURRENCY"
        ):
            raise PinNotSet
        if user.check_pin(raw_pin=payload.pin) == "INVALID":
            raise PinIncorrect
        if user.check_pin(raw_pin=payload.pin) == "VALID":
            return generate_transfer_token(user_uid=user.uid, amount=payload.amount)

    @transaction.atomic
    def create_transaction(self, user: User, payload: TransferRequest):
        to_user = self.auth_query.get_user_by_uid(uid=payload.user_uid)
        if not to_user:
            raise UserNotFound

        if not verify_transfer_token(
            user_uid=user.uid,
            token=payload.transfer_token,
            amount=payload.convert_amount,
        ):
            raise InvalidTokenOrAmountIncorrect
        if payload.group_uid:
            group = self.group_query.get_group_sync(group_uid=payload.group_uid)
            if not group:
                raise GroupNotFound
            self.group_query.update_balance_in_group(
                user=user,
                group=group,
                amount=-payload.original_amount,
                currency=payload.currency,
            )
            self.group_query.update_balance_in_group(
                user=to_user,
                group=group,
                amount=payload.original_amount,
                currency=payload.currency,
            )
            self.group_query.update_restructure_debt(
                debtor=user,
                creditor=to_user,
                group=group,
                amount=payload.original_amount,
                currency=payload.currency,
            )
        else:
            group = None
        if user.balance < payload.convert_amount:
            raise BalanceNotEnough
        self.query.update_balance_in_wallet(
            uid=user.uid, amount=-payload.convert_amount
        )
        self.query.update_balance_in_wallet(
            uid=payload.user_uid, amount=payload.convert_amount
        )
        transaction = self.query.create_transaction(
            from_user=user,
            to_user=to_user,
            amount=payload.convert_amount,
            description=payload.description,
            group=group,
        )
        return TransactionResponse(
            from_user=UserResponse.from_orm(user),
            to_user=UserResponse.from_orm(to_user),
            amount=payload.convert_amount,
            description=payload.description,
            group=group.name if payload.group_uid else None,
            code=transaction.code,
            created_at=transaction.created_at,
        )

    def list_transactions(
        self,
        user: User,
        filter: FilterGroupSchema,
        filter_date_and_amount: FilterDateAndAmountSchema,
    ):
        transactions = self.query.list_transactions(
            user=user, filter=filter, filter_date_and_amount=filter_date_and_amount
        )
        list_transaction = []
        for trans in transactions:
            list_transaction.append(
                ListTransactionResponse(
                    from_user=trans.from_user.full_name,
                    to_user=trans.to_user.full_name,
                    amount=trans.amount,
                    description=trans.description,
                    group=trans.group.name if trans.group else None,
                    code=trans.code,
                    created_at=trans.created_at,
                )
            )
        return list_transaction
