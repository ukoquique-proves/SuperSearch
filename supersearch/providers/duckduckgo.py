from __future__ import annotations

import asyncio

from ddgs import DDGS

from supersearch.models import SearchResult
from supersearch.providers.base import SearchProvider


class DuckDuckGoProvider(SearchProvider):
    name = "duckduckgo"

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        return await asyncio.to_thread(self._search_sync, query, max_results)

    def _search_sync(self, query: str, max_results: int) -> list[SearchResult]:
        out: list[SearchResult] = []
        seen: set[str] = set()
        with DDGS() as ddgs:
            for row in ddgs.text(query, max_results=max_results):
                url = row.get("href") or ""
                if not url or url in seen:
                    continue
                seen.add(url)
                out.append(
                    SearchResult(
                        title=row.get("title") or "",
                        url=url,
                        snippet=row.get("body") or "",
                        source=row.get("source") or self.name,
                        rank=len(out),
                        providers=frozenset({self.name}),
                    )
                )
        return out


class DuckDuckGoNewsProvider(SearchProvider):
    name = "duckduckgo_news"

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        return await asyncio.to_thread(self._search_sync, query, max_results)

    def _search_sync(self, query: str, max_results: int) -> list[SearchResult]:
        out: list[SearchResult] = []
        with DDGS() as ddgs:
            for i, row in enumerate(ddgs.news(query, max_results=max_results)):
                url = row.get("url") or row.get("href") or ""
                if not url:
                    continue
                out.append(
                    SearchResult(
                        title=row.get("title") or "",
                        url=url,
                        snippet=row.get("body") or row.get("excerpt") or "",
                        source=row.get("source") or self.name,
                        rank=i,
                        providers=frozenset({self.name}),
                    )
                )
        return out
