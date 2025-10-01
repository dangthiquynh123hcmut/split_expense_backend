from collections import OrderedDict
from typing import Any, Generic, List, Type, TypeVar, get_args, get_origin

from django.core.paginator import Paginator
from ninja import Schema
from ninja.pagination import PaginationBase
from ninja_extra.pagination import paginate as ninja_paginate
from pydantic import BaseModel


T = TypeVar("T")
U = TypeVar("U")


class PaginatedResponseSchema(BaseModel, Generic[T]):
    content: List[T]
    current_page: int
    page_size: int
    total_rows: int
    total_pages: int


class NestedPaginatedResponseSchema(BaseModel, Generic[T, U]):
    content: List[T]
    current_page: int
    page_size: int
    total_rows: int
    total_pages: int


class InnerPaginatedResponse(BaseModel, Generic[U]):
    content: List[U]
    inner_current_page: int
    inner_page_size: int
    inner_total_rows: int
    inner_total_pages: int


class Pagination(PaginationBase):
    items_attribute: str = "content"
    page_query_param = "page"
    page_size_query_param = "page_size"

    class Input(Schema):
        page_size: int = 20
        page: int = 1

    def paginate_queryset(self, queryset: Any, pagination: Input, **params: Any):
        paginator = Paginator(queryset, pagination.page_size)

        total_pages = paginator.num_pages

        if int(total_pages) < pagination.page:
            page_number = pagination.page
            content = []
        else:
            current_page = paginator.page(pagination.page)
            page_number = current_page.number
            content = list(current_page)

        total = paginator.count

        return OrderedDict(
            [
                ("content", content),
                ("total_rows", total),
                ("total_pages", total_pages),
                ("current_page", page_number),
                ("page_size", pagination.page_size),
            ]
        )

    @classmethod
    def get_response_schema(cls, response_schema: Type[Schema]):
        return PaginatedResponseSchema[response_schema]  # type: ignore


class NestedPagination(PaginationBase):
    items_attribute: str = "items"

    class Input(Schema):
        page: int = 1
        page_size: int = 2
        inner_page: int = 1
        inner_page_size: int = 10

    def paginate_queryset(self, queryset: Any, pagination: Input, **params: Any):
        outer_paginator = Paginator(queryset, pagination.page_size)
        outer_content: list[Any] = []
        if pagination.page > outer_paginator.num_pages:
            current_page_number = pagination.page
        else:
            outer_page_obj = outer_paginator.page(pagination.page)
            current_page_number = outer_page_obj.number
            for obj in outer_page_obj:
                inner_list = getattr(obj, self.items_attribute, [])
                inner_paginator = Paginator(
                    inner_list.content,  # type: ignore
                    pagination.inner_page_size,
                )
                if pagination.inner_page > inner_paginator.num_pages:
                    inner_content = []
                    inner_current_page_number = pagination.inner_page
                else:
                    inner_page_obj = inner_paginator.page(pagination.inner_page)
                    inner_content = list(inner_page_obj)
                    inner_current_page_number = inner_page_obj.number
                inner_pagination_data = {
                    "content": inner_content,
                    "inner_current_page": inner_current_page_number,
                    "inner_page_size": pagination.inner_page_size,
                    "inner_total_rows": inner_paginator.count,
                    "inner_total_pages": inner_paginator.num_pages,
                }

                obj_dict = obj.__dict__
                obj_dict[self.items_attribute] = inner_pagination_data
                outer_content.append(obj_dict)

        return OrderedDict(
            [
                ("content", outer_content),
                ("current_page", current_page_number),
                ("page_size", pagination.page_size),
                ("total_rows", outer_paginator.count),
                ("total_pages", outer_paginator.num_pages),
            ]
        )

    @classmethod
    def get_response_schema(cls, response_schema: Type[BaseModel]):
        inner_schema = None

        if get_origin(response_schema) is list:
            args = get_args(response_schema)
            if args:
                inner_schema = args[0]
        elif hasattr(response_schema, "__annotations__"):
            for attr in ("items", "results", "members"):
                if attr in response_schema.__annotations__:
                    args = get_args(response_schema.__annotations__[attr])
                    if args:
                        inner_schema = args[0]
                    else:
                        inner_schema = response_schema.__annotations__[attr]
                    break

        if inner_schema is None:
            inner_schema = response_schema

        return NestedPaginatedResponseSchema[response_schema, inner_schema]  # type: ignore


paginate = ninja_paginate(Pagination)
nested_paginate = ninja_paginate(NestedPagination)
