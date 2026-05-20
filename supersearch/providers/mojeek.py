from __future__ import annotations

import httpx

from supersearch.config import Config
from supersearch.models import SearchResult
from supersearch.providers.base import SearchProvider


class MojeekProvider(SearchProvider):
    """Mojeek search provider — optional, requires API key."""

    name = "mojeek"

    def __init__(self, config: Config) -> None:
        self._key = config.mojeek_api_key
        self._timeout = config.timeout

    @property
    def enabled(self) -> bool:
        return bool(self._key)

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        if not self.enabled:
            return []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                "https://api.mojeek.com/search",
                params={
                    "q": query,
                    "api_key": self._key,
                    "fmt": "json",
                },
                headers={"User-Agent": "SuperSearch/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        # Mojeek JSON response structure: {"results": [{"title": "...", "url": "...", "snippet": "..."}, ...]}
        for i, hit in enumerate(data.get("results", [])):
            url = hit.get("url")
            if not url:
                continue
            results.append(
                SearchResult(
                    title=hit.get("title") or "",
                    url=url,
                    snippet=hit.get("snippet") or "",
                    source=self.name,
                    rank=i,
                    providers=frozenset({self.name}),
                )
            )
            if len(results) >= max_results:
                break
        return results
