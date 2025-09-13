from http import HTTPStatus

from utils.router.exception import APIException


class FriendHasRelation(APIException):
    error_code = HTTPStatus.CONFLICT
    message_code = "FRIEND_HAS_RELATION"
    message = "Friendship relation already exists"


class FriendshipNotFound(APIException):
    error_code = HTTPStatus.NOT_FOUND
    message_code = "FRIENDSHIP_NOT_FOUND"
    message = "Friendship not found"
