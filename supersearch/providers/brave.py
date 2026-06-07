from __future__ import annotations

import httpx

from supersearch.config import Config
from supersearch.models import SearchResult
from supersearch.providers.base import SearchProvider


class BraveProvider(SearchProvider):
    name = "brave"

    @property
    def independent(self) -> bool:
        return True

    def __init__(self, config: Config) -> None:
        self._key = config.brave_api_key
        self._timeout = config.timeout

    @property
    def enabled(self) -> bool:
        return bool(self._key)

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        if not self._key:
            return []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": max_results},
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self._key,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        results: list[SearchResult] = []
        for i, row in enumerate(data.get("web", {}).get("results", [])):
            results.append(
                SearchResult(
                    title=row.get("title") or "",
                    url=row.get("url") or "",
                    snippet=row.get("description") or "",
                    source=self.name,
                    rank=i,
                    providers=frozenset({self.name}),
                )
            )
        return results
