"""
Common Pydantic Schemas and Generic Response Envelopes.
"""
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, Any

T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    error: Optional[str] = None
    code: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
