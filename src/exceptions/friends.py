from http import HTTPStatus

from utils.router.exception import APIException


class FriendHasRelation(APIException):
    error_code = HTTPStatus.CONFLICT
    message_code = "FRIEND_HAS_RELATION"
    message = "Friendship relation already exists"
