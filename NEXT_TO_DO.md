# Next To Do

Pending improvements ordered by impact.

---

## High Priority

- [ ] **1. Fix the broken virtual environment**
  The `.venv` directory exists but has no `pip` — it was created without `ensurepip`.
  Requires system package `python3.11-venv` (needs `apt install python3.11-venv`), then:
  ```bash
  python3 -m venv .venv --clear
  .venv/bin/pip install -r requirements.txt
  ```
  Until then, the system Python is used as a workaround.

- [ ] **2. Register a free Semantic Scholar API key**
  Without a key, the provider hits HTTP 429 on almost every cold request and relies on the retry backoff to eventually succeed (adds 3–7 s latency). Observed failing three times in a row before giving up in live runs.
  Registration: https://www.semanticscholar.org/product/api — no credit card required.
  Add the key to `.env` as `SEMANTIC_SCHOLAR_API_KEY=`.

- [ ] **3. Improve Internet Archive relevance**
  The current query uses `mediatype:texts` which surfaces obscure digitized documents.
  Options:
  - Add a `mediatype:web` variant to find archived web pages
  - Filter by date range for fresher content
  - Score Archive results lower by default (they are rarely the most relevant result for general queries)

---

## Medium Priority

- [ ] **4. Add more free providers**
  Candidates that require no API key:
  - **Common Crawl index** (`https://index.commoncrawl.org/`) — useful for deep/archival queries
  - **OpenLibrary** (`https://openlibrary.org/search.json`) — books and publications
  - **arXiv** (`https://export.arxiv.org/api/query`) — preprints in science and engineering

- [ ] **5. Configurable provider weights**
  Allow users to define per-provider score multipliers in `.env` (e.g. `PROVIDER_WEIGHT_DUCKDUCKGO=1.5`).
  Useful for tuning relevance to personal workflows (e.g. boosting academic sources for researchers).

- [ ] **6. Paginated results**
  The CLI currently returns one flat batch of up to `--max` results.
  Supporting `--page N` would allow fetching the next batch without re-querying all providers, useful for interactive exploration.

---

## Low Priority

- [ ] **7. Interactive TUI mode**
  A curses/textual-based interactive mode where the user can refine the query, filter by provider, and open URLs directly from the terminal.

---

## Completed

- [x] **Mojeek 403 fix** — Gated `MojeekProvider` with `MOJEEK_API_KEY`; without a key the provider is now disabled cleanly instead of crashing with 403 Forbidden.
- [x] **SearX 429 fix** — All-429 state now propagates up as a retryable error to the aggregator's backoff handler; added dynamic fallback to fetch fresh working instances from `searx.space/data/instances.json` at runtime.
- [x] **Wikipedia 0 results fix** — Switched from the prefix-match `opensearch` API to the full-text REST Search API (`/w/rest.php/v1/search/page`); returns richer results even for specific technical queries.
- [x] **Cache hit confirmed** — Second identical query returned in ~0.3 s with no network calls. Disk caching (`supersearch/cache.py`, TTL-based) is working correctly.
- [x] **Disk caching system** — `supersearch/cache.py`, TTL-based on-disk JSON cache integrated into the aggregator. `.search_cache/` excluded from version control via `.gitignore`.
- [x] **Mojeek provider** — `supersearch/providers/mojeek.py`, optional provider requiring `MOJEEK_API_KEY`.
- [x] **Unit tests** — `tests/test_aggregator.py`, 4 tests covering `normalize_url`, `_score`, `_merge`, and the timeout guard. All passing.
- [x] **`.gitignore`** — excludes `.env`, `__pycache__/`, `*.pyc`, `.venv/`, `.pytest_cache/`, `.search_cache/`.
- [x] **Global provider timeout guard** — `asyncio.wait_for` in `aggregator.py` cancels stalled providers individually.
- [x] **Expanded SearX instance pool** — from 3 to 13 public instances in `.env` and `.env.example`.
- [x] **HackerNews provider** — `supersearch/providers/hn.py`.
- [x] **Reddit provider** — `supersearch/providers/reddit.py`.
- [x] **Retry/backoff** — exponential backoff on 429 in `aggregator._safe_search`.
- [x] **SearX parallel querying** — all instances queried concurrently, results merged.
- [x] **Scoring fix** — `math.log1p` diversity weight.
- [x] **Wikipedia safe unpacking** — guarded index access.
- [x] **Semantic Scholar API key support** — optional `x-api-key` header.
- [x] **`.env` file created** — all variables pre-declared.
