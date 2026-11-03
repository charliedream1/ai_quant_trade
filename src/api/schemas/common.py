"""Shared response helpers."""

from typing import Any

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    code: int = 0
    message: str = ""
    data: Any = None


class PageQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


def ok(data: Any = None, message: str = "") -> dict[str, Any]:
    return {"code": 0, "message": message, "data": data}


def page(items: list[dict[str, Any]], total: int, page_no: int, page_size: int) -> dict[str, Any]:
    return {"items": items, "page": page_no, "page_size": page_size, "total": total}
