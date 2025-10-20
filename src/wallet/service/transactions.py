from authenticate.models import User
from wallet.orm.transaction import TransactionORM


class TransactionService:
    def __init__(self):
        self.query = TransactionORM()

    def get_external_transaction_history(self, user: User):
        return self.query.get_external_transaction_history(user=user)


# def create_transaction(self, user: User, data: TransactionRequest):
#     return self.query.create_transaction(user=user, data=data)

# def get_transaction_detail(self, user: User, transaction_uid: UUID):
#     return self.query.get_transaction_detail(user=user, transaction_uid=transaction_uid)

# def list_transactions(self, user: User, filter: FilterNameSchema, order_by: OrderByNameAndUpdatedAtSchema):
#     return self.query.list_transactions(user=user, filter=filter, order_by=order_by)
