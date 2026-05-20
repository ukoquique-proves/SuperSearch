from supersearch.config import Config
from supersearch.providers.archive import InternetArchiveProvider
from supersearch.providers.base import SearchProvider
from supersearch.providers.bing import BingProvider
from supersearch.providers.brave import BraveProvider
from supersearch.providers.duckduckgo import DuckDuckGoNewsProvider, DuckDuckGoProvider
from supersearch.providers.google import GoogleCSEProvider
from supersearch.providers.hn import HackerNewsProvider
from supersearch.providers.mojeek import MojeekProvider
from supersearch.providers.reddit import RedditProvider
from supersearch.providers.searx import SearXProvider
from supersearch.providers.semantic_scholar import SemanticScholarProvider
from supersearch.providers.wikipedia import WikipediaProvider


def build_providers(config: Config) -> list[SearchProvider]:
    return [
        DuckDuckGoProvider(),
        DuckDuckGoNewsProvider(),
        HackerNewsProvider(config),
        RedditProvider(config),
        SemanticScholarProvider(config),
        InternetArchiveProvider(config),
        WikipediaProvider(config),
        MojeekProvider(config),
        SearXProvider(config),
        BraveProvider(config),
        GoogleCSEProvider(config),
        BingProvider(config),
    ]
