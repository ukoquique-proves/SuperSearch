# SuperSearch

A multi-engine web search aggregator that maximizes coverage by querying multiple search providers in parallel, merging results by URL, and boosting cross-provider hits.

## Features

- **Multi-provider aggregation**: Queries multiple search engines simultaneously for broader coverage
- **Smart merging**: Deduplicates results by normalized URL and combines metadata from multiple sources
- **Relevance scoring**: Boosts results that appear across multiple providers (log-scale diversity signal)
- **Async/parallel**: Fast concurrent queries to all backends with per-provider timeout cancellation
- **Retry/backoff**: Automatic retry with exponential backoff on rate-limited (429) providers
- **Result caching**: TTL-based on-disk JSON cache to speed up repeated queries and reduce rate-limit pressure
- **Flexible output**: Beautiful table view or JSON output
- **Configurable**: Optional API keys for premium providers, works out-of-the-box with free providers

## Supported Providers

| Provider | Type | API Key Required |
|----------|------|------------------|
| DuckDuckGo | General search | No |
| DuckDuckGo News | News search | No |
| Hacker News | Tech stories (Algolia API) | No |
| Reddit | Community discussions | No |
| Mojeek | Independent general search | Optional (free tier) |
| SearX | Meta-search (aggregates many engines, 17 instances + dynamic fallback) | No |
| Wikipedia | Encyclopedia | No |
| Semantic Scholar | Academic papers | Optional (free) |
| Internet Archive | Web archives | No |
| Brave Search | General search | Optional |
| Google Custom Search | General search | Optional |
| Bing Search | General search | Optional |

## Installation

### Requirements

- Python 3.8+
- pip

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd SuperSearch
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. (Optional) Configure API keys for additional providers:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

## Usage

### Basic Search

```bash
python main.py "your search query"
```

### Command-Line Options

```
usage: main.py [-h] [-n MAX] [-p PER_PROVIDER] [--json] [-v] [--list-providers] [query ...]

SuperSearch — multi-engine web search to maximize coverage.

positional arguments:
  query                 Search terms

options:
  -h, --help            show this help message and exit
  -n MAX, --max MAX     Max merged results (default: 25)
  -p PER_PROVIDER, --per-provider PER_PROVIDER
                        Max results fetched per backend (default: 15)
  --json                Print JSON instead of table
  -v, --verbose         Log provider errors
  --list-providers      Show enabled backends and exit
```

### Examples

Search with default settings:
```bash
python main.py "machine learning tutorials"
```

Get more results:
```bash
python main.py -n 50 "climate change research"
```

Output as JSON:
```bash
python main.py --json "quantum computing"
```

Show active providers:
```bash
python main.py --list-providers
```

Verbose mode (for debugging):
```bash
python main.py -v "python async programming"
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Optional API keys — more providers = broader coverage
BRAVE_API_KEY=your_brave_api_key
GOOGLE_CSE_API_KEY=your_google_api_key
GOOGLE_CSE_CX=your_custom_search_engine_id
BING_API_KEY=your_bing_api_key

# Free API key — reduces rate limiting on Semantic Scholar (no credit card needed)
# Register at: https://www.semanticscholar.org/product/api
SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_api_key

# Comma-separated SearX instances (all queried in parallel)
SEARX_INSTANCES=https://searx.tiekoetter.com,https://search.mdosch.de,https://opnxng.com

# Request timeout in seconds
SEARCH_TIMEOUT=15
```

### API Key Setup

