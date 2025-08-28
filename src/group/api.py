# from .services import Service
# from utils.router.controller import Controller, api, post, put,delete, get
# from utils.types import AuthenticatedRequest
# from utils.router.authenticate import AuthBear
# from utils.router.permissions import IsAuthenticated
# from utils.router.paginate import paginate
# from ninja import Query
# from .schemas.request import GroupRequest, GroupUpdateDTO, FilterGroupSchema, OrderByGroupSchema
# from .schemas.response import GroupResponse
# from utils.exceptions import GroupAlreadyExists, GroupNotFound
# @api(prefix_or_class="groups", tags=["Group"], auth=AuthBear(), permissions=[IsAuthenticated])
# class GroupAPI(Controller):
#     def __init__(self, service:Service):
#         self.service = service

#     @post("", response=GroupResponse, exceptions=(GroupAlreadyExists,))
#     def create_group(self, request: AuthenticatedRequest, data: GroupRequest):
#         return self.service.create_group(user=request.user, data=data)

#     @get("", response=list[GroupResponse], paginate=True)
#     @paginate
#     def list_groups(self,
#        request: AuthenticatedRequest,
#        filter: FilterGroupSchema = Query(...),
#        order_by: OrderByGroupSchema = Query(...),
#     ):
#         return self.service.list_groups(user_uid=request.user.uid,
#          filter=filter,
#           order_by=order_by)

#     @get("/{group_id}", response=GroupResponse, exceptions=(GroupNotFound,))
#     async def get_group(self, group_id: str):
#         return await Service.get_group(group_id)

#     @put("/{group_id}", response=GroupResponse, exceptions=(GroupNotFound,))
#     async def update_group(self, group_id: str, group_data: GroupUpdateDTO):
#         return await Service.update_group(group_id, group_data)

#     @delete("/{group_id}", response=bool, exceptions=(GroupNotFound,))
#     async def delete_group(self, group_id: str):
#         return await Service.delete_group(group_id)
