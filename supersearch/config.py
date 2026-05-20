from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DEFAULT_SEARX = (
    "https://searx.tiekoetter.com,"
    "https://search.mdosch.de,"
    "https://opnxng.com,"
    "https://searx.be,"
    "https://priv.au,"
    "https://searxng.site,"
    "https://baresearch.org,"
    "https://search.ononoki.org,"
    "https://searx.ru,"
    "https://gruble.de,"
    "https://searx.ch,"
    "https://search.bus-hit.me,"
    "https://search.inetol.net,"
    "https://searx.work,"
    "https://searx.info,"
    "https://searx.xyz,"
    "https://searx.ca"
)


@dataclass(frozen=True)
class Config:
    brave_api_key: str | None
    google_api_key: str | None
    google_cx: str | None
    bing_api_key: str | None
    searx_instances: list[str]
    semantic_scholar_api_key: str | None
    mojeek_api_key: str | None = None
    timeout: float = 15.0

    @classmethod
    def from_env(cls) -> Config:
        raw = os.getenv("SEARX_INSTANCES", DEFAULT_SEARX)
        instances = [u.strip().rstrip("/") for u in raw.split(",") if u.strip()]
        return cls(
            brave_api_key=os.getenv("BRAVE_API_KEY") or None,
            google_api_key=os.getenv("GOOGLE_CSE_API_KEY") or None,
            google_cx=os.getenv("GOOGLE_CSE_CX") or None,
            bing_api_key=os.getenv("BING_API_KEY") or None,
            searx_instances=instances,
            semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY") or None,
            mojeek_api_key=os.getenv("MOJEEK_API_KEY") or None,
            timeout=float(os.getenv("SEARCH_TIMEOUT", "15")),
        )
