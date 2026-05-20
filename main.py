#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from rich.console import Console
from rich.table import Table

from supersearch import SuperSearchAggregator
from supersearch.config import Config


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="SuperSearch — multi-engine web search to maximize coverage.",
    )
    p.add_argument("query", nargs="*", help="Search terms")
    p.add_argument("-n", "--max", type=int, default=25, help="Max merged results")
    p.add_argument(
        "-p",
        "--per-provider",
        type=int,
        default=15,
        help="Max results fetched per backend",
    )
    p.add_argument("--json", action="store_true", help="Print JSON instead of table")
    p.add_argument("-v", "--verbose", action="store_true", help="Log provider errors")
    p.add_argument(
        "--list-providers",
        action="store_true",
        help="Show enabled backends and exit",
    )
    return p.parse_args()


def print_table(results: list, console: Console) -> None:
    table = Table(show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", max_width=40)
    table.add_column("URL", max_width=50)
    table.add_column("Sources", max_width=20)
    for i, row in enumerate(results, 1):
        sources = ", ".join(sorted(row.providers))[:40]
        table.add_row(str(i), row.title[:80], row.url[:90], sources)
    console.print(table)


async def run() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    agg = SuperSearchAggregator(Config.from_env())

    if args.list_providers:
        print("Active providers:", ", ".join(agg.active_providers))
        print("Add API keys in .env for: brave, google_cse, bing")
        return 0

    query = " ".join(args.query).strip()
    if not query:
        print("Error: provide a search query.", file=sys.stderr)
        return 2
    results = await agg.search(
        query,
        max_results=args.max,
        per_provider=args.per_provider,
    )

    if args.json:
        payload = [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "source": r.source,
                "providers": sorted(r.providers),
            }
            for r in results
        ]
        print(json.dumps({"query": query, "count": len(payload), "results": payload}, ensure_ascii=False, indent=2))
        return 0

    console = Console()
    console.print(f"[bold]Query:[/bold] {query}")
    console.print(f"[dim]Providers:[/dim] {', '.join(agg.active_providers)}")
    console.print(f"[dim]Unique URLs:[/dim] {len(results)}\n")
    if not results:
        console.print("[yellow]No results. Try -v or check network / SearX instances.[/yellow]")
        return 1
    print_table(results, console)
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
