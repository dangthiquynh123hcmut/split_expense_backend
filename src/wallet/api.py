from uuid import UUID

from ninja import Query

from authenticate.schemas import TokenResponse
from exceptions.group import GroupNotFound
from exceptions.users import UserNotFound
from exceptions.wallet import (
    BankAccountNotFound,
    BankBinNotFound,
    DepositNotFound,
    InvalidTokenOrAmountIncorrect,
    PayOSPayoutFailed,
)
from user.schemas.response import WalletResponse
from user.services import UserService
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, get, post
from utils.router.paginate import paginate
from utils.router.permissions import IsAuthenticated
from utils.schemas.filter_and_order_by import (
    FilterCodeSchema,
    FilterDateAndAmountSchema,
    FilterGroupSchema,
)
from utils.types import AuthenticatedRequest
from wallet.schemas.response import (
    ListTransactionResponse,
    TransactionHistoryResponse,
    TransactionResponse,
    WalletDepositResponse,
    WalletWithdrawResponse,
)
from wallet.service.deposits import DepositService
from wallet.service.transactions import TransactionService
from wallet.service.withdraw import WithdrawService

from .schemas.request import TransferRequest, VerifyPinRequest, WithdrawRequest


@api(
    prefix_or_class="wallet",
    tags=["Wallet"],
    auth=AuthBear(),
    permissions=[IsAuthenticated],
)
class WalletAPI(Controller):
    def __init__(self):
        self.user_service = UserService()
        self.deposit_service = DepositService()
        self.transaction_service = TransactionService()
        self.withdraw_service = WithdrawService()

    @get("", response=WalletResponse)
    def get_wallet(self, request: AuthenticatedRequest):
        return self.user_service.get_wallet(user=request.user)

    @get("/external", response=TransactionHistoryResponse, paginate=True)
    @paginate
    def get_external_transaction_history(
        self,
        request: AuthenticatedRequest,
        filter_code: FilterCodeSchema = Query(...),
        filter: FilterDateAndAmountSchema = Query(...),
    ):
        return self.transaction_service.get_external_transaction_history(
            user=request.user,
            filter_code=filter_code,
            filter=filter,
        )

    @get(
        "/{deposit_uid}/deposit",
        response=WalletDepositResponse,
        exceptions=(DepositNotFound,),
    )
    def deposit_detail(self, request: AuthenticatedRequest, deposit_uid: UUID):
        return self.deposit_service.deposit_detail(
            user=request.user, deposit_uid=deposit_uid
        )

    @post(
        "/withdraw",
        response=WalletWithdrawResponse,
        exceptions=(BankAccountNotFound, BankBinNotFound, PayOSPayoutFailed),
    )
    def withdraw(self, request: AuthenticatedRequest, payload: WithdrawRequest):
        return self.withdraw_service.withdraw(user=request.user, payload=payload)

    @get("/{withdraw_uid}/withdraw", response=WalletWithdrawResponse)
    def withdraw_detail(self, request: AuthenticatedRequest, withdraw_uid: UUID):
        return self.withdraw_service.withdraw_detail(
            user=request.user, withdraw_uid=withdraw_uid
        )

    @post("/verify-pin", response=TokenResponse, exceptions=(UserNotFound,))
    def verify_pin(self, request: AuthenticatedRequest, payload: VerifyPinRequest):
        token = self.transaction_service.verify_pin(user=request.user, payload=payload)
        return TokenResponse(token=token)

    @post(
        "/transaction",
        response=TransactionResponse,
        exceptions=(UserNotFound, InvalidTokenOrAmountIncorrect, GroupNotFound),
    )
    def create_transaction(
        self, request: AuthenticatedRequest, payload: TransferRequest
    ):
        return self.transaction_service.create_transaction(
            user=request.user, payload=payload
        )

    @get("/transaction", response=ListTransactionResponse, paginate=True)
    @paginate
    def list_transactions(
        self,
        request: AuthenticatedRequest,
        filter: FilterGroupSchema = Query(...),
        filter_date_and_amount: FilterDateAndAmountSchema = Query(...),
    ):
        return self.transaction_service.list_transactions(
            user=request.user,
            filter=filter,
            filter_date_and_amount=filter_date_and_amount,
        )
