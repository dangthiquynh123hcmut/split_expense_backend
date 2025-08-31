# class ExpenseAPI:
#     def __init__(self, service:Service):
#         self.service = service

#     @api(prefix_or_class="expenses", tags=["Expense"], auth=AuthBear(), permissions=[IsAuthenticated])
#     class ExpenseAPI(Controller):
#         def __init__(self, service:Service):
#             self.service = service

#     @post("", response=ExpenseResponse, exceptions=(ExpenseNameAlreadyExists,))
#     def create_expense(self, request: AuthenticatedRequest, data: ExpenseRequest):
#         return self.service.create_expense(leader=request.user, data=data)

#     @get("", response=ExpenseResponse, paginate=True)
#     @paginate
#     def list_expenses(self, request: AuthenticatedRequest, filter: FilterExpenseSchema, order_by: OrderByExpenseSchema):
#         return self.service.list_expenses(user_uid=request.user.uid, filter=filter, order_by=order_by)

#     @delete("/{expense_uid}", response=bool, exceptions=(ExpenseNotFound,))
#     def delete_expense(self, expense_uid: UUID):
#         return self.service.delete_expense(expense_uid=expense_uid)

#     @get("/{expense_uid}", response=ExpenseResponse, exceptions=(ExpenseNotFound,))
#     def get_expense(self, expense_uid: UUID):
#         return self.service.get_expense(expense_uid=expense_uid)

#     @put("/{expense_uid}", response=ExpenseResponse, exceptions=(ExpenseNotFound,))
#     def update_expense(self, expense_uid: UUID, data: ExpenseUpdateRequest):
#         return self.service.update_expense(expense_uid=expense_uid, data=data)

#     @post("/{expense_uid}/join", response=bool, exceptions=(ExpenseNotFound,))
#     def join_expense(self, expense_uid: UUID):
#         return self.service.join_expense(expense_uid=expense_uid)

#     @post("/{expense_uid}/leave", response=bool, exceptions=(ExpenseNotFound,))
#     def leave_expense(self, expense_uid: UUID):
#         return self.service.leave_expense(expense_uid=expense_uid)

#     @get("/{expense_uid}/members", response=UserResponse, paginate=True)
#     @paginate
#     def list_expense_members(self, expense_uid: UUID):
#         return self.service.list_expense_members(expense_uid=expense_uid)
