from http import HTTPStatus

from utils.router.exception import APIException


class GroupNameAlreadyExists(APIException):
    error_code = HTTPStatus.CONFLICT
    message_code = "GROUP_NAME_ALREADY_EXISTS"
    message = "Group name already exists"


class GroupNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "GROUP_NOT_FOUND"
    message = "Group not found"
