from uuid import UUID

from attachment.services import AttachmentService
from authenticate.api import AuthenticatedRequest
from exceptions.event import EventNotFound
from exceptions.expense import ExpenseNotFound
from exceptions.group import GroupNotFound
from exceptions.users import UserNotFound
from expense.schemas.request import ExpenseRequest, ExpenseUpdateRequest
from expense.schemas.response import (
    CreateExpenseResponse,
    ExpenseResponse,
    ListExpenseResponse,
)
from expense.service import Service
from utils.exceptions import DeleteIsDenied, GetIsDenied, UpdatedIsDenied
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, delete, get, post, put
from utils.router.paginate import paginate
from utils.router.permissions import IsAuthenticated


@api(
    prefix_or_class="expenses",
    tags=["Expense"],
    auth=AuthBear(),
    permissions=[IsAuthenticated],
)
class ExpenseAPI(Controller):
    def __init__(self, service: Service):
        self.service = service
        self.attachment_service = AttachmentService()

    @post(
        "",
        response=CreateExpenseResponse,
        exceptions=(GroupNotFound, EventNotFound, UserNotFound),
    )
    def create_expense(self, request: AuthenticatedRequest, payload: ExpenseRequest):
        list_attachment = []
        for att in payload.list_attachment:
            attachment, presigned_url = self.attachment_service.get_presigned_url(
                user=request.user,
                payload=att,
            )
            list_attachment.append({"uid": attachment.uid, "url": presigned_url})
        expense = self.service.create_expense(creator=request.user, payload=payload)
        return {"list_attachment": list_attachment, "expense": expense}

    @get(
        "/{event_uid}",
        response=ListExpenseResponse,
        paginate=True,
        exceptions=(EventNotFound, GetIsDenied),
    )
    @paginate
    def list_expenses(
        self,
        request: AuthenticatedRequest,
        event_uid: UUID,
    ):
        return self.service.list_expenses(user=request.user, event_uid=event_uid)

    @get(
        "/{expense_uid}",
        response=ExpenseResponse,
        exceptions=(ExpenseNotFound, GetIsDenied),
    )
    def get_expense(self, request: AuthenticatedRequest, expense_uid: UUID):
        return self.service.get_expense(user=request.user, expense_uid=expense_uid)

    @put(
        "/{expense_uid}",
        response=ExpenseResponse,
        exceptions=(ExpenseNotFound, UpdatedIsDenied),
    )
    def update_expense(
        self,
        request: AuthenticatedRequest,
        expense_uid: UUID,
        payload: ExpenseUpdateRequest,
    ):
        return self.service.update_expense(
            user=request.user, expense_uid=expense_uid, payload=payload
        )

    @delete(
        "/{expense_uid}", response=bool, exceptions=(ExpenseNotFound, DeleteIsDenied)
    )
    def delete_expense(self, request: AuthenticatedRequest, expense_uid: UUID):
        return self.service.delete_expense(user=request.user, expense_uid=expense_uid)
