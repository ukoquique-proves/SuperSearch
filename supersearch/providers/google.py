from __future__ import annotations

import httpx

from supersearch.config import Config
from supersearch.models import SearchResult
from supersearch.providers.base import SearchProvider


class GoogleCSEProvider(SearchProvider):
    name = "google_cse"

    def __init__(self, config: Config) -> None:
        self._key = config.google_api_key
        self._cx = config.google_cx
        self._timeout = config.timeout

    @property
    def enabled(self) -> bool:
        return bool(self._key and self._cx)

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        if not self.enabled:
            return []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": self._key,
                    "cx": self._cx,
                    "q": query,
                    "num": min(max_results, 10),
                },
            )
            resp.raise_for_status()
            data = resp.json()
        results: list[SearchResult] = []
        for i, row in enumerate(data.get("items", [])):
            results.append(
                SearchResult(
                    title=row.get("title") or "",
                    url=row.get("link") or "",
                    snippet=row.get("snippet") or "",
                    source=self.name,
                    rank=i,
                    providers=frozenset({self.name}),
                )
            )
        return results
