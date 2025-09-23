from http import HTTPStatus

from utils.router.exception import APIException


class GroupNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "GROUP_NOT_FOUND"
    message = "Group not found"


class UserNotInGroup(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "USER_NOT_IN_GROUP"
    message = "User not in group"
