# from authenticate.models import User
# from wallet.queries import Query
# from wallet.schemas.request import TransactionRequest
# class Service:
#     def __init__(self):
#         self.query = Query()

#     def get_wallet(self, user: User):
#         return self.query.get_wallet(user=user)

#     def create_wallet(self, user: User):
#         return self.query.create_wallet(user=user)

#     def create_transaction(self, user: User, data: TransactionRequest):
#         return self.query.create_transaction(user=user, data=data)

#     def get_transaction_detail(self, user: User, transaction_uid: UUID):
#         return self.query.get_transaction_detail(user=user, transaction_uid=transaction_uid)

#     def list_transactions(self, user: User, filter: FilterNameSchema, order_by: OrderByNameAndUpdatedAtSchema):
#         return self.query.list_transactions(user=user, filter=filter, order_by=order_by)
