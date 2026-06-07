from __future__ import annotations

import asyncio
import pathlib

import httpx
import pytest

from supersearch.aggregator import SuperSearchAggregator
from supersearch.cache import SearchCache
from supersearch.config import Config
from supersearch.models import SearchResult, normalize_url
from supersearch.providers.base import SearchProvider


def _tmp_cache(tmp_path: pathlib.Path) -> SearchCache:
    """Return a fresh SearchCache backed by a pytest tmp_path — never hits disk state."""
    return SearchCache(cache_dir=str(tmp_path))


def test_normalize_url() -> None:
    assert normalize_url("https://www.google.com/") == "https://google.com"
    assert normalize_url("http://example.com/path/") == "http://example.com/path"
    assert normalize_url("example.com/path?q=1") == "https://example.com/path?q=1"
    assert normalize_url("HTTPS://SUB.DOMAIN.COM/A/B") == "https://sub.domain.com/A/B"


def test_score_calculation() -> None:
    # Score(R) = ln(1 + provider_count) + 1/(1 + rank) + min(len(snippet), 300)/300
    #          + 0.3 * independent_source_count
    res1 = SearchResult(
        title="Test Title",
        url="https://example.com",
        snippet="Short snippet",
        source="test",
        rank=0,
        independent_source_count=0,
    )
    score1 = SuperSearchAggregator._score(res1, provider_count=1)

    # provider_count=1 -> ln(2) ~= 0.693147
    # rank=0 -> 1/(1+0) = 1.0
    # snippet="Short snippet" -> len=13 -> 13/300 ~= 0.043333
    # independence = 0.3 * 0 = 0.0
    # Total ~= 0.693147 + 1.0 + 0.043333 + 0.0 = 1.73648
    assert abs(score1 - 1.73648) < 1e-4

    res2 = SearchResult(
        title="Test Title 2",
        url="https://example.com/2",
        snippet="x" * 400,  # Longer snippet (capped at 300/300 = 1.0)
        source="test",
        rank=9,  # worse rank -> 1/10 = 0.1
        independent_source_count=2,
    )
    score2 = SuperSearchAggregator._score(res2, provider_count=3)
    # provider_count=3 -> ln(4) ~= 1.386294
    # rank=9 -> 1/10 = 0.1
    # snippet length >= 300 -> 1.0
    # independence = 0.3 * 2 = 0.6
    # Total ~= 1.386294 + 0.1 + 1.0 + 0.6 = 3.08629
    assert abs(score2 - 3.08629) < 1e-4


def test_independence_scoring_boost() -> None:
    """Results confirmed by independent providers should score higher than identical
    results from Big-Tech-syndicated providers only."""

    # Same result, no independent sources
    no_indep = SearchResult(
        title="Same Title",
        url="https://example.com/page",
        snippet="A decent snippet with enough detail",
        source="test",
        rank=0,
        independent_source_count=0,
    )
    # Same result, 1 independent source
    one_indep = SearchResult(
        title="Same Title",
        url="https://example.com/page",
        snippet="A decent snippet with enough detail",
        source="test",
        rank=0,
        independent_source_count=1,
    )
    # Same result, 3 independent sources
    many_indep = SearchResult(
        title="Same Title",
        url="https://example.com/page",
        snippet="A decent snippet with enough detail",
        source="test",
        rank=0,
        independent_source_count=3,
    )

    score_none = SuperSearchAggregator._score(no_indep, provider_count=1)
    score_one = SuperSearchAggregator._score(one_indep, provider_count=1)
    score_many = SuperSearchAggregator._score(many_indep, provider_count=3)

    # Independence boost should monotonically increase scores
    assert score_one > score_none, "1 independent source should score higher than 0"
    assert score_many > score_one, "3 independent sources should score higher than 1"

    # Verify the exact boost delta per independent source is 0.3
    assert abs((score_one - score_none) - 0.3) < 1e-9


