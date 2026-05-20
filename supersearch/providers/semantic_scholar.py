from __future__ import annotations

import httpx

from supersearch.config import Config
from supersearch.models import SearchResult
from supersearch.providers.base import SearchProvider


class SemanticScholarProvider(SearchProvider):
    """Academic papers — often missed by generic web search."""

    name = "semantic_scholar"

    def __init__(self, config: Config) -> None:
        self._timeout = config.timeout
        self._api_key = config.semantic_scholar_api_key

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        headers: dict[str, str] = {"User-Agent": "SuperSearch/1.0 (research tool)"}
        if self._api_key:
            headers["x-api-key"] = self._api_key

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={
                    "query": query,
                    "limit": max_results,
                    "fields": "title,abstract,url,externalIds,year",
                },
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        for i, paper in enumerate(data.get("data", [])):
            url = paper.get("url") or ""
            ext = paper.get("externalIds") or {}
            if not url and ext.get("DOI"):
                url = f"https://doi.org/{ext['DOI']}"
            if not url:
                continue
            year = paper.get("year")
            title = paper.get("title") or "Untitled paper"
            if year:
                title = f"{title} ({year})"
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=(paper.get("abstract") or "")[:500],
                    source=self.name,
                    rank=i,
                    providers=frozenset({self.name}),
                )
            )
        return results
