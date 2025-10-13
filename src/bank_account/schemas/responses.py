from ninja import ModelSchema

from bank_account.models import BankAccount


class BankAccountResponse(ModelSchema):
    class Meta:
        model = BankAccount
        fields = "__all__"


class ListBankAccount(ModelSchema):
    class Meta:
        model = BankAccount
        exclude = ["user"]
