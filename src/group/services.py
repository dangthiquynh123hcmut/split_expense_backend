from group.schemas.request import GroupRequest
from group.schemas.response import GroupResponse
from utils.types import TUser

from .queries import Query


class Service:
    def __init__(self):
        self.query = Query()

    def create_group(self, user: TUser, data: GroupRequest) -> GroupResponse:
        return self.query.create_group(user=user, data=data)
