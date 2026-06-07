from __future__ import annotations

import httpx

from supersearch.config import Config
from supersearch.models import SearchResult
from supersearch.providers.base import SearchProvider


class InternetArchiveProvider(SearchProvider):
    """Archived pages and documents Google often surfaces weakly."""

    name = "internet_archive"

    @property
    def independent(self) -> bool:
        return True

    def __init__(self, config: Config) -> None:
        self._timeout = config.timeout

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                "https://archive.org/advancedsearch.php",
                params={
                    "q": f"({query}) AND mediatype:texts",
                    "fl[]": ["identifier", "title", "description"],
                    "rows": max_results,
                    "output": "json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        for i, doc in enumerate(data.get("response", {}).get("docs", [])):
            ident = doc.get("identifier") or ""
            if not ident:
                continue
            title = doc.get("title") or ident
            if isinstance(title, list):
                title = title[0] if title else ident
            desc = doc.get("description") or ""
            if isinstance(desc, list):
                desc = " ".join(str(x) for x in desc[:2])
            url = f"https://archive.org/details/{ident}"
            results.append(
                SearchResult(
                    title=str(title),
                    url=url,
                    snippet=str(desc)[:500],
                    source=self.name,
                    rank=i,
                    providers=frozenset({self.name}),
                )
            )
        return results
