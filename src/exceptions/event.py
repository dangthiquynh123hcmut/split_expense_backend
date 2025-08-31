from http import HTTPStatus

from utils.router.exception import APIException


class EventNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "EVENT_NOT_FOUND"
    message = "Event not found"
