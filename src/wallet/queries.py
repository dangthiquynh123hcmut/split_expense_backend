# from utils.schemas.filter_and_order_by import FilterNameSchema, OrderByNameAndUpdatedAtSchema
# from uuid import UUID
from utils.types import User
from wallet.models import WalletDeposit


# from .schemas.request import TransactionRequest


class Query:
    # @staticmethod
    # def create_transaction(user: User, data: TransactionRequest):
    #     return Transaction.objects.create(user=user, **data.dict())

    # @staticmethod
    # def get_transaction_detail(user: User, transaction_uid: UUID):
    #     return Transaction.objects.get(user=user, uid=transaction_uid)

    # @staticmethod
    # def list_transactions(user: User, filter: FilterNameSchema, order_by: OrderByNameAndUpdatedAtSchema):
    #     return Transaction.objects.filter(user=user).order_by(order_by.order_by)

    @staticmethod
    def add_deposit_history(amount: float, user: User, code: str, currency: str):
        WalletDeposit.objects.create(
            user=user,
            amount=amount,
            currency=currency,
            code=code,
        )
