from http import HTTPStatus

from utils.router.exception import APIException


class ExpenseNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "EXPENSE_NOT_FOUND"
    message = "Expense not found"
