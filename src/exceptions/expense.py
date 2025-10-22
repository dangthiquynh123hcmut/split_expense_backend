from http import HTTPStatus

from utils.router.exception import APIException


class ExpenseNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "EXPENSE_NOT_FOUND"
    message = "Expense not found"


class ListMemberNotMatch(APIException):
    error_code = HTTPStatus.BAD_REQUEST
    message_code = "LIST_MEMBER_NOT_MATCH"
    message = "List member not match"
