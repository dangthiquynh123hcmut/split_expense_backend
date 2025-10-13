from http import HTTPStatus

from utils.router.exception import APIException


class BankAccountIsExists(APIException):
    error_code = HTTPStatus.CONFLICT
    message_code = "BANK_ACCOUNT_IS_EXISTS"
    message = "Bank account is exists"


class AccountNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "ACCOUNT_NOT_FOUND"
    message = "Account not found"
