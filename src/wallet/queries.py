# from wallet.models import Wallet, Transaction
# from utils.schemas.filter_and_order_by import FilterNameSchema, OrderByNameAndUpdatedAtSchema
# from uuid import UUID
# from utils.types import User
# from wallet.schemas.request import TransactionRequest

# class Query:
#     @staticmethod
#     def get_wallet(user: User):
#         return Wallet.objects.get(user=user)

#     @staticmethod
#     def create_wallet(user: User):
#         return Wallet.objects.create(user=user)

#     @staticmethod
#     def create_transaction(user: User, data: TransactionRequest):
#         return Transaction.objects.create(user=user, **data.dict())

#     @staticmethod
#     def get_transaction_detail(user: User, transaction_uid: UUID):
#         return Transaction.objects.get(user=user, uid=transaction_uid)

#     @staticmethod
#     def list_transactions(user: User, filter: FilterNameSchema, order_by: OrderByNameAndUpdatedAtSchema):
#         return Transaction.objects.filter(user=user).order_by(order_by.order_by)
