#!/usr/bin/env python3
"""
Daily Digest: adolescent psychology, behavioral therapy (ABA/CBT),
school counseling & education trends, and child/parent mental health.

Free sources only -- public RSS feeds + the free NCBI PubMed E-utilities API.
No API keys, no subscriptions, no background service. Run manually:

    python3 daily_digest.py

Generates an HTML file in ./digests/ and opens it in your browser.
"""

import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import config

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "DailyDigestScript/1.0 (personal, non-commercial use)"
)
REQUEST_TIMEOUT = 12
OUTPUT_DIR = Path(__file__).parent / "digests"
SITE_INDEX_PATH = Path(__file__).parent / "docs" / "index.html"
IS_CI = bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))


def fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return resp.read()


def strip_html(raw):
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def truncate(text, max_chars):
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut.rstrip(".,;: ") + "…"


def parse_rss_date(raw):
    if not raw:
        return None
    parsed = None
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
    if parsed is not None and parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)
    return parsed


_UNESCAPED_AMP_RE = re.compile(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)")
# XML 1.0 disallows most control characters; some feeds embed them anyway.
_INVALID_XML_CHARS_RE = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"
)


def parse_rss(xml_bytes, limit):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        # Some feeds contain unescaped "&" or stray control characters; repair and retry.
        text = xml_bytes.decode("utf-8", errors="replace")
        text = _UNESCAPED_AMP_RE.sub("&amp;", text)
        text = _INVALID_XML_CHARS_RE.sub("", text)
        root = ET.fromstring(text)
    items = []
    # Support both RSS 2.0 (<item>) and Atom (<entry>) feeds.
    for item in root.iter():
        tag = item.tag.lower().split("}")[-1]
        if tag not in ("item", "entry"):
            continue

        def find_text(*names):
            for child in item:
                child_tag = child.tag.lower().split("}")[-1]
                if child_tag in names:
                    return (child.text or "").strip()
            return ""

        title = strip_html(find_text("title"))

        link = find_text("link")
        if not link:
            for child in item:
                if child.tag.lower().split("}")[-1] == "link":
                    link = child.attrib.get("href", "")
                    break

        summary_raw = find_text("description", "summary", "content")
        summary = truncate(strip_html(summary_raw), config.SUMMARY_MAX_CHARS)

        date_raw = find_text("pubdate", "published", "updated", "date")
        date = parse_rss_date(date_raw)

        if title and link:
            items.append(
                {"title": title, "link": link, "summary": summary, "date": date}
            )
        if len(items) >= limit:
            break
    return items


def fetch_rss(name, url, limit):
    try:
        raw = fetch_url(url)
        return parse_rss(raw, limit)
    except (urllib.error.URLError, ET.ParseError, TimeoutError) as exc:
        print(f"  [skipped] {name}: {exc}")
        return []


def classify(text):
    lowered = text.lower()
    for category in config.CATEGORIES:
        keywords = config.CATEGORY_KEYWORDS.get(category, [])
        if any(kw in lowered for kw in keywords):
            return category
    return None


def collect_fixed_sources():
    results = []
    for src in config.FIXED_RSS_SOURCES:
        print(f"Fetching {src['name']}...")
        items = fetch_rss(src["name"], src["url"], config.MAX_ITEMS_PER_RSS_SOURCE)
        for item in items:
            results.append({**item, "source": src["name"], "category": src["category"]})
    return results


def collect_auto_sources():
    results = []
    for src in config.AUTO_RSS_SOURCES:
        print(f"Fetching {src['name']}...")
        items = fetch_rss(src["name"], src["url"], config.MAX_ITEMS_PER_RSS_SOURCE * 3)
        kept = 0
        for item in items:
            category = classify(item["title"] + " " + item["summary"])
            if category is None:
                category = src.get("fallback_category")
            if category is None:
                continue
            results.append({**item, "source": src["name"], "category": category})
            kept += 1
            if kept >= config.MAX_ITEMS_PER_RSS_SOURCE:
                break
    return results


