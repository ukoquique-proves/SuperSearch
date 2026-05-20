from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse, urlunparse


@dataclass(frozen=True, slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    rank: int = 0
    providers: frozenset[str] = field(default_factory=frozenset)

    def with_provider(self, provider: str) -> SearchResult:
        merged = frozenset(self.providers) | {provider}
        return SearchResult(
            title=self.title,
            url=self.url,
            snippet=self.snippet,
            source=self.source,
            rank=self.rank,
            providers=merged,
        )


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        parsed = urlparse("https://" + url.strip())
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/") or ""
    return urlunparse((parsed.scheme.lower(), host, path, "", parsed.query, ""))
