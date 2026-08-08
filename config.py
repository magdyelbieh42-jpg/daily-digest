"""
Source configuration for the daily digest.
Edit this file to add/remove RSS feeds, PubMed queries, or category keywords.
No API keys required -- everything here is a free, public RSS feed or the
free NCBI PubMed E-utilities API.
"""

CATEGORIES = [
    "Adolescent Psychology & Child Development",
    "Behavioral Therapy (ABA & CBT)",
    "School Counseling & Education Trends",
    "Child & Parent Mental Health",
]

# Keyword lists used to auto-classify items from general/mixed feeds
# (e.g. regional news outlets, general APA news) into one of the categories
# above. Matching is case-insensitive substring matching against the
# item's title + summary. Order matters: a source checks categories in this
# order and assigns the first one with a keyword match.
CATEGORY_KEYWORDS = {
    "Adolescent Psychology & Child Development": [
        "adolescen", "teen", "child development", "puberty",
        "developmental psychology", "youth mental",
    ],
    "Behavioral Therapy (ABA & CBT)": [
        "behavior therapy", "behaviour therapy", "cognitive behavioral",
        "cognitive behavioural", "cbt", "applied behavior analysis",
        " aba ", "behavioral intervention", "behaviour analysis",
        "behavior analyst",
    ],
    "School Counseling & Education Trends": [
        "school", "classroom", "teacher", "education", "counselor",
        "counsellor", "curriculum", "student",
    ],
    "Child & Parent Mental Health": [
        "parent", "mental health", "anxiety", "depression",
        "family therapy", "child psychiatry", "adhd", "autism",
        "wellbeing", "well-being",
    ],
}

# RSS feeds with a FIXED category (used as-is, not keyword filtered).
# Note: APA's own RSS feeds are blocked for automated/script requests
# (Incapsula bot protection returns an empty page), so they're deliberately
# left out here even though they're publicly documented feeds.
FIXED_RSS_SOURCES = [
    {
        "name": "ScienceDaily: Child Development",
        "url": "https://www.sciencedaily.com/rss/mind_brain/child_development.xml",
        "category": "Adolescent Psychology & Child Development",
    },
    {
        "name": "ADDitude Magazine",
        "url": "https://www.additudemag.com/feed/",
        "category": "Behavioral Therapy (ABA & CBT)",
    },
    {
        "name": "NPR: Education",
        "url": "https://www.npr.org/rss/rss.php?id=1013",
        "category": "School Counseling & Education Trends",
    },
    {
        "name": "K-12 Dive",
        "url": "https://www.k12dive.com/feeds/news/",
        "category": "School Counseling & Education Trends",
    },
]

# RSS feeds that are general/mixed -- each item gets auto-classified using
# CATEGORY_KEYWORDS. If no keyword matches, the item is dropped, UNLESS
# "fallback_category" is set, in which case it goes there instead.
AUTO_RSS_SOURCES = [
    {
        "name": "PsyPost",
        "url": "https://www.psypost.org/feed/",
        "fallback_category": None,
    },
    {
        "name": "Neuroscience News",
        "url": "https://neurosciencenews.com/feed/",
        "fallback_category": None,
    },
    {
        "name": "Child Mind Institute",
        "url": "https://childmind.org/feed/",
        "fallback_category": "Child & Parent Mental Health",
    },
    {
        "name": "Egypt Independent",
        "url": "https://www.egyptindependent.com/feed/",
        "fallback_category": None,
    },
    {
        "name": "Daily News Egypt",
        "url": "https://www.dailynewsegypt.com/feed/",
        "fallback_category": None,
    },
    {
        "name": "Arab News",
        "url": "https://www.arabnews.com/rss.xml",
        "fallback_category": None,
    },
]

# PubMed search terms per category (via free NCBI E-utilities, no API key).
PUBMED_QUERIES = {
    "Adolescent Psychology & Child Development": "adolescent psychology",
    "Behavioral Therapy (ABA & CBT)": (
        '"cognitive behavioral therapy" OR "applied behavior analysis"'
    ),
    "School Counseling & Education Trends": (
        '"school counseling" OR "school psychology"'
    ),
    "Child & Parent Mental Health": '"child mental health" OR "parent training"',
}

MAX_ITEMS_PER_RSS_SOURCE = 5
MAX_ITEMS_PER_PUBMED_QUERY = 4
SUMMARY_MAX_CHARS = 220

# --- Front page (docs/index.html) presentation ---

MASTHEAD_TITLE = "The Behavioral Brief"
MASTHEAD_TAGLINE = "Adolescent psychology · behavioral therapy · education · Egypt & global"

# The front page shows only the top N items by relevance score (the full,
# unranked list for every item found still gets saved locally under digests/).
MAX_FRONT_PAGE_ITEMS = 10

# Issue number is computed from days elapsed since this date -- no counter
# file to maintain, just deterministic based on today's date.
ISSUE_EPOCH = "2026-08-08"

# Words/phrases that mark an item as Egypt/Middle East relevant, for ranking
# purposes (extra weight) regardless of which source it came from.
EGYPT_ME_KEYWORDS = [
    "egypt", "cairo", "arab", "middle east", "mena", "gulf", "saudi",
    "jordan", "lebanon", "uae", "emirates", "qatar", "kuwait", "bahrain",
    "oman", "palestin", "jerusalem", "syria", "iraq",
]

# Sources that are inherently Egypt/Middle East focused get this flat bonus
# added on top of any keyword matches above.
EGYPT_ME_SOURCES = {"Egypt Independent", "Daily News Egypt", "Arab News"}

# Relative weights used when scoring items for the front page ranking.
TOPIC_KEYWORD_WEIGHT = 2
EGYPT_ME_KEYWORD_WEIGHT = 3
EGYPT_ME_SOURCE_BONUS = 4
RECENCY_WEIGHT = 5
RECENCY_HALF_LIFE_DAYS = 3
