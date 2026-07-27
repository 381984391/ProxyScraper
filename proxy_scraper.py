#!/usr/bin/env python3
"""Standalone proxy scraper with support for multiple sources."""

from __future__ import annotations

import asyncio
import re
from typing import Callable

import aiohttp


_PROXY_RE = re.compile(
    r"^(?:https?://)?(?:[^@\s]+@)?[a-zA-Z0-9](?:[a-zA-Z0-9\-.]*[a-zA-Z0-9])?:\d{1,5}$"
)

PROXY_SOURCES: list[tuple[str, str]] = [
    ("TheSpeedX", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"),
    ("monosans", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"),
    ("proxifly", "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt"),
    ("ShiftyTR-http", "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt"),
    ("ShiftyTR-https", "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt"),
    ("roosterkid", "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt"),
    ("sunny9577", "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/http_proxies.txt"),
    ("rdavydov", "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt"),
    ("Anonym0usWork12", "https://raw.githubusercontent.com/Anonym0usWork12/Proxy-List/master/http.txt"),
    ("officialputuid", "https://raw.githubusercontent.com/officialputuid/rules/master/proxies.txt"),
    ("mmpx12-http", "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt"),
    ("mmpx12-https", "https://raw.githubusercontent.com/mmpx12/proxy-list/master/https.txt"),
    ("iplocate-http", "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/protocols/http.txt"),
    ("iplocate-https", "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/protocols/https.txt"),
    ("openproxylist.xyz", "https://api.openproxylist.xyz/http.txt"),
    ("proxyscrape.com", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"),
    ("proxyscrape-socks4", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks4&timeout=10000&country=all"),
    ("proxyscrape-socks5", "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all"),
    ("geonode.com", "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps"),
    ("proxy-list.download-http", "https://www.proxy-list.download/api/v1/get?type=http"),
    ("proxy-list.download-https", "https://www.proxy-list.download/api/v1/get?type=https"),
    ("proxy-list.download-socks4", "https://www.proxy-list.download/api/v1/get?type=socks4"),
    ("proxy-list.download-socks5", "https://www.proxy-list.download/api/v1/get?type=socks5"),
    ("jetkai-socks4", "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks4.txt"),
    ("jetkai-socks5", "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt"),
    ("proxyscan-http", "https://www.proxyscan.io/download?type=http"),
    ("proxyscan-socks4", "https://www.proxyscan.io/download?type=socks4"),
    ("proxyscan-socks5", "https://www.proxyscan.io/download?type=socks5"),
    ("TheSpeedX-socks4", "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt"),
    ("TheSpeedX-socks5", "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt"),
    ("proxy-list-raw", "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"),
    ("jetkai-http", "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt"),
]


def _emit(message: str, printer: Callable[[str], None] | None) -> None:
    """Print message using custom printer or default print()."""
    if printer is None:
        print(message)
    else:
        printer(message)


def _classify_source(name: str, url: str) -> str:
    """Return the proxy category for a given source."""
    key = f"{name} {url}".lower()
    if "socks" in key or "sock" in key:
        return "socks"
    return "http"


async def scrape_proxies(
    printer: Callable[[str], None] | None = None,
    return_categories: bool = False,
) -> list[str] | dict[str, list[str]]:
    """Fetch free proxies from sources, deduplicate, and optionally return categories.

    Args:
        printer: Optional custom printer function. Defaults to print().
        return_categories: If True, returns a dict with http, socks, and all lists.

    Returns:
        List of unique proxy addresses, or a category dict when return_categories is True.
    """
    _emit(f"Scraping {len(PROXY_SOURCES)} sources...", printer)

    async def _fetch_one(name: str, url: str) -> list[tuple[str, str]]:
        category = _classify_source(name, url)
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                trust_env=False,
            ) as sess:
                async with sess.get(url) as resp:
                    if resp.status != 200:
                        _emit(f"  ✗ {name} HTTP {resp.status}", printer)
                        return []
                    text = await resp.text()
                    found = [
                        (p.strip(), category)
                        for p in text.splitlines()
                        if _PROXY_RE.match(p.strip())
                    ]
                    _emit(f"  ✓ {name} {len(found)} proxies", printer)
                    return found
        except Exception as exc:
            _emit(f"  ✗ {name} {exc}", printer)
            return []

    results = await asyncio.gather(*[_fetch_one(name, url) for name, url in PROXY_SOURCES])

    seen: set[str] = set()
    http_seen: set[str] = set()
    socks_seen: set[str] = set()
    all_proxies: list[str] = []
    http_proxies: list[str] = []
    socks_proxies: list[str] = []

    for batch in results:
        for proxy, category in batch:
            if category == "http" and proxy not in http_seen:
                http_seen.add(proxy)
                http_proxies.append(proxy)
            elif category == "socks" and proxy not in socks_seen:
                socks_seen.add(proxy)
                socks_proxies.append(proxy)

            key = proxy.split("@")[-1] if "@" in proxy else proxy
            if key not in seen:
                seen.add(key)
                all_proxies.append(proxy)

    if not all_proxies:
        _emit("All sources failed — no proxies.", printer)
        return [] if not return_categories else {"http": [], "socks": [], "all": []}

    _emit(f"{len(all_proxies)} unique proxies (~2-5% usually work)", printer)
    if return_categories:
        return {"http": http_proxies, "socks": socks_proxies, "all": all_proxies}
    return all_proxies


if __name__ == "__main__":
    import sys
    try:
        asyncio.run(scrape_proxies())
    except KeyboardInterrupt:
        sys.exit(130)
