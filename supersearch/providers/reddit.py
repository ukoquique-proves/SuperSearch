from __future__ import annotations

import httpx

from supersearch.config import Config
from supersearch.models import SearchResult
from supersearch.providers.base import SearchProvider


class RedditProvider(SearchProvider):
    """Reddit post search using the public JSON API — free, no OAuth required."""

    name = "reddit"

    def __init__(self, config: Config) -> None:
        self._timeout = config.timeout

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        async with httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=True,
            headers={
                # Reddit blocks generic User-Agent strings
                "User-Agent": "SuperSearch/1.0 (open-source research tool; +https://github.com/supersearch)",
            },
        ) as client:
            resp = await client.get(
                "https://www.reddit.com/search.json",
                params={
                    "q": query,
                    "limit": max_results,
                    "sort": "relevance",
                    "type": "link",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        children = data.get("data", {}).get("children", [])
        for i, child in enumerate(children):
            post = child.get("data", {})
            permalink = post.get("permalink") or ""
            url = post.get("url") or (f"https://www.reddit.com{permalink}" if permalink else "")
            if not url:
                continue
            title = post.get("title") or ""
            snippet = post.get("selftext") or ""
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