**Brave Search**: Get API key from [Brave Search API](https://api.search.brave.com/)

**Google Custom Search**:
1. Create a Custom Search Engine at [Google CSE](https://programmablesearchengine.google.com/)
2. Enable API access at [Google Cloud Console](https://console.cloud.google.com/)
3. Get API key and CX ID

**Bing Search**: Get API key from [Azure Portal](https://portal.azure.com/)

**Semantic Scholar** (free — no credit card): Register at [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api). Provides a higher rate limit and avoids the 429 errors that affect unauthenticated requests.

**Mojeek** (free tier available): Register at [mojeek.com/services/search/api](https://www.mojeek.com/services/search/api). Set `MOJEEK_API_KEY` in `.env`. Without a key the provider is disabled cleanly.

## Architecture

```
SuperSearch/
├── main.py                 # CLI entry point
├── requirements.txt         # Python dependencies
├── .env.example            # Configuration template
├── .env                    # Local configuration (not committed)
├── .gitignore              # Excludes .env, __pycache__, .venv, .pytest_cache
├── CHANGELOG.md            # Version history
├── NEXT_TO_DO.md           # Pending improvements tracker
├── tests/
│   └── test_aggregator.py  # Unit tests (normalize_url, _score, _merge, timeout guard)
└── supersearch/
    ├── __init__.py
    ├── aggregator.py       # Core orchestration, retry/backoff, timeout guard, scoring
    ├── cache.py            # TTL-based on-disk JSON result cache
    ├── config.py           # Configuration management
    ├── models.py           # Data models
    └── providers/
        ├── base.py         # Abstract provider interface
        ├── duckduckgo.py   # DuckDuckGo provider (general + news)
        ├── hn.py           # Hacker News provider (Algolia API)
        ├── reddit.py       # Reddit provider (public JSON API)
        ├── mojeek.py       # Mojeek independent search provider
        ├── brave.py        # Brave Search provider
        ├── google.py       # Google CSE provider
        ├── bing.py         # Bing Search provider
        ├── searx.py        # SearX meta-search (parallel instance querying)
        ├── wikipedia.py    # Wikipedia provider
        ├── semantic_scholar.py  # Academic search provider
        └── archive.py      # Internet Archive provider
```

### How It Works

1. **Parallel Queries**: All enabled providers are queried concurrently using asyncio
2. **Retry/Backoff**: Providers that return HTTP 429 (rate limited) are retried up to 3 times with exponential backoff (1 s → 2 s → 4 s)
3. **Safe Execution**: Individual provider failures don't crash the entire search
4. **URL Normalization**: Results are deduplicated by normalized URL (scheme, host, path)
5. **Smart Merging**: When the same URL appears from multiple providers:
   - Titles and snippets are merged (longer version preferred)
   - Provider list is combined
   - Rank is minimized (best position)
6. **Scoring**: Results are ranked by a balanced formula:
   - Provider diversity: `log(1 + provider_count)` — cross-provider results score higher but don't overwhelm single-provider results
   - Original rank: `1 / (1 + rank)` — top-ranked results score higher
   - Snippet richness: `min(len(snippet), 300) / 300` — more context scores higher

## Output Formats

### Table Output (default)

```
Query: python async programming
Providers: duckduckgo, duckduckgo_news, searx, wikipedia
Unique URLs: 25

┏━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ #  ┃ Title                                      ┃ URL                                          ┃ Sources          ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ 1  │ Python Async/Await ...                     │ https://docs.python.org/3/library/asyncio... │ duckduckgo, searx │
...
```

### JSON Output

```json
{
  "query": "python async programming",
  "count": 25,
  "results": [
    {
      "title": "Python Async/Await Tutorial",
      "url": "https://docs.python.org/3/library/asyncio.html",
      "snippet": "The asyncio module provides...",
      "source": "duckduckgo",
      "providers": ["duckduckgo", "searx"]
    }
  ]
}
```

## Development

### Running Tests

```bash
python -m pytest
```

### Adding a New Provider

1. Create a new file in `supersearch/providers/`
2. Inherit from `SearchProvider` in `base.py`
3. Implement the `search()` method
4. Add to `build_providers()` in `providers/__init__.py`

Example:

```python
from supersearch.providers.base import SearchProvider
from supersearch.models import SearchResult
from supersearch.config import Config

class MyProvider(SearchProvider):
    name = "myprovider"
    
    def __init__(self, config: Config):
        self.config = config
    
    @property
    def enabled(self) -> bool:
        return bool(self.config.my_api_key)
    
    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        # Implement search logic
        return []
```

## License

[Specify your license here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
