from .queries import Query
from .schemas.request import UserFilterSchema


class UserService:
    def __init__(self):
        self.query = Query()

    def search_user(self, search: UserFilterSchema):
        return self.query.search_user(search=search)
