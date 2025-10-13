from uuid import UUID

from exceptions.account import AccountNotFound
from utils.exceptions import UpdatedIsDenied
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, delete, get, post, put
from utils.router.paginate import paginate
from utils.router.permissions import IsAuthenticated
from utils.types import AuthenticatedRequest

from .schemas.requests import BankAccountRequest
from .schemas.responses import BankAccountResponse, ListBankAccount
from .services import Service


@api(
    prefix_or_class="bank_account",
    tags=["Bank Account"],
    auth=AuthBear(),
    permissions=[IsAuthenticated],
)
class BankAccountAPI(Controller):
    def __init__(self):
        self.service = Service()

    @get("", response=ListBankAccount, paginate=True)
    @paginate
    def get_bank_account(self, request: AuthenticatedRequest):
        return self.service.get_bank_account(user=request.user)

    @post("", response=BankAccountResponse)
    def create_bank_account(
        self, request: AuthenticatedRequest, payload: BankAccountRequest
    ):
        return self.service.create_bank_account(user=request.user, payload=payload)

    @put("/{uid}", response=BankAccountResponse, exceptions=(UpdatedIsDenied,))
    def update_bank_account(
        self, uid: UUID, request: AuthenticatedRequest, payload: BankAccountRequest
    ):
        return self.service.update_bank_account(
            uid=uid, user=request.user, payload=payload
        )

    @delete("/{uid}", response=bool, exceptions=(AccountNotFound,))
    def delete_bank_account(self, uid: UUID, request: AuthenticatedRequest):
        return self.service.delete_bank_account(uid=uid, user=request.user)
