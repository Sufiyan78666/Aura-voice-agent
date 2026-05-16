"""
websearch_tool.py - Voice Agent Web Search Tool
Uses Serper (Google) search API.
"""

from __future__ import annotations

import html
import json
import re
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, unquote
from urllib.request import Request, urlopen


def web_search(query: str, api_key: Optional[str], num_results: int = 5, provider: str = "serper") -> str:
    if not query:
        return "Please say what you want me to search for."

    provider = (provider or "serper").lower().strip()
    if provider == "duckduckgo":
        return _duckduckgo_search(query, num_results)
    if provider == "tavily":
        if not api_key:
            return "Search API key is missing. Please set TAVILY_API_KEY in .env."
        return _tavily_search(query, api_key, num_results)

    if not api_key:
        return "Search API key is missing. Please set SERPER_API_KEY in .env."
    return _serper_search(query, api_key, num_results)


def _serper_search(query: str, api_key: str, num_results: int) -> str:
    payload = json.dumps({"q": query, "num": num_results}).encode("utf-8")
    req = Request(
        "https://google.serper.dev/search",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-API-KEY": api_key,
            "User-Agent": "voice-agent/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=15) as response:
            data = response.read().decode("utf-8")
    except HTTPError as exc:
        try:
            details = exc.read().decode("utf-8").strip()
        except Exception:
            details = ""
        message = f"Search service error (HTTP {exc.code})."
        if details:
            message = f"{message} {details}"
        return message
    except URLError:
        return "Sorry, I could not reach the search service right now."
    except Exception:
        return "Sorry, I could not reach the search service right now."

    try:
        result = json.loads(data)
    except Exception:
        return "Sorry, I could not parse the search results."

    items = result.get("organic", [])
    if not items:
        return "No results found."

    lines = []
    for idx, item in enumerate(items[:num_results], 1):
        title = item.get("title") or "(no title)"
        snippet = item.get("snippet") or ""
        if snippet:
            lines.append(f"{idx}. {title} — {snippet}")
        else:
            lines.append(f"{idx}. {title}")

    return "Top results: " + " ".join(lines)


def _tavily_search(query: str, api_key: str, num_results: int) -> str:
    payload = json.dumps({
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "include_answer": True,
        "include_images": False,
        "include_raw_content": False,
        "max_results": num_results
    }).encode("utf-8")
    req = Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=15) as response:
            data = response.read().decode("utf-8")
    except HTTPError as exc:
        try:
            details = exc.read().decode("utf-8").strip()
        except Exception:
            details = ""
        message = f"Search service error (HTTP {exc.code})."
        if details:
            message = f"{message} {details}"
        return message
    except URLError:
        return "Sorry, I could not reach the search service right now."
    except Exception:
        return "Sorry, I could not reach the search service right now."

    try:
        result = json.loads(data)
    except Exception:
        return "Sorry, I could not parse the search results."

    items = result.get("results", [])
    if not items:
        return "No results found."

    lines = []
    answer = result.get("answer")
    if answer:
        lines.append(f"Answer: {answer}")
        
    for idx, item in enumerate(items[:num_results], 1):
        title = item.get("title") or "(no title)"
        snippet = item.get("content") or ""
        if snippet:
            lines.append(f"{idx}. {title} — {snippet}")
        else:
            lines.append(f"{idx}. {title}")

    return "Top results: " + " ".join(lines)


def _duckduckgo_search(query: str, num_results: int) -> str:
    q = quote_plus(query)
    url = f"https://duckduckgo.com/html/?q={q}"
    req = Request(url, headers={"User-Agent": "voice-agent/1.0"})

    try:
        with urlopen(req, timeout=15) as response:
            raw_html = response.read().decode("utf-8", errors="ignore")
    except Exception:
        return "Sorry, I could not reach the search service right now."

    # Extract results from DDG HTML page
    titles = []
    for match in re.finditer(r"<a[^>]+class=\"result__a\"[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", raw_html):
        title = re.sub(r"<.*?>", "", match.group(2)).strip()
        title = html.unescape(title)   # now refers to the module, not the variable
        if title:
            titles.append(title)
        if len(titles) >= num_results:
            break

    snippets = []
    for match in re.finditer(r"class=\"result__snippet\"[^>]*>(.*?)</a>", raw_html, flags=re.IGNORECASE | re.DOTALL):
        snippet = re.sub(r"<.*?>", "", match.group(1)).strip()
        snippet = html.unescape(snippet)
        if snippet:
            snippets.append(snippet)
        if len(snippets) >= num_results:
            break

    if not titles:
        return "No results found."

    lines = []
    for idx, title in enumerate(titles, 1):
        snippet = snippets[idx - 1] if idx - 1 < len(snippets) else ""
        if snippet:
            lines.append(f"{idx}. {title} — {snippet}")
        else:
            lines.append(f"{idx}. {title}")

    return "Top results: " + " ".join(lines)


def _unwrap_duckduckgo_link(link: str) -> str:
    if link.startswith("//"):
        link = "https:" + link
    if "duckduckgo.com/l/?" not in link:
        return link
    query = link.split("?", 1)[1]
    params = parse_qs(query)
    target = params.get("uddg", [""])[0]
    return unquote(target) if target else link


def fetch_goldpricez_india(karat: str = "24k") -> Optional[dict]:
    karat = (karat or "24k").lower().strip()
    allowed = {"24k", "22k", "18k", "14k", "10k", "23k"}
    if karat not in allowed:
        karat = "24k"

    url = f"https://www.goldpricez.com/in/{karat}/gram"
    req = Request(url, headers={"User-Agent": "voice-agent/1.0"})
    try:
        with urlopen(req, timeout=15) as response:
            raw_html = response.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = re.sub(r"\s+", " ", text)

    per_gram = _extract_inr_value(text, r"1 Gram Rate")
    per_10g = _extract_inr_value(text, r"10 Gram Rate")
    if not per_gram:
        return None

    return {
        "source": url,
        "karat": karat,
        "per_gram": per_gram,
        "per_10g": per_10g,
    }


def _extract_inr_value(text: str, label: str) -> Optional[str]:
    pattern = rf"{label}\s*₹\s*([0-9,]+(?:\.\d+)?)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1)
