from typing import List, Literal
from uuid import UUID

from ninja import Query

from authenticate.api import AuthenticatedRequest
from event.services import Service as EventService
from exceptions.event import EventClosed, EventNotFound
from exceptions.expense import ExpenseNotFound, ListMemberNotMatch
from exceptions.users import UserNotFound
from expense.schemas.request import ExpenseRequest, UpdateExpenseRequest
from expense.schemas.response import (
    CreateExpense,
    ExpenseResponse,
    ListExpenseUser,
    NameExpense,
)
from expense.service import Service
from group.schemas.response import GroupChart
from utils.exceptions import GetIsDenied
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, delete, get, post, put
from utils.router.paginate import paginate
from utils.router.permissions import IsAuthenticated
from utils.schemas.filter_and_order_by import (
    FilterAmountSchema,
    FilterDateSchema,
    FilterEventSchema,
)


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
        exceptions=(EventNotFound, EventClosed, UserNotFound, ListMemberNotMatch),
    )
    def create_expense(self, request: AuthenticatedRequest, payload: ExpenseRequest):
        event = self.event_service.query.get_event(event_uid=payload.event_uid)
        if not event:
            raise EventNotFound
        expense = self.service.create_expense(
            creator=request.user, payload=payload, event=event
        )
        self.service.calculate_debt(expense=expense, old_currency="")
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
        exceptions=(ExpenseNotFound, EventClosed, ListMemberNotMatch),
    )
    def update_expense(
        self,
        request: AuthenticatedRequest,
        expense_uid: UUID,
        payload: UpdateExpenseRequest,
    ):
        old_expense = self.service.get_expense(expense_uid=expense_uid, status="ACTIVE")
        if not old_expense:
            raise ExpenseNotFound
        expense = self.service.update_expense(
            user=request.user, expense_uid=expense_uid, payload=payload
        )
        self.service.calculate_debt(expense=expense, old_currency=old_expense.currency)
        return expense

    @put(
        "/{expense_uid}/restore",
        response=bool,
        exceptions=(ExpenseNotFound, EventClosed),
    )
    def restore_expense(self, request: AuthenticatedRequest, expense_uid: UUID):
        expense = self.service.restore_expense(
            user=request.user, expense_uid=expense_uid
        )
        self.service.calculate_debt(expense=expense, old_currency="")
        return True

    @put(
        "/{expense_uid}/soft", response=bool, exceptions=(ExpenseNotFound, EventClosed)
    )
    def soft_delete_expense(self, request: AuthenticatedRequest, expense_uid: UUID):
        expense = self.service.soft_delete_expense(
            user=request.user, expense_uid=expense_uid
        )
        self.service.calculate_debt(expense=expense, old_currency="")
        return True

    @delete("/{expense_uid}/hard", response=bool, exceptions=(ExpenseNotFound,))
    def hard_delete_expense(self, request: AuthenticatedRequest, expense_uid: UUID):
        return self.service.hard_delete_expense(
            user=request.user, expense_uid=expense_uid
        )


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
        status: Literal["DELETED", "ACTIVE"] = "ACTIVE",
    ):
        return self.service.list_expenses_in_event(
            user=request.user, event_uid=event_uid, status=status
        )

    @get(
        "/transaction",
        response=ListExpenseUser,
        paginate=True,
    )
    @paginate
    def list_expenses_by_user(
        self,
        request: AuthenticatedRequest,
        status: Literal["DELETED", "ACTIVE"] = "ACTIVE",
        filter: FilterDateSchema = Query(...),
        filter_amount: FilterAmountSchema = Query(...),
        filter_name: FilterEventSchema = Query(...),
    ):
        return self.service.list_expenses_by_user(
            user=request.user,
            status=status,
            filter=filter,
            filter_amount=filter_amount,
            filter_name=filter_name,
        )

    @get(
        "/transaction-chart",
        response=List[GroupChart],
    )
    def transaction_chart(
        self,
        request: AuthenticatedRequest,
        year: int,
    ):
        return self.service.transaction_chart(user=request.user, year=year)
