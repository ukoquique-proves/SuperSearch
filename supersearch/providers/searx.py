from __future__ import annotations

import asyncio

import httpx

from supersearch.config import Config
from supersearch.models import SearchResult, normalize_url
from supersearch.providers.base import SearchProvider


class SearXProvider(SearchProvider):
    """Meta-search: queries all SearX instances in parallel and merges results."""

    name = "searx"

    def __init__(self, config: Config) -> None:
        self._instances = config.searx_instances
        self._timeout = config.timeout

    @property
    def enabled(self) -> bool:
        return bool(self._instances)

    async def _fetch_dynamic_instances(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("https://searx.space/data/instances.json")
                if resp.status_code == 200:
                    data = resp.json()
                    instances = data.get("instances", {})
                    working = []
                    for name, info in instances.items():
                        http = info.get("http") or {}
                        if http.get("status_code") == 200 and not http.get("error"):
                            uptime = (info.get("uptime") or {}).get("uptimeDay", 0) or 0
                            if uptime >= 95.0:
                                working.append((name, uptime))
                    working.sort(key=lambda x: x[1], reverse=True)
                    return [name.rstrip("/") for name, _ in working[:5]]
        except Exception:
            pass
        return []

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        async with httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=True,
            headers={"User-Agent": "SuperSearch/1.0 (research tool; contact@supersearch.org)"},
        ) as client:
            results_dict = {}
            statuses = {}

            async def run_instance(base: str):
                try:
                    res = await self._query_instance(client, base, query, max_results)
                    results_dict[base] = res
                    statuses[base] = 200
                except httpx.HTTPStatusError as exc:
                    statuses[base] = exc.response.status_code
                    results_dict[base] = []
                except Exception:
                    statuses[base] = 500
                    results_dict[base] = []

            if self._instances:
                await asyncio.gather(*[run_instance(base) for base in self._instances])

            merged_batches = [res for base, res in results_dict.items() if res]
            had_429 = any(code == 429 for code in statuses.values())

            # Fallback if no instances returned results
            if not merged_batches:
                dynamic_instances = await self._fetch_dynamic_instances()
                if dynamic_instances:
                    results_dict_fallback = {}
                    statuses_fallback = {}

                    async def run_fallback_instance(base: str):
                        try:
                            res = await self._query_instance(client, base, query, max_results)
                            results_dict_fallback[base] = res
                            statuses_fallback[base] = 200
                        except httpx.HTTPStatusError as exc:
                            statuses_fallback[base] = exc.response.status_code
                            results_dict_fallback[base] = []
                        except Exception:
                            statuses_fallback[base] = 500
                            results_dict_fallback[base] = []

                    await asyncio.gather(*[run_fallback_instance(base) for base in dynamic_instances])
                    merged_batches = [res for base, res in results_dict_fallback.items() if res]
                    had_429 = had_429 or any(code == 429 for code in statuses_fallback.values())

            if not merged_batches and had_429:
                request = httpx.Request("GET", "https://searx.space")
                response = httpx.Response(429, request=request)
                raise httpx.HTTPStatusError("SearX all instances rate limited (429)", request=request, response=response)

        seen: set[str] = set()
        merged: list[SearchResult] = []
        for batch in merged_batches:
            for row in batch:
                key = normalize_url(row.url)
                if key and key not in seen:
                    seen.add(key)
                    merged.append(row)

        return [
            SearchResult(
                title=r.title,
                url=r.url,
                snippet=r.snippet,
                source=r.source,
                rank=i,
                providers=r.providers,
            )
            for i, r in enumerate(merged[:max_results])
        ]

    async def _query_instance(
        self,
        client: httpx.AsyncClient,
        base: str,
        query: str,
        max_results: int,
    ) -> list[SearchResult]:
        resp = await client.get(
            f"{base}/search",
            params={"q": query, "format": "json", "language": "auto"},
        )
        resp.raise_for_status()
        data = resp.json()
        results: list[SearchResult] = []
        for i, row in enumerate(data.get("results", [])[:max_results]):
            url = row.get("url") or ""
            if not url:
                continue
            engines = row.get("engines") or []
            source = engines[0] if engines else self.name
            results.append(
                SearchResult(
                    title=row.get("title") or "",
                    url=url,
                    snippet=row.get("content") or "",
                    source=source,
                    rank=i,
                    providers=frozenset({self.name, *engines[:3]}),
                )
            )
        return results
