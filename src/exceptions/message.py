from http import HTTPStatus

from utils.router.exception import APIException


class MessageNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "MESSAGE_NOT_FOUND"
    message = "Message not found"
