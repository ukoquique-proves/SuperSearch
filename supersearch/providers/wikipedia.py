from __future__ import annotations

import re

import httpx

from supersearch.config import Config
from supersearch.models import SearchResult
from supersearch.providers.base import SearchProvider


def strip_html_tags(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text)


class WikipediaProvider(SearchProvider):
    name = "wikipedia"

    @property
    def independent(self) -> bool:
        return True

    def __init__(self, config: Config) -> None:
        self._timeout = config.timeout

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                "https://en.wikipedia.org/w/rest.php/v1/search/page",
                params={
                    "q": query,
                    "limit": max_results,
                },
                headers={
                    "User-Agent": "SuperSearch/1.0 (research tool; contact@supersearch.org)"
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        pages = data.get("pages") or []
        for i, page in enumerate(pages):
            key = page.get("key")
            if not key:
                continue
            url = f"https://en.wikipedia.org/wiki/{key}"
            title = page.get("title") or ""
            excerpt = page.get("excerpt") or ""
            description = page.get("description") or ""

            snippet = description
            clean_excerpt = strip_html_tags(excerpt).strip()
            if clean_excerpt:
                if snippet:
                    snippet += f" — {clean_excerpt}"
                else:
                    snippet = clean_excerpt

            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source=self.name,
                    rank=i,
                    providers=frozenset({self.name}),
                )
            )
        return results
