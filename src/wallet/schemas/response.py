from ninja import ModelSchema

from bank_account.schemas.responses import BankAccountResponse
from user.schemas.response import UserResponse
from wallet.models import WalletDeposit, Withdraw


# class GroupTransactionsReport(BaseModel):
#     total_amount: Decimal
#     transactions: list[TransactionResponse]


class WalletDepositResponse(ModelSchema):
    class Meta:
        model = WalletDeposit
        fields = "__all__"


class WalletWithdrawResponse(ModelSchema):
    user: UserResponse
    bank_account: BankAccountResponse

    class Meta:
        model = Withdraw
        fields = "__all__"
