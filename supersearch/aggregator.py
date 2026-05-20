from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import replace

import httpx

from supersearch.cache import SearchCache
from supersearch.config import Config
from supersearch.models import SearchResult, normalize_url
from supersearch.providers import build_providers
from supersearch.providers.base import SearchProvider

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # seconds; doubles each attempt


class SuperSearchAggregator:
    """Query many backends in parallel, merge by URL, boost cross-provider hits."""

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or Config.from_env()
        self._providers = [p for p in build_providers(self._config) if p.enabled]
        self._cache = SearchCache()

    @property
    def active_providers(self) -> list[str]:
        return [p.name for p in self._providers]

    async def search(
        self,
        query: str,
        *,
        max_results: int = 25,
        per_provider: int = 15,
    ) -> list[SearchResult]:
        if not query.strip():
            return []

        cached = self._cache.get(query, per_provider)
        if cached is not None:
            logger.info("Cache hit for query: %s", query)
            return cached[:max_results]

        async def _timed_safe_search(provider: SearchProvider, q: str, max_res: int) -> list[SearchResult]:
            try:
                return await asyncio.wait_for(
                    self._safe_search(provider, q, max_res),
                    timeout=self._config.timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("%s timed out after %.1fs", provider.name, self._config.timeout)
                return []

        tasks = [
            _timed_safe_search(provider, query, per_provider)
            for provider in self._providers
        ]
        batches = await asyncio.gather(*tasks)
        merged = self._merge(batches)
        results = merged[:max_results]
        if results:
            self._cache.set(query, per_provider, results)
        return results

    async def _safe_search(
        self,
        provider: SearchProvider,
        query: str,
        max_results: int,
    ) -> list[SearchResult]:
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                rows = await provider.search(query, max_results)
                logger.info("%s returned %d results", provider.name, len(rows))
                return rows
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    delay = _RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "%s rate-limited (429), retrying in %.1fs (attempt %d/%d)",
                        provider.name, delay, attempt + 1, _MAX_RETRIES,
                    )
                    await asyncio.sleep(delay)
                    last_exc = exc
                else:
                    logger.warning("%s failed with HTTP %d: %s", provider.name, exc.response.status_code, exc)
                    return []
            except Exception as exc:
                logger.warning("%s failed: %s", provider.name, exc)
                return []
        logger.warning("%s gave up after %d retries: %s", provider.name, _MAX_RETRIES, last_exc)
        return []

    def _merge(self, batches: list[list[SearchResult]]) -> list[SearchResult]:
        by_url: dict[str, SearchResult] = {}
        best_rank: dict[str, float] = {}

        for batch in batches:
            for row in batch:
                key = normalize_url(row.url)
                if not key or not row.url:
                    continue
                existing = by_url.get(key)
                if existing is None:
                    by_url[key] = row
                    best_rank[key] = self._score(row, provider_count=1)
                else:
                    combined_providers = existing.providers | row.providers
                    snippet = existing.snippet if len(existing.snippet) >= len(row.snippet) else row.snippet
                    title = existing.title if len(existing.title) >= len(row.title) else row.title
                    merged = replace(
                        existing,
                        title=title,
                        snippet=snippet,
                        rank=min(existing.rank, row.rank),
                        providers=combined_providers,
                    )
                    by_url[key] = merged
                    best_rank[key] = self._score(merged, provider_count=len(combined_providers))

        ordered = sorted(by_url.values(), key=lambda r: best_rank[normalize_url(r.url)], reverse=True)
        return ordered

    @staticmethod
    def _score(row: SearchResult, provider_count: int) -> float:
        # log-scale diversity so cross-provider boost is meaningful but doesn't drown rank/snippet
        rank_bonus = 1.0 / (1 + row.rank)
        diversity = math.log1p(provider_count)
        snippet_bonus = min(len(row.snippet), 300) / 300.0
        return diversity + rank_bonus + snippet_bonus
