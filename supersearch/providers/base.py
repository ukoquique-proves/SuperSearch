from __future__ import annotations

from abc import ABC, abstractmethod

from supersearch.models import SearchResult


class SearchProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        ...

    @property
    def enabled(self) -> bool:
        return True
