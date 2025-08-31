# class Query:

#     @staticmethod
#     def create_expense(leader: TUser, name: str, avatar_url: Optional[str]):
#         return Expense.objects.create(leader=leader, name=name, avatar_url=avatar_url)

#     @staticmethod
#     def create_expense_members(expense: Expense, members: List[UUID]):
#         members = [
#             ExpenseMember(
#                 expense=expense,
#                 user=User.objects.get(uid=member_uid)
#             )
#             for member_uid in members
#         ]
#         ExpenseMember.objects.bulk_create(members)
#         return

#     @staticmethod
#     def list_expenses(user_uid: UUID, filter: FilterExpenseSchema, order_by: OrderByExpenseSchema):
#         queryset = Expense.objects.filter(
#             expense_member_fk_expense__user__uid=user_uid,
#             status="ACTIVE"
#         ).distinct()

#         if filter:
#             queryset = queryset.filter(filter.get_filter_expression())

#         if order_by:
#             queryset = queryset.order_by(order_by.get_order_by_expression())

#         return queryset

#     @staticmethod
#     def get_expense(expense_id: UUID):
#         return Expense.objects.filter(uid=expense_id, status="ACTIVE").first()

#     @staticmethod
#     def update_expense(expense_id: UUID, data: ExpenseUpdateRequest):
#         return Expense.objects.filter(uid=expense_id, status="ACTIVE").update(**data.dict())

#     @staticmethod
#     def leave_expense(user: TUser, expense_uid: UUID):
#         return ExpenseMember.objects.filter(user_uid=user.uid, expense_uid=expense_uid).update(status="DELETED")

#     @staticmethod
#     def delete_expense(expense_id: UUID):
#         return Expense.objects.filter(uid=expense_id).update(status="DELETED")

#     @staticmethod
#     def list_expense_members(expense_uid: UUID):
#         return ExpenseMember.objects.filter(expense_uid=expense_uid, status="ACTIVE")

#     @staticmethod
#     def get_detail_expense(expense_uid: UUID):
#         return Expense.objects.filter(uid=expense_uid, status="ACTIVE").first()

#     @staticmethod
#     def join_expense(user: TUser, expense_uid: UUID):
#         return ExpenseMember.objects.filter(user_uid=user.uid, expense_uid=expense_uid).update(status="ACTIVE")

#     @staticmethod
#     def get_detail_expense(expense_uid: UUID):
#         return Expense.objects.filter(uid=expense_uid, status="ACTIVE").first()
