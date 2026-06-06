from django.db import transaction

from authenticate.models import User
from authenticate.queries import Query as AuthQuery
from event.queries import Query as EventQuery
from exceptions.event import EventNotFound
from exceptions.group import GroupNotFound
from exceptions.users import BalanceNotEnough, UserNotFound
from exceptions.wallet import InvalidTokenOrAmountIncorrect, PinIncorrect, PinNotSet
from expense.queries import Query as ExpenseQuery
from group.queries import Query as GroupQuery
from user.schemas.response import UserResponse
from utils.enums import DebtOptimizationEnum
from utils.functions.debt_simplification import settle_event_debts_by_group_payment
from utils.functions.transfer_token import (
    generate_transfer_token,
    verify_transfer_token,
)
from utils.schemas.filter_and_order_by import (
    FilterCodeSchema,
    FilterDateAndAmountSchema,
    FilterGroupSchema,
)
from utils.services.firebase_cm.fcm_service import FCMService
from wallet.orm.transaction import TransactionORM
from wallet.schemas.request import TransferRequest, VerifyPinRequest
from wallet.schemas.response import ListTransactionResponse, TransactionResponse


class TransactionService:
    def __init__(self):
        self.query = TransactionORM()
        self.auth_query = AuthQuery()
        self.group_query = GroupQuery()
        self.event_query = EventQuery()
        self.expense_query = ExpenseQuery()
        self.fcm_service = FCMService()

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
        if user.balance < payload.convert_amount:
            raise BalanceNotEnough
        if payload.group_uid:
            group = self.group_query.get_group_sync(group_uid=payload.group_uid)
            if not group:
                raise GroupNotFound
            if group.debt_optimization == DebtOptimizationEnum.GROUP:
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
            if group.debt_optimization == DebtOptimizationEnum.EVENT:
                event_debts = (
                    self.event_query.get_event_restructure_debts_between_users(
                        debtor=user,
                        creditor=to_user,
                        group=group,
                        currency=payload.currency,
                    )
                )
                settlements = settle_event_debts_by_group_payment(
                    event_debts, payload.original_amount
                )
                for debt, settled_amount in settlements:
                    self.event_query.settle_event_restructure_debt(
                        debt=debt,
                        amount=settled_amount,
                        debtor=user,
                        creditor=to_user,
                        currency=payload.currency,
                    )

            transaction = self.query.create_transaction(
                from_user=user,
                to_user=to_user,
                amount=payload.convert_amount,
                description=payload.description,
                group=group,
            )
        elif payload.event_uid:
            event = self.event_query.get_event(event_uid=payload.event_uid)
            if not event:
                raise EventNotFound
            self.event_query.update_event_member_balance(
                debtor=user,
                creditor=to_user,
                event=event,
                amount=payload.original_amount,
                currency=payload.currency,
            )
            self.event_query.update_event_restructure_debt(
                debtor=user,
                creditor=to_user,
                event=event,
                amount=payload.original_amount,
                currency=payload.currency,
            )
            transaction = self.query.create_transaction(
                from_user=user,
                to_user=to_user,
                amount=payload.convert_amount,
                description=payload.description,
                event=event,
            )
        else:
            # Direct wallet-to-wallet transfer (no group or event)
            transaction = self.query.create_transaction(
                from_user=user,
                to_user=to_user,
                amount=payload.convert_amount,
                description=payload.description,
            )
        self.query.update_balance_in_wallet(
            uid=user.uid, amount=-payload.convert_amount
        )
        self.query.update_balance_in_wallet(
            uid=payload.user_uid, amount=payload.convert_amount
        )
        self.fcm_service.send_notification(
            token=user.fcm_token,
            title="Transaction Request",
            body=f"You have requested to transfer {payload.convert_amount} to {to_user.full_name}.",
        )
        self.fcm_service.send_notification(
            token=to_user.fcm_token,
            title="Transaction Request",
            body=f"You have received {payload.convert_amount} from {user.full_name}.",
        )
        return TransactionResponse(
            from_user=UserResponse.from_orm(user),
            to_user=UserResponse.from_orm(to_user),
            amount=payload.convert_amount,
            description=payload.description,
            group=group.name if payload.group_uid else None,
            code=transaction.code,
            created_at=transaction.created_at,
            event=event.name if payload.event_uid else None,
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