def fetch_pubmed(category, query, limit):
    print(f"Fetching PubMed: {category}...")
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    search_params = urllib.parse.urlencode(
        {
            "db": "pubmed",
            "term": query,
            "retmax": limit,
            "sort": "date",
            "retmode": "json",
            "datetype": "pdat",
            "reldate": 30,
        }
    )
    try:
        search_raw = fetch_url(base + "esearch.fcgi?" + search_params)
        ids = json.loads(search_raw)["esearchresult"].get("idlist", [])
        if not ids:
            return []
        summary_params = urllib.parse.urlencode(
            {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
        )
        summary_raw = fetch_url(base + "esummary.fcgi?" + summary_params)
        summary_json = json.loads(summary_raw)
        results = []
        for pmid in ids:
            record = summary_json.get("result", {}).get(pmid)
            if not record:
                continue
            title = strip_html(record.get("title", ""))
            journal = record.get("fulljournalname", "PubMed")
            pubdate = record.get("pubdate", "")
            results.append(
                {
                    "title": title,
                    "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "summary": f"{journal} — {pubdate}",
                    "date": None,
                    "source": "PubMed",
                    "category": category,
                }
            )
        return results
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, TimeoutError) as exc:
        print(f"  [skipped] PubMed ({category}): {exc}")
        return []


def collect_pubmed():
    results = []
    for category, query in config.PUBMED_QUERIES.items():
        results.extend(
            fetch_pubmed(category, query, config.MAX_ITEMS_PER_PUBMED_QUERY)
        )
    return results


def dedupe(items):
    seen_links = set()
    unique = []
    for item in items:
        if item["link"] in seen_links:
            continue
        seen_links.add(item["link"])
        unique.append(item)
    return unique


def group_by_category(items):
    grouped = {c: [] for c in config.CATEGORIES}
    for item in items:
        grouped.setdefault(item["category"], []).append(item)
    for category, group in grouped.items():
        group.sort(key=lambda i: i["date"] or datetime.min.replace(tzinfo=None), reverse=True)
    return grouped


def render_html(grouped, generated_at):
    parts = [
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        f"<title>Daily Digest — {generated_at:%B %d, %Y}</title>",
        "<style>",
        """
        body { font-family: -apple-system, Helvetica, Arial, sans-serif;
               max-width: 720px; margin: 0 auto; padding: 24px 16px 64px;
               background: #fafaf8; color: #1f2430; }
        h1 { font-size: 1.5rem; margin-bottom: 0; }
        .subtitle { color: #6b7280; margin-top: 4px; margin-bottom: 32px; font-size: 0.9rem; }
        h2 { font-size: 1.05rem; text-transform: uppercase; letter-spacing: 0.04em;
             color: #4a5568; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;
             margin-top: 40px; }
        .item { padding: 14px 0; border-bottom: 1px solid #edf0f3; }
        .item:last-child { border-bottom: none; }
        .item a { font-size: 1.02rem; font-weight: 600; color: #1a56db;
                  text-decoration: none; }
        .item a:hover { text-decoration: underline; }
        .item .summary { margin: 4px 0 0; color: #374151; font-size: 0.92rem; }
        .item .meta { margin-top: 4px; color: #9ca3af; font-size: 0.78rem; }
        .empty { color: #9ca3af; font-style: italic; padding: 10px 0; }
        """,
        "</style></head><body>",
        "<h1>Your Daily Digest</h1>",
        f"<p class='subtitle'>Generated {generated_at:%A, %B %d, %Y at %I:%M %p}</p>",
    ]

    for category in config.CATEGORIES:
        items = grouped.get(category, [])
        parts.append(f"<h2>{html.escape(category)}</h2>")
        if not items:
            parts.append("<p class='empty'>No fresh items today.</p>")
            continue
        for item in items:
            date_str = item["date"].strftime("%b %d, %Y") if item["date"] else ""
            meta = f"{html.escape(item['source'])}" + (f" · {date_str}" if date_str else "")
            parts.append(
                "<div class='item'>"
                f"<a href='{html.escape(item['link'])}' target='_blank' rel='noopener'>"
                f"{html.escape(item['title'])}</a>"
                f"<p class='summary'>{html.escape(item['summary'])}</p>"
                f"<p class='meta'>{meta}</p>"
                "</div>"
            )

    parts.append("</body></html>")
    return "\n".join(parts)


def main():
    all_items = []
    all_items.extend(collect_fixed_sources())
    all_items.extend(collect_auto_sources())
    all_items.extend(collect_pubmed())
    all_items = dedupe(all_items)

    grouped = group_by_category(all_items)

    generated_at = datetime.now()
    output_html = render_html(grouped, generated_at)

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"digest-{generated_at:%Y-%m-%d}.html"
    out_path.write_text(output_html, encoding="utf-8")

    SITE_INDEX_PATH.parent.mkdir(exist_ok=True)
    SITE_INDEX_PATH.write_text(output_html, encoding="utf-8")

    total = sum(len(v) for v in grouped.values())
    print(f"\nSaved {total} items to {out_path}")
    print(f"Updated site page at {SITE_INDEX_PATH}")

    if not IS_CI:
        webbrowser.open(f"file://{out_path.resolve()}")


if __name__ == "__main__":
    main()
