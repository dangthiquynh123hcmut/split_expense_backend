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


class ExpenseAlreadyVoted(APIException):
    error_code = HTTPStatus.BAD_REQUEST
    message_code = "EXPENSE_ALREADY_VOTED"
    message = "You have already voted on this expense"


class ExpenseApprovalExpired(APIException):
    error_code = HTTPStatus.BAD_REQUEST
    message_code = "EXPENSE_APPROVAL_EXPIRED"
    message = "The approval period for this expense has expired"


class ExpenseApprovalNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "EXPENSE_APPROVAL_NOT_FOUND"
    message = "You are not a member of this expense approval"


class ExpenseNotPendingApproval(APIException):
    error_code = HTTPStatus.BAD_REQUEST
    message_code = "EXPENSE_NOT_PENDING_APPROVAL"
    message = "This expense does not have a pending approval"


class ExpenseHasPendingAction(APIException):
    error_code = HTTPStatus.BAD_REQUEST
    message_code = "EXPENSE_HAS_PENDING_ACTION"
    message = "This expense already has a pending action awaiting approval"
