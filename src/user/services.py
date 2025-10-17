from authenticate.models import User
from user.schemas.response import UserResponse, WalletResponse
from utils.types import TUser

from .queries import Query
from .schemas.request import UserFilterSchema


class UserService:
    def __init__(self):
        self.query = Query()

    def search_user(self, user: TUser, search: UserFilterSchema):
        return self.query.search_user(user=user, search=search)

    def get_wallet(self, user: User):
        return WalletResponse(
            balance=user.balance,
            user=UserResponse.from_orm(user),
            currency=user.currency,
        )
