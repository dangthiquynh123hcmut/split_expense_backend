# class Service:
#     def __init__(self):
#         self.query = Query()

#     def create_expense(self, leader: TUser, data: ExpenseRequest):
#         expense = self.query.create_expense(leader=leader, name=data.name, avatar_url=data.avatar_url)
#         self.query.create_expense_members(expense=expense, members=data.list_user_uid)
#         return expense

#     def list_expenses(self, user: TUser, filter: FilterExpenseSchema, order_by: OrderByExpenseSchema):
#         return self.query.list_expenses(user=user, filter=filter, order_by=order_by)

#     def get_expense(self, expense_id: UUID):
#         return self.query.get_expense(expense_id=expense_id)

#     def update_expense(self, expense_id: UUID, data: ExpenseUpdateRequest):
#         return self.query.update_expense(expense_id=expense_id, data=data)

#     def leave_expense(self, user: TUser, expense_uid: UUID):
#         return self.query.leave_expense(user=user, expense_uid=expense_uid)

#     def delete_expense(self, expense_id: UUID):
#         return self.query.delete_expense(expense_id=expense_id)

#     def list_expense_members(self, expense_uid: UUID):
#         return self.query.list_expense_members(expense_uid=expense_uid)

#     def get_detail_expense(self, expense_uid: UUID):
#         return self.query.get_detail_expense(expense_uid=expense_uid)

#     def join_expense(self, user: TUser, expense_uid: UUID):
#         return self.query.join_expense(user=user, expense_uid=expense_uid)

#     def get_detail_expense(self, expense_uid: UUID):
#         return self.query.get_detail_expense(expense_uid=expense_uid)
