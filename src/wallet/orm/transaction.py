# from utils.schemas.filter_and_order_by import FilterNameSchema, OrderByNameAndUpdatedAtSchema
# from uuid import UUID

# from .schemas.request import TransactionRequest


class TransactionORM:
    pass
    # @staticmethod
    # def create_transaction(user: User, data: TransactionRequest):
    #     return Transaction.objects.create(user=user, **data.dict())

    # @staticmethod
    # def get_transaction_detail(user: User, transaction_uid: UUID):
    #     return Transaction.objects.get(user=user, uid=transaction_uid)

    # @staticmethod
    # def list_transactions(user: User, filter: FilterNameSchema, order_by: OrderByNameAndUpdatedAtSchema):
    #     return Transaction.objects.filter(user=user).order_by(order_by.order_by)
