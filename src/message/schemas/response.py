from ninja import ModelSchema

from message.models import Message
from user.schemas.response import UserResponse


class MessageOut(ModelSchema):
    user: UserResponse

    class Meta:
        model = Message
        exclude = ["group"]


class MessageUpdateOut(ModelSchema):
    class Meta:
        model = Message
        exclude = ["group", "user"]
