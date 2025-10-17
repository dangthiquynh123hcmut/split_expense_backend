from uuid import UUID

from authenticate.models import User
from exceptions.wallet import DepositNotFound
from wallet.orm.deposit import DepositORM


class DepositService:
    def __init__(self):
        self.query = DepositORM()

    def deposit_history(self, user: User):
        return self.query.deposit_history(user=user)

    def deposit_detail(self, user: User, deposit_uid: UUID):
        deposit = self.query.deposit_detail(user=user, deposit_uid=deposit_uid)
        if deposit is None:
            raise DepositNotFound
        return deposit


#     def create_transaction(self, user: User, data: TransactionRequest):
#         return self.query.create_transaction(user=user, data=data)

#     def get_transaction_detail(self, user: User, transaction_uid: UUID):
#         return self.query.get_transaction_detail(user=user, transaction_uid=transaction_uid)

#     def list_transactions(self, user: User, filter: FilterNameSchema, order_by: OrderByNameAndUpdatedAtSchema):
#         return self.query.list_transactions(user=user, filter=filter, order_by=order_by)
