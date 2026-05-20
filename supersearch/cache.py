from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

from supersearch.models import SearchResult


class SearchCache:
    """Simple on-disk JSON cache for search results with TTL."""

    def __init__(self, cache_dir: str = ".search_cache", ttl: int = 3600) -> None:
        self.cache_dir = cache_dir
        self.ttl = ttl
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _get_cache_path(self, query: str, per_provider: int) -> str:
        key = f"{query}:{per_provider}"
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_key}.json")

    def get(self, query: str, per_provider: int) -> list[SearchResult] | None:
        path = self._get_cache_path(query, per_provider)
        if not os.path.exists(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if time.time() - data["timestamp"] > self.ttl:
                return None

            return [
                SearchResult(
                    title=r["title"],
                    url=r["url"],
                    snippet=r["snippet"],
                    source=r["source"],
                    rank=r["rank"],
                    providers=frozenset(r["providers"]),
                )
                for r in data["results"]
            ]
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def set(self, query: str, per_provider: int, results: list[SearchResult]) -> None:
        path = self._get_cache_path(query, per_provider)
        data = {
            "timestamp": time.time(),
            "query": query,
            "per_provider": per_provider,
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source,
                    "rank": r.rank,
                    "providers": list(r.providers),
                }
                for r in results
            ],
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
