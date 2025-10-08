# from utils.types import AuthenticatedRequest
# from .services import Service
# from .schemas.response import WalletResponse
# from utils.router.authenticate import AuthBear
# from utils.router.permissions import IsAuthenticated
# from utils.router.controller import Controller, api, get, post
# from .schemas.response import TransactionResponse
# from .schemas.request import TransactionRequest
# from utils.router.paginate import paginate
# from uuid import UUID
# from ninja import Query
# from utils.schemas.filter_and_order_by import FilterNameSchema, OrderByNameAndUpdatedAtSchema
# @api(
#     prefix_or_class="wallet",
#     tags=["Wallet"],
#     auth=AuthBear(),
#     permissions=[IsAuthenticated],
# )
# class WalletAPI(Controller):
#     def __init__(self):
#         self.service = Service()

#     @get("/wallet", response=WalletResponse)
#     def get_wallet(self, request: AuthenticatedRequest):
#         return self.service.get_wallet(user=request.user)

# @api(
#     prefix_or_class="transaction",
#     tags=["Transaction"],
#     auth=AuthBear(),
#     permissions=[IsAuthenticated],
# )
# class TransactionAPI(Controller):
#     def __init__(self):
#         self.service = Service()

#     @post("", response=TransactionResponse)
#     def create_transaction(self, request: AuthenticatedRequest, data: TransactionRequest):
#         return self.service.create_transaction(user=request.user, data=data)

#     @get("", response=TransactionResponse, paginate=True)
#     @paginate
#     def list_transactions(self, request: AuthenticatedRequest, filter: FilterNameSchema = Query(...), order_by: OrderByNameAndUpdatedAtSchema = Query(...)):
#         return self.service.list_transactions(user=request.user, filter=filter, order_by=order_by)

#     @get("/{transaction_uid}", response=TransactionResponse)
#     def get_transaction(self, request: AuthenticatedRequest, transaction_uid: UUID):
#         return self.service.get_transaction(user=request.user, transaction_uid=transaction_uid)

#     @get("/{group_uid}", response=TransactionResponse)
#     def group_transactions_report(self, request: AuthenticatedRequest, group_uid: UUID):
#         return self.service.group_transactions_report(user=request.user, group_uid=group_uid)
