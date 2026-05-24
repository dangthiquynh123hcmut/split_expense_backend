from http import HTTPStatus

from utils.router.exception import APIException


class EventNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "EVENT_NOT_FOUND"
    message = "Event not found"


class EventClosed(APIException):
    error_code = HTTPStatus.FORBIDDEN
    message_code = "EVENT_CLOSED"
    message = "Event is closed. No changes are allowed."
