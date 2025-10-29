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


class PinIncorrect(APIException):
    error_code = HTTPStatus.BAD_REQUEST
    message_code = "PIN_INCORRECT"
    message = "Pin incorrect"


class PinAlreadyExists(APIException):
    error_code = HTTPStatus.BAD_REQUEST
    message_code = "PIN_ALREADY_EXISTS"
    message = "Pin already exists"


class InvalidTokenOrAmountIncorrect(APIException):
    error_code = HTTPStatus.BAD_REQUEST
    message_code = "INVALID_TOKEN_OR_AMOUNT_INCORRECT"
    message = "Invalid token or amount incorrect"
