from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Réponse paginée uniforme de tous les endpoints de liste."""

    items: list[T]
    total: int
    page: int
    page_size: int
