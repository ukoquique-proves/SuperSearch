from __future__ import annotations

import httpx

from supersearch.config import Config
from supersearch.models import SearchResult
from supersearch.providers.base import SearchProvider


class HackerNewsProvider(SearchProvider):
    """Hacker News search via Algolia API — free, no key required."""

    name = "hacker_news"

    @property
    def independent(self) -> bool:
        return True

    def __init__(self, config: Config) -> None:
        self._timeout = config.timeout

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                "https://hn.algolia.com/api/v1/search",
                params={
                    "query": query,
                    "hitsPerPage": max_results,
                    "tags": "story",
                },
                headers={"User-Agent": "SuperSearch/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        for i, hit in enumerate(data.get("hits", [])):
            # Prefer the external URL; fall back to the HN discussion page
            url = hit.get("url") or ""
            object_id = hit.get("objectID") or ""
            if not url and object_id:
                url = f"https://news.ycombinator.com/item?id={object_id}"
            if not url:
                continue
            title = hit.get("title") or hit.get("story_title") or ""
            snippet = hit.get("story_text") or hit.get("comment_text") or ""
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:500],
                    source=self.name,
                    rank=i,
                    providers=frozenset({self.name}),
                )
            )
        return results
