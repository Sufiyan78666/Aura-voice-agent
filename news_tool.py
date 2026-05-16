"""
news_tool.py - Voice Agent News Tool
Fetches latest headlines from Google News RSS.
"""

from __future__ import annotations

from typing import Optional
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


_COUNTRY_CODES = {
    "worldwide": None,
    "global": None,
    "international": None,
    "india": "IN",
    "bharat": "IN",
    "usa": "US",
    "us": "US",
    "united states": "US",
    "america": "US",
    "uk": "GB",
    "united kingdom": "GB",
    "england": "GB",
    "uae": "AE",
    "dubai": "AE",
    "canada": "CA",
    "australia": "AU",
    "singapore": "SG",
    "japan": "JP",
    "france": "FR",
    "germany": "DE",
}


def get_news_items(
    country: Optional[str] = None,
    language: str = "en",
    max_items: int = 3,
    query: Optional[str] = None,
) -> list[str]:
    if query:
        url = _build_google_news_search_url(query, country, language)
    else:
        url = _build_google_news_url(country, language)
    items = _fetch_rss_items(url)
    headlines = [title for title in items[:max_items] if title]
    return headlines


def get_news(
    country: Optional[str] = None,
    language: str = "en",
    max_items: int = 3,
    query: Optional[str] = None,
) -> str:
    headlines = get_news_items(country=country, language=language, max_items=max_items, query=query)
    if not headlines:
        return "Sorry, I could not fetch the latest news right now."

    label = _format_country_label(country)
    joined = "; ".join(headlines)
    return f"Top headlines {label}: {joined}."


def _build_google_news_url(country: Optional[str], language: str) -> str:
    cc = _normalize_country_code(country)
    lang = (language or "en").lower()

    if not cc:
        # Worldwide/default edition
        return f"https://news.google.com/rss?hl={lang}&ceid=US:{lang}&gl=US"

    # Country edition
    hl = f"{lang}-{cc}" if lang == "en" else lang
    return f"https://news.google.com/rss?hl={hl}&ceid={cc}:{lang}&gl={cc}"


def _build_google_news_search_url(query: str, country: Optional[str], language: str) -> str:
    cc = _normalize_country_code(country) or "IN"
    lang = (language or "en").lower()
    hl = f"{lang}-{cc}" if lang == "en" else lang
    q = query.strip().replace(" ", "+")
    return f"https://news.google.com/rss/search?q={q}&hl={hl}&ceid={cc}:{lang}&gl={cc}"


def _normalize_country_code(country: Optional[str]) -> Optional[str]:
    if not country:
        return None
    key = country.strip().lower()
    return _COUNTRY_CODES.get(key)


def _format_country_label(country: Optional[str]) -> str:
    if not country:
        return "worldwide"
    key = country.strip().lower()
    if key in ("worldwide", "global", "international"):
        return "worldwide"
    return f"for {country.title()}"


def _fetch_rss_items(url: str) -> list[str]:
    try:
        req = Request(url, headers={"User-Agent": "voice-agent/1.0"})
        with urlopen(req, timeout=10) as response:
            data = response.read()
    except Exception:
        return []

    try:
        root = ET.fromstring(data)
    except Exception:
        return []

    items: list[str] = []
    for item in root.findall(".//item"):
        title_node = item.find("title")
        if title_node is not None and title_node.text:
            items.append(title_node.text.strip())
    return items
