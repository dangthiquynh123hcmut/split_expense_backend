from uuid import UUID

from authenticate.api import AuthenticatedRequest
from event.services import Service as EventService
from exceptions.event import EventNotFound
from exceptions.expense import ExpenseNotFound
from exceptions.users import UserNotFound
from expense.schemas.request import ExpenseRequest
from expense.schemas.response import CreateExpense, ExpenseResponse, NameExpense
from expense.service import Service
from utils.exceptions import GetIsDenied
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
    def __init__(self):
        self.service = Service()
        self.event_service = EventService()

    @post(
        "",
        response=CreateExpense,
        exceptions=(EventNotFound, UserNotFound),
    )
    def create_expense(self, request: AuthenticatedRequest, payload: ExpenseRequest):
        event = self.event_service.query.get_event(event_uid=payload.event_uid)
        if not event:
            raise EventNotFound
        expense = self.service.create_expense(
            creator=request.user, payload=payload, event=event
        )
        self.service.calculate_debt(event=event)
        return expense

    @get(
        "/{expense_uid}",
        response=ExpenseResponse,
        exceptions=(ExpenseNotFound, GetIsDenied),
    )
    def get_expense_detail(self, request: AuthenticatedRequest, expense_uid: UUID):
        return self.service.get_expense_detail(
            user=request.user, expense_uid=expense_uid
        )

    @put(
        "/{expense_uid}",
        response=CreateExpense,
        exceptions=(ExpenseNotFound,),
    )
    def update_expense(
        self,
        request: AuthenticatedRequest,
        expense_uid: UUID,
        payload: ExpenseRequest,
    ):
        expense = self.service.update_expense(
            user=request.user, expense_uid=expense_uid, payload=payload
        )
        self.service.calculate_debt(event=expense.event)
        return expense

    @put("/{expense_uid}/restore", response=bool, exceptions=(ExpenseNotFound,))
    def restore_expense(self, expense_uid: UUID):
        expense = self.service.restore_expense(expense_uid=expense_uid)
        self.service.calculate_debt(event=expense.event)
        return True

    @put("/{expense_uid}/soft", response=bool, exceptions=(ExpenseNotFound,))
    def soft_delete_expense(self, expense_uid: UUID):
        event = self.service.soft_delete_expense(expense_uid=expense_uid)
        self.service.calculate_debt(event=event)
        return True

    @delete("/{expense_uid}/hard", response=bool, exceptions=(ExpenseNotFound,))
    def hard_delete_expense(self, expense_uid: UUID):
        return self.service.hard_delete_expense(expense_uid=expense_uid)


@api(
    prefix_or_class="list-expenses",
    tags=["Expense"],
    auth=AuthBear(),
    permissions=[IsAuthenticated],
)
class ListExpenseAPI(Controller):
    def __init__(self):
        self.service = Service()

    @get(
        "/{event_uid}/event",
        response=NameExpense,
        paginate=True,
        exceptions=(EventNotFound, GetIsDenied),
    )
    @paginate
    def list_expenses_in_event(
        self,
        request: AuthenticatedRequest,
        event_uid: UUID,
    ):
        return self.service.list_expenses_in_event(
            user=request.user, event_uid=event_uid
        )
