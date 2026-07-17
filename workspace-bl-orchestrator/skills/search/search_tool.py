#!/usr/bin/env python3
"""search_tool.py — DuckDuckGo search via ddgs library (adapted from news Scout).

Backlink variant: supports site-scoped queries (keeps Reddit/forums) vs open-web
mode (filters aggregators/social noise for find-sites).

Usage:
  python3 search_tool.py --query "site:reddit.com/r/saas marketing" --max 10
  python3 search_tool.py --query "saas forum" --mode open --max 8
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from urllib.parse import urlparse

# Open-web discovery: skip search engines and low-value hosts.
_OPEN_SKIP_DOMAINS = frozenset({
    "news.google.com",
    "google.com", "bing.com", "duckduckgo.com", "yahoo.com",
    "youtube.com", "youtu.be", "m.youtube.com",
    "reddit.com", "old.reddit.com",
    "twitter.com", "x.com", "mobile.twitter.com",
    "facebook.com", "m.facebook.com",
    "instagram.com", "tiktok.com", "pinterest.com",
    "linkedin.com", "t.me",
    "wikipedia.org", "amazon.com",
    "translate.google.com", "policies.google.com", "support.google.com",
})

# Site-scoped scans: only skip pure search/aggregator noise.
_SITE_SKIP_DOMAINS = frozenset({
    "google.com", "bing.com", "duckduckgo.com", "yahoo.com",
    "news.google.com",
})

MAX_DEFAULT = 10
RETRY_BACKOFF_S = 2.0


def _ddg_retries() -> int:
    raw = os.environ.get("BL_DDG_RETRIES", "3").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 3


def _ddg_backends() -> list[str]:
    raw = os.environ.get("BL_DDG_BACKENDS", "auto").strip()
    parts = [x.strip() for x in raw.split(",") if x.strip()]
    return parts or ["auto"]


def _ddg_timeout() -> float:
    raw = os.environ.get("BL_DDG_TIMEOUT", "20").strip()
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 20.0


def _load_ddgs():
    try:
        from ddgs import DDGS  # type: ignore[import-untyped]
        return DDGS
    except Exception:
        pass
    try:
        from duckduckgo_search import DDGS  # type: ignore[import-untyped]
        return DDGS
    except Exception:
        return None


def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except ValueError:
        return ""


def _infer_mode(query: str, mode: str | None) -> str:
    if mode in ("site", "open"):
        return mode
    return "site" if "site:" in query.lower() else "open"


def _skip_domains(mode: str) -> frozenset[str]:
    return _SITE_SKIP_DOMAINS if mode == "site" else _OPEN_SKIP_DOMAINS


def _normalize_item(item: dict, skip: frozenset[str]) -> dict | None:
    if not isinstance(item, dict):
        return None
    url = str(item.get("href") or item.get("url") or item.get("link") or "").strip()
    if not url.startswith("http"):
        return None
    dom = _domain(url)
    if not dom or dom in skip:
        return None
    return {
        "title": str(item.get("title") or "").strip(),
        "url": url,
        "snippet": str(item.get("body") or item.get("snippet") or "").strip(),
        "domain": dom,
    }


def _priority_index(domain: str, order: list[str]) -> int:
    base = domain.split(".")[0] if domain else ""
    for i, name in enumerate(order):
        key = "".join(ch for ch in name.lower() if ch.isalnum())
        if key and (key in domain.replace(".", "") or key == base):
            return i
    return len(order) + 1


def _raw_search(ddgs_cls, query: str, max_results: int, timelimit: str | None) -> list[dict]:
    backends = _ddg_backends()
    retries = _ddg_retries()
    timeout = _ddg_timeout()
    last_err: Exception | None = None
    for backend in backends:
        for attempt in range(retries):
            try:
                with ddgs_cls(timeout=timeout) as ddgs:
                    try:
                        results = list(ddgs.text(
                            query,
                            region="us-en",
                            safesearch="off",
                            timelimit=timelimit,
                            backend=backend,
                            max_results=max_results,
                        ))
                    except TypeError:
                        results = list(ddgs.text(
                            query,
                            region="us-en",
                            safesearch="off",
                            timelimit=timelimit,
                            max_results=max_results,
                        ))
                if results:
                    return results
            except TypeError:
                try:
                    with ddgs_cls() as ddgs:
                        try:
                            results = list(ddgs.text(
                                query,
                                region="us-en",
                                safesearch="off",
                                timelimit=timelimit,
                                backend=backend,
                                max_results=max_results,
                            ))
                        except TypeError:
                            results = list(ddgs.text(
                                query,
                                region="us-en",
                                safesearch="off",
                                timelimit=timelimit,
                                max_results=max_results,
                            ))
                    if results:
                        return results
                except Exception as e:
                    last_err = e
                    time.sleep(RETRY_BACKOFF_S * (attempt + 1))
            except Exception as e:
                last_err = e
                time.sleep(RETRY_BACKOFF_S * (attempt + 1))
    if last_err:
        print(f"[search_tool] all backends failed: {last_err}", file=sys.stderr)
    return []


def _load_priority_order() -> list[str]:
    raw = os.environ.get("BL_SOURCE_PRIORITY", "").strip()
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()]
    return []


def search(
    query: str,
    *,
    max_results: int = MAX_DEFAULT,
    timelimit: str | None = None,
    priority_order: list[str] | None = None,
    mode: str | None = None,
    dedupe_by_domain: bool = False,
) -> list[dict]:
    """Return [{title, url, snippet, domain}] or [] on failure."""
    ddgs_cls = _load_ddgs()
    if ddgs_cls is None:
        print("SEARCH_EMPTY: ddgs library not importable", file=sys.stderr)
        return []
    m = _infer_mode(query, mode)
    skip = _skip_domains(m)
    raw = _raw_search(ddgs_cls, query, max_results * 3, timelimit)
    seen: set[str] = set()
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        norm = _normalize_item(item, skip)
        if not norm:
            continue
        key = norm["domain"] if dedupe_by_domain else norm["url"]
        if key in seen:
            continue
        seen.add(key)
        out.append(norm)
    order = priority_order if priority_order is not None else _load_priority_order()
    if order:
        out.sort(key=lambda r: _priority_index(r["domain"], order))
    return out[:max_results]


def main() -> int:
    ap = argparse.ArgumentParser(description="DuckDuckGo search for backlink discovery")
    ap.add_argument("--query", required=True)
    ap.add_argument("--max", type=int, default=MAX_DEFAULT)
    ap.add_argument("--timelimit", default=None, help="d|w|m|y")
    ap.add_argument("--mode", choices=["site", "open"], default=None)
    ap.add_argument("--dedupe-domain", action="store_true", dest="dedupe_domain")
    args = ap.parse_args()

    results = search(
        args.query,
        max_results=args.max,
        timelimit=args.timelimit,
        mode=args.mode,
        dedupe_by_domain=args.dedupe_domain,
    )
    print(json.dumps(
        {"query": args.query, "count": len(results), "results": results},
        indent=2, ensure_ascii=False,
    ))
    if results:
        print(f"SEARCH_OK: {len(results)} results", file=sys.stderr)
        return 0
    print("SEARCH_EMPTY: no usable results", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
