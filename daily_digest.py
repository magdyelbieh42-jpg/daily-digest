#!/usr/bin/env python3
"""
Daily Digest: adolescent psychology, behavioral therapy (ABA/CBT),
school counseling & education trends, and child/parent mental health.

Free sources only -- public RSS feeds + the free NCBI PubMed E-utilities API.
No API keys, no subscriptions, no background service. Run manually:

    python3 daily_digest.py

Generates the full ranked archive in ./digests/, a curated top-N front
page at ./docs/index.html (served by GitHub Pages), and opens the local
archive in your browser.
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


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def build_dek(text, max_chars):
    """Take whole sentences up to max_chars, instead of an arbitrary cut."""
    text = text.strip()
    if not text:
        return ""
    sentences = _SENTENCE_SPLIT_RE.split(text)
    dek = ""
    for sentence in sentences:
        candidate = f"{dek} {sentence}".strip() if dek else sentence
        if len(candidate) > max_chars and dek:
            break
        dek = candidate
        if len(dek) > max_chars:
            break
    return truncate(dek, max_chars)


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
        summary = build_dek(strip_html(summary_raw), config.SUMMARY_MAX_CHARS)

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


_PUBMED_DATE_FORMATS = ("%Y %b %d", "%Y %b", "%Y")


def parse_pubmed_date(raw):
    if not raw:
        return None
    # esummary pubdate strings look like "2026 Aug 5", "2026 Aug", or "2026".
    cleaned = raw.split("-")[0].strip()
    for fmt in _PUBMED_DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def fetch_pubmed_abstracts(ids, base):
    params = urllib.parse.urlencode(
        {"db": "pubmed", "id": ",".join(ids), "rettype": "abstract", "retmode": "xml"}
    )
    raw = fetch_url(base + "efetch.fcgi?" + params)
    root = ET.fromstring(raw)
    abstracts = {}
    for article in root.iter("PubmedArticle"):
        pmid_el = article.find(".//PMID")
        if pmid_el is None or not pmid_el.text:
            continue
        pieces = [el.text or "" for el in article.iter("AbstractText")]
        if pieces:
            abstracts[pmid_el.text] = " ".join(pieces)
    return abstracts


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

        try:
            abstracts = fetch_pubmed_abstracts(ids, base)
        except (urllib.error.URLError, ET.ParseError, TimeoutError):
            abstracts = {}

        results = []
        for pmid in ids:
            record = summary_json.get("result", {}).get(pmid)
            if not record:
                continue
            title = strip_html(record.get("title", ""))
            journal = record.get("fulljournalname", "PubMed")
            pubdate = record.get("pubdate", "")
            abstract = strip_html(abstracts.get(pmid, ""))
            dek = (
                build_dek(abstract, config.SUMMARY_MAX_CHARS)
                if abstract
                else f"New research published in {journal}."
            )
            results.append(
                {
                    "title": title,
                    "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "summary": dek,
                    "date": parse_pubmed_date(pubdate),
                    "source": journal,
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


def score_item(item, now):
    text = f"{item['title']} {item['summary']}".lower()

    topic_hits = sum(
        1
        for keywords in config.CATEGORY_KEYWORDS.values()
        for kw in keywords
        if kw in text
    )
    egypt_hits = sum(1 for kw in config.EGYPT_ME_KEYWORDS if kw in text)
    egypt_source_bonus = (
        config.EGYPT_ME_SOURCE_BONUS if item["source"] in config.EGYPT_ME_SOURCES else 0
    )

    if item["date"]:
        age_days = max(0.0, (now - item["date"]).total_seconds() / 86400)
    else:
        age_days = config.RECENCY_HALF_LIFE_DAYS  # neutral default when no date is known
    recency_score = config.RECENCY_WEIGHT * (0.5 ** (age_days / config.RECENCY_HALF_LIFE_DAYS))

    return (
        topic_hits * config.TOPIC_KEYWORD_WEIGHT
        + egypt_hits * config.EGYPT_ME_KEYWORD_WEIGHT
        + egypt_source_bonus
        + recency_score
    )


def rank_items(items, now):
    for item in items:
        item["score"] = score_item(item, now)
    return sorted(items, key=lambda i: i["score"], reverse=True)


def issue_number(today):
    epoch = datetime.strptime(config.ISSUE_EPOCH, "%Y-%m-%d").date()
    return max(1, (today - epoch).days + 1)


def render_html(ranked_items, generated_at):
    issue = issue_number(generated_at.date())
    parts = [
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        f"<title>{html.escape(config.MASTHEAD_TITLE)} — {generated_at:%B %d, %Y}</title>",
        "<link rel='preconnect' href='https://fonts.googleapis.com'>",
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>",
        "<link href='https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&display=swap' rel='stylesheet'>",
        "<style>",
        """
        body { font-family: -apple-system, Helvetica, Arial, sans-serif;
               max-width: 760px; margin: 0 auto; padding: 32px 20px 80px;
               background: #fff; color: #171717; }
        .masthead { text-align: center; }
        .masthead h1 { font-family: 'Playfair Display', Georgia, serif;
               font-weight: 900; font-size: 2.75rem; margin: 0; }
        .masthead .tagline { color: #555; font-size: 0.95rem; margin: 8px 0 0; }
        .rule-thick { border: none; border-top: 3px solid #171717; margin: 20px 0 6px; }
        .meta-line { display: flex; justify-content: space-between; color: #666;
               font-size: 0.82rem; padding-bottom: 10px; border-bottom: 1px solid #ccc;
               margin-bottom: 30px; }
        .label { text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.78rem;
               font-weight: 700; color: #1a56db; margin: 0 0 8px; }
        .story { padding: 24px 0; border-bottom: 1px solid #e6e6e6; }
        .story:last-child { border-bottom: none; }
        .story h2 { font-family: 'Playfair Display', Georgia, serif; font-weight: 700;
               font-size: 1.4rem; line-height: 1.28; margin: 0 0 10px; }
        .story.lead h2 { font-size: 2rem; }
        .story h2 a { color: #171717; text-decoration: none; }
        .story h2 a:hover { text-decoration: underline; }
        .story .dek { font-size: 1rem; color: #222; margin: 0 0 8px; line-height: 1.55; }
        .story .source { font-size: 0.8rem; color: #888; }
        .empty { color: #999; font-style: italic; padding: 20px 0; }
        """,
        "</style></head><body>",
        "<div class='masthead'>",
        f"<h1>{html.escape(config.MASTHEAD_TITLE)}</h1>",
        f"<p class='tagline'>{html.escape(config.MASTHEAD_TAGLINE)}</p>",
        "</div>",
        "<hr class='rule-thick'>",
        "<div class='meta-line'>"
        f"<span>{generated_at:%A, %B %d, %Y}</span>"
        f"<span>Issue no. {issue}</span>"
        "</div>",
    ]

    if not ranked_items:
        parts.append("<p class='empty'>No fresh items today — check back tomorrow.</p>")
    else:
        for i, item in enumerate(ranked_items):
            is_lead = i == 0
            date_str = item["date"].strftime("%b %d, %Y") if item["date"] else ""
            source_line = html.escape(item["source"]) + (f" · {date_str}" if date_str else "")
            parts.append(f"<div class='story{' lead' if is_lead else ''}'>")
            if is_lead:
                parts.append("<p class='label'>Lead story</p>")
            parts.append(
                f"<h2><a href='{html.escape(item['link'])}' target='_blank' rel='noopener'>"
                f"{html.escape(item['title'])}</a></h2>"
                f"<p class='dek'>{html.escape(item['summary'])}</p>"
                f"<p class='source'>{source_line}</p>"
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

    generated_at = datetime.now()
    ranked_items = rank_items(all_items, generated_at)

    # Full ranked list, saved locally for your own reference/archive.
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"digest-{generated_at:%Y-%m-%d}.html"
    out_path.write_text(render_html(ranked_items, generated_at), encoding="utf-8")

    # Curated front page: only the top N stories by relevance score.
    front_page_items = ranked_items[: config.MAX_FRONT_PAGE_ITEMS]
    SITE_INDEX_PATH.parent.mkdir(exist_ok=True)
    SITE_INDEX_PATH.write_text(
        render_html(front_page_items, generated_at), encoding="utf-8"
    )

    print(f"\nSaved {len(ranked_items)} items to {out_path}")
    print(f"Updated site page ({len(front_page_items)} items) at {SITE_INDEX_PATH}")

    if not IS_CI:
        webbrowser.open(f"file://{out_path.resolve()}")


if __name__ == "__main__":
    main()
