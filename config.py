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
SUMMARY_MAX_CHARS = 160
