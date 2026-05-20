# Changelog

All notable changes to SuperSearch are documented here.

## [Unreleased] — 2026-05-20

### Added

- **Disk Caching System** ([cache.py](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/supersearch/cache.py)): TTL-based on-disk JSON cache integrated into the aggregator. Dramatically improves performance for repeated queries and reduces provider rate-limiting. `.search_cache/` excluded from version control.
- **Mojeek search provider** ([mojeek.py](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/supersearch/providers/mojeek.py)): Independent search index via the Mojeek JSON API. Requires `MOJEEK_API_KEY` (provider is disabled cleanly when the key is absent, avoiding 403 errors).
- **Aggregator Unit Tests** ([test_aggregator.py](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/tests/test_aggregator.py)): Unit test suite covering URL normalization, scoring/ranking logic, result merging, and the async timeout guard. All 4 tests pass.
- **Git Ignore** ([.gitignore](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/.gitignore)): Excludes `.env`, `__pycache__/`, `*.pyc`, `.venv/`, `.pytest_cache/`, `.search_cache/`.
- **HackerNews provider** ([hn.py](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/supersearch/providers/hn.py)): Algolia HN API — fully free, no API key required, generous rate limits.
- **Reddit provider** ([reddit.py](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/supersearch/providers/reddit.py)): Public Reddit JSON search API — free, no OAuth required. Uses a descriptive `User-Agent` to avoid 403 blocks.
- **Semantic Scholar API key support**: `SemanticScholarProvider` reads `SEMANTIC_SCHOLAR_API_KEY` from env and sends it as `x-api-key`. Free registration at https://www.semanticscholar.org/product/api.
- **`MOJEEK_API_KEY`** variable added to `.env` and `.env.example`.
- **`SEMANTIC_SCHOLAR_API_KEY`** variable added to `.env` and `.env.example`.
- **`SEARCH_TIMEOUT`** variable documented in `.env` and `.env.example`.
- **`.env` file**: Added ready-to-use `.env` with all variables pre-declared. Previously only `.env.example` existed, leaving `load_dotenv()` with nothing to load.

### Changed

- **Wikipedia full-text REST API** ([wikipedia.py](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/supersearch/providers/wikipedia.py)): Switched from the prefix-match `opensearch` endpoint to `/w/rest.php/v1/search/page`. Returns richer excerpts (with HTML stripped) and reliable results for specific technical queries that previously returned 0.
- **SearX dynamic fallback** ([searx.py](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/supersearch/providers/searx.py)): When all configured instances are rate-limited (all-429), a live instance list is fetched from `https://searx.space/data/instances.json` (≥95% uptime, top 5 by uptime). If this also fails, the 429 is propagated to the aggregator's backoff handler for retry.
- **Global Provider Timeout Guard** ([aggregator.py](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/supersearch/aggregator.py)): Each provider is wrapped with `asyncio.wait_for(...)` so stalled providers are cancelled individually at the configured timeout without delaying the aggregate result.
- **Expanded SearX instance pool** ([config.py](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/supersearch/config.py)): Default pool expanded from 3 to 17 instances for better resilience against rate limiting.
- **Retry/backoff logic** ([aggregator.py](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/supersearch/aggregator.py)): `_safe_search` retries up to 3× with exponential backoff (1 s → 2 s → 4 s) on HTTP 429. Other errors fail fast.
- **SearX parallel querying** ([searx.py](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/supersearch/providers/searx.py)): All instances queried concurrently via `asyncio.gather()`, results merged and deduplicated.
- **Scoring algorithm** ([aggregator.py](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/supersearch/aggregator.py)): Diversity weight changed from `provider_count * 2.0` to `math.log1p(provider_count)` so well-ranked single-provider results are no longer buried.
- **`Config` dataclass** ([config.py](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/supersearch/config.py)): Added `semantic_scholar_api_key` and `mojeek_api_key` fields.
- **Provider registry** ([__init__.py](file:///root/my-applications/BUSQUEDAS_TREMENDAS/SuperSearch/supersearch/providers/__init__.py)): `HackerNewsProvider`, `RedditProvider`, and `MojeekProvider` registered. Active provider count: 9 free + 3 optional-key.

### Fixed

- **Mojeek 403 errors**: Provider now disabled cleanly when `MOJEEK_API_KEY` is absent.
- **SearX returning 0 results**: Parallel querying + dynamic fallback to `searx.space` resolve all-429 states. Propagated 429 triggers the aggregator's retry backoff.
- **Wikipedia returning 0 results**: Full-text REST API replaces the prefix-match `opensearch` endpoint.
- **Semantic Scholar always returning 0 results**: Retry backoff resolves transient 429s; free API key eliminates them.
- **Wikipedia `IndexError`** on malformed responses: Guarded index access replaced the hard `[1:4]` unpack.
- **Scoring burying high-quality single-provider results**: Log-scale diversity weight.