def test_merge_logic(tmp_path: pathlib.Path) -> None:
    agg = SuperSearchAggregator(
        Config(
            brave_api_key=None,
            google_api_key=None,
            google_cx=None,
            bing_api_key=None,
            searx_instances=[],
            semantic_scholar_api_key=None,
            timeout=5.0,
        ),
        cache=_tmp_cache(tmp_path),
    )

    batch1 = [
        SearchResult(
            title="Short Title",
            url="https://example.com/path",
            snippet="A brief desc",
            source="provider1",
            rank=2,
            providers=frozenset({"provider1"}),
        )
    ]
    batch2 = [
        SearchResult(
            title="Much Longer Title of Example Page",
            url="https://example.com/path/",
            snippet="A significantly longer and more detailed description of the page",
            source="provider2",
            rank=0,
            providers=frozenset({"provider2"}),
        )
    ]

    merged = agg._merge([batch1, batch2])
    assert len(merged) == 1
    res = merged[0]

    # Check that duplicates are merged under the normalized URL
    assert normalize_url(res.url) == "https://example.com/path"

    # Check metadata enrichment: longest title & longest snippet are preferred
    assert res.title == "Much Longer Title of Example Page"
    assert (
        res.snippet
        == "A significantly longer and more detailed description of the page"
    )

    # Check combined provider set
    assert res.providers == frozenset({"provider1", "provider2"})

    # Check minimum rank position (best position)
    assert res.rank == 0


class MockProvider(SearchProvider):
    name = "mock_provider"

    def __init__(
        self, delay: float = 0.0, raise_error: bool = False, rate_limit: int = 0
    ) -> None:
        self.delay = delay
        self.raise_error = raise_error
        self.rate_limit_attempts = rate_limit
        self.calls = 0

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        self.calls += 1
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        if self.raise_error:
            raise ValueError("Mock error")
        if self.calls <= self.rate_limit_attempts:
            # Raise HTTP 429
            req = httpx.Request("GET", "https://mock")
            resp = httpx.Response(429, request=req)
            raise httpx.HTTPStatusError(
                "429 Too Many Requests", request=req, response=resp
            )

        return [
            SearchResult(
                title=f"Mock Result {i}",
                url=f"https://mock.com/{i}",
                snippet="Mock snippet",
                source=self.name,
                rank=i,
                providers=frozenset({self.name}),
            )
            for i in range(max_results)
        ]


class MockIndependentProvider(SearchProvider):
    """Mock provider marked as independent for testing."""
    name = "mock_independent"

    @property
    def independent(self) -> bool:
        return True

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        return [
            SearchResult(
                title=f"Independent Result {i}",
                url=f"https://independent.com/{i}",
                snippet="Independent snippet with good content",
                source=self.name,
                rank=i,
                providers=frozenset({self.name}),
            )
            for i in range(max_results)
        ]


@pytest.mark.asyncio
async def test_aggregator_timeout_guard(tmp_path: pathlib.Path) -> None:
    # Test that a slow provider is aborted, but others complete
    slow_provider = MockProvider(delay=1.0)
    fast_provider = MockProvider(delay=0.01)

    agg = SuperSearchAggregator(
        Config(
            brave_api_key=None,
            google_api_key=None,
            google_cx=None,
            bing_api_key=None,
            searx_instances=[],
            semantic_scholar_api_key=None,
            timeout=0.2,  # short timeout
        ),
        cache=_tmp_cache(tmp_path),
    )
    agg._providers = [slow_provider, fast_provider]

    results = await agg.search("test query", max_results=10, per_provider=3)

    # Fast provider should have completed successfully
    # Slow provider should have timed out and contributed 0 results
    assert len(results) == 3
    assert all(r.source == "mock_provider" for r in results)
    assert fast_provider.calls == 1
    assert slow_provider.calls == 1


@pytest.mark.asyncio
async def test_independent_only_filter(tmp_path: pathlib.Path) -> None:
    """Test that --independent-only filters out results from non-independent providers."""
    dependent_provider = MockProvider(delay=0.0)
    independent_provider = MockIndependentProvider()

    agg = SuperSearchAggregator(
        Config(
            brave_api_key=None,
            google_api_key=None,
            google_cx=None,
            bing_api_key=None,
            searx_instances=[],
            semantic_scholar_api_key=None,
            timeout=5.0,
        ),
        cache=_tmp_cache(tmp_path),
    )
    agg._providers = [dependent_provider, independent_provider]
    # Rebuild the independence map for injected providers
    agg._independence_map = {p.name: p.independent for p in agg._providers}

    # Without filter: both providers contribute results
    all_results = await agg.search("test query", max_results=20, per_provider=3)
    sources = {r.source for r in all_results}
    assert "mock_provider" in sources
    assert "mock_independent" in sources

    # With filter: only independent provider results survive
    indep_results = await agg.search(
        "test independent",
        max_results=20,
        per_provider=3,
        independent_only=True,
    )
    assert len(indep_results) > 0
    assert all(r.independent_source_count > 0 for r in indep_results)
    assert all(r.source == "mock_independent" for r in indep_results)
