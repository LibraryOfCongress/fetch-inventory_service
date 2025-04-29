from typing import TypeVar
from fastapi import Query
from fastapi_pagination import Page
from fastapi_pagination.customization import CustomizedPage, UseParamsFields


T = TypeVar("T")
default_page_size = 50
maximum_allowed_page_size = 500

RequestListPagination = CustomizedPage[
    Page[T],
    UseParamsFields(size=Query(default=default_page_size, le=maximum_allowed_page_size))
]
