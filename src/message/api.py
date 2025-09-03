from uuid import UUID

from asgiref.sync import async_to_sync
from ninja import Query

from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, delete, get, post, put
from utils.router.paginate import paginate
from utils.router.permissions import IsAuthenticated
from utils.types import AuthenticatedRequest

from .schemas.request import MessageFilter, MessageIn
from .schemas.response import MessageOut, MessageUpdateOut
from .services import Service


@api(
    prefix_or_class="messages",
    tags=["Message"],
    auth=AuthBear(),
    permissions=[IsAuthenticated],
)
class MessageAPI(Controller):
    def __init__(self, service: Service):
        self.service = service

    @post("/group/{group_uid}", response=MessageOut)
    def sent_message(
        self, request: AuthenticatedRequest, group_uid: UUID, message: MessageIn
    ):
        return async_to_sync(self.service.sent_message)(
            user=request.user,
            group_uid=group_uid,
            message=message,
        )

    @get("/group/{group_uid}", response=MessageOut, paginate=True)
    @paginate
    def list_messages(self, group_uid: UUID, filters: MessageFilter = Query(...)):
        return self.service.list_messages(group_uid=group_uid, filters=filters)

    @put("/{message_uid}", response=MessageUpdateOut)
    def update_message(
        self, request: AuthenticatedRequest, message_uid: UUID, data: MessageIn
    ):
        return async_to_sync(self.service.update_message)(
            user=request.user,
            message_uid=message_uid,
            data=data,
        )

    @delete("/{message_uid}", response=bool)
    def delete_message(self, request: AuthenticatedRequest, message_uid: UUID):
        return async_to_sync(self.service.delete_message)(
            user=request.user,
            message_uid=message_uid,
        )
