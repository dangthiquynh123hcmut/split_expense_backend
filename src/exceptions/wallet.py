from http import HTTPStatus

from utils.router.exception import APIException


class DepositNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "DEPOSIT_NOT_FOUND"
    message = "Deposit not found"


class WithdrawNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "WITHDRAW_NOT_FOUND"
    message = "Withdraw not found"


class BankAccountNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "BANK_ACCOUNT_NOT_FOUND"
    message = "Bank account not found"
