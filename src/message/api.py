from uuid import UUID

from asgiref.sync import async_to_sync
from ninja import Query

from exceptions.group import GroupNotFound
from utils.exceptions import GetIsDenied
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, delete, get, post, put
from utils.router.paginate import paginate
from utils.router.permissions import IsAuthenticated
from utils.types import AuthenticatedRequest

from .schemas.request import MessageFilter, MessageIn
from .schemas.response import MessageOut, MessageUpdateOut, NotificationResponse
from .services.message_services import MessageService
from .services.notification_services import NotificationService


@api(
    prefix_or_class="messages",
    tags=["Message"],
    auth=AuthBear(),
    permissions=[IsAuthenticated],
)
class MessageAPI(Controller):
    def __init__(self, service: MessageService):
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

    @get(
        "/group/{group_uid}",
        response=MessageOut,
        paginate=True,
        exceptions=(GroupNotFound, GetIsDenied),
    )
    @paginate
    def list_messages(
        self,
        request: AuthenticatedRequest,
        group_uid: UUID,
        filters: MessageFilter = Query(...),
    ):
        return self.service.list_messages(
            user=request.user, group_uid=group_uid, filters=filters
        )

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


@api(
    prefix_or_class="notifications",
    tags=["Notification"],
    auth=AuthBear(),
    permissions=[IsAuthenticated],
)
class NotificationAPI(Controller):
    def __init__(self, service: NotificationService):
        self.notification_service = service

    @get("", response=NotificationResponse, paginate=True)
    @paginate
    def list_notifications(self, request: AuthenticatedRequest):
        return self.notification_service.list_notifications(user=request.user)
