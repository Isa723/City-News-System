import requests
import asyncio
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse
from functools import partial

# Only crawl these sections (user-requested tokens for discovery)
TARGET_SECTION_TOKENS = [
    ("gundem", ["gundem", "gündem", "Gündem"]),
    ("asayis", ["asayis", "asayiş", "Asayiş"]),
    ("yerelhaberler", ["yerelhaberler", "yerel haberler", "yerelhaber", "yerel haber", "Yerel Haberler"]),
    ("sontak", ["sontak", "sondakika", "son dakika", "son-dakika", "Son Dakika"]),
    ("yasam", ["yasam", "yaşam", "Yaşam"]),
]

# Listing-first crawling config (User specified sections)
SITE_CONFIGS = {
    "Çağdaş Kocaeli": {
        "base": "https://www.cagdaskocaeli.com.tr",
        "sections": ["/guncel", "/gundem", "/yasam", "/asayis", "/kultur-sanat"],
    },
    "Özgür Kocaeli": {
        "base": "https://www.ozgurkocaeli.com.tr",
        "sections": ["/gundem", "/guncel", "/asayis", "/yasam", "/son-dakika"],
    },
    "Ses Kocaeli": {
        "base": "https://www.seskocaeli.com",
        "sections": ["/gundem", "/asayis", "/yasam"],
    },
    "Yeni Kocaeli": {
        "base": "https://www.yenikocaeli.com",
        "sections": ["/guncel", "/polis-adliye", "/yasam"],
    },
    "Bizim Yaka": {
        "base": "https://www.bizimyaka.com",
        "sections": ["/gundem", "/asayis", "/yasam"],
    },
}

# RSS fallback (used when listing crawl is blocked/un-discoverable).
RSS_FEEDS = {
    "Çağdaş Kocaeli": "https://www.cagdaskocaeli.com.tr/rss",
    "Özgür Kocaeli": "https://www.ozgurkocaeli.com.tr/rss",
    "Ses Kocaeli": "https://www.seskocaeli.com/rss",
    "Yeni Kocaeli": "https://www.yenikocaeli.com/rss",
    "Bizim Yaka": "https://www.bizimyaka.com/rss",
}

# Section token filter for URLs (best-effort, to avoid missing content).
ALLOWED_SECTION_URL_TOKENS = [
    "gundem", "guncel", "asayis", "polis-adliye", "yerel", "son-dakika", "sondakika", "yasam"
]

DISALLOWED_SECTION_URL_TOKENS = [
    "spor", "ekonomi", "dunya", "saglik", "magazin", "teknoloji", "siyaset"
]

def _normalize_for_tokens(s: str) -> str:
    s = (s or "").lower()
    s = (
        s.replace("ç", "c")
         .replace("ğ", "g")
         .replace("ı", "i")
         .replace("İ", "i")
         .replace("ö", "o")
         .replace("ş", "s")
         .replace("ü", "u")
    )
    s = re.sub(r"[\s\-_]+", " ", s).strip()
    return s

def clean_html_text(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ")
    text = "".join(ch for ch in text if ch.isprintable())
    text = re.sub(r'[^\w\s\.\,!\?\-\:\(\)]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_any_date(date_str):
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt
    except Exception:
        return None

def url_matches_allowed_sections(url: str) -> bool:
    n = _normalize_for_tokens(url)
    for t in DISALLOWED_SECTION_URL_TOKENS:
        if t in n:
            return False
    for t in ALLOWED_SECTION_URL_TOKENS:
        if t in n:
            return True
    return True

def parse_rss_entry_datetime(entry) -> datetime | None:
    for attr in ("published", "updated", "pubDate"):
        raw = getattr(entry, attr, None)
        if raw:
            dt = parse_any_date(raw)
            if dt:
                return dt
    return None

def extract_rss_entry_content(entry) -> str:
    raw = getattr(entry, "summary", None) or getattr(entry, "description", None) or ""
    return clean_html_text(raw)

def scrape_rss_source_paginated(
    source_name: str,
    feed_url: str,
    start_dt: datetime,
    end_dt: datetime,
    max_pages: int = 5,
) -> list[dict]:
    scraped: list[dict] = []
    seen_urls: set[str] = set()
    feed_variants = lambda u, n: [u, f"{u}?paged={n}", f"{u}?page={n}"]

    for page_num in range(1, max_pages + 1):
        page_entries_added = 0
        found_old = False

        for variant in feed_variants(feed_url, page_num):
            try:
                resp = requests.get(variant, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            except Exception:
                continue
            if resp.status_code != 200:
                continue

            feed = feedparser.parse(resp.content)
            entries = getattr(feed, "entries", None) or []
            if not entries:
                continue

            for entry in entries:
                url = getattr(entry, "link", None) or getattr(entry, "id", None)
                if not url or url in seen_urls:
                    continue

                pub_date = parse_rss_entry_datetime(entry)
                if not pub_date:
                    continue

                if pub_date < start_dt:
                    found_old = True
                    continue

                if pub_date > end_dt:
                    continue

                if not url_matches_allowed_sections(url):
                    continue

                title = clean_html_text(getattr(entry, "title", "") or "")
                content = extract_rss_entry_content(entry)
                if len(content) < 120:
                    detail_title, detail_content, _ = scrape_article_details(url)
                    if detail_content:
                        content = detail_content
                    if not title and detail_title:
                        title = detail_title

                if not title:
                    continue

                scraped.append({
                    "title": title,
                    "content": content,
                    "url": url,
                    "source": source_name,
                    "publish_date": pub_date.isoformat(),
                })
                seen_urls.add(url)
                page_entries_added += 1

            # If we've seen items and now strictly finding old ones, we can stop after the full page is checked.
            if found_old and page_entries_added == 0:
                return scraped
            # Otherwise, dont break mid-page because of sticky/unsorted posts.
            break

        if page_entries_added == 0 and found_old:
            break
    return scraped

def normalize_link(href: str, base_url: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith("//"):
        href = f"{urlparse(base_url).scheme}:{href}"
    elif href.startswith("/"):
        href = urljoin(base_url, href)
    elif not href.startswith("http"):
        href = urljoin(base_url, href)

    parsed = urlparse(href)
    base_host = urlparse(base_url).netloc
    if parsed.netloc != base_host:
        return None
    return href.split("#")[0]

def extract_listing_links(listing_html: bytes, base_url: str) -> list[str]:
    soup = BeautifulSoup(listing_html, "lxml")
    links: set[str] = set()
    for a in soup.find_all("a", href=True):
        url = normalize_link(a.get("href"), base_url)
        if not url:
            continue
        p = urlparse(url).path.lower()
        # Broadened filter: catch /haber/, /haberler/, /news/ OR any reasonably long slug with digits (common in many sites)
        if any(tok in p for tok in ["/haber/", "/haberler/", "/news/", "/guncel/", "/asayis/", "/yasam/", "/gundem/"]):
            links.add(url)
        elif re.search(r"/\d+/", p) or (len(p.split("/")) > 2 and len(p) > 20):
            # Also catch patterns like /category/12345-slug or /2026/03/26/slug
            links.add(url)
    return sorted(links)

def extract_publish_date_from_soup(soup: BeautifulSoup) -> datetime | None:
    meta_selectors = [
        ("meta", {"property": "article:published_time"}, "content"),
        ("meta", {"name": "article:published_time"}, "content"),
        ("meta", {"name": "pubdate"}, "content"),
        ("meta", {"name": "publish-date"}, "content"),
        ("meta", {"itemprop": "datePublished"}, "content"),
        ("time", {"datetime": True}, "datetime"),
    ]
    for tag_name, attrs, attr_name in meta_selectors:
        tag = soup.find(tag_name, attrs=attrs)
        if tag:
            raw = tag.get(attr_name)
            dt = parse_any_date(raw)
            if dt:
                return dt
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.get_text() or ""
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', raw)
        if m:
            dt = parse_any_date(m.group(1))
            if dt:
                return dt
    return None

def scrape_article_details(url: str) -> tuple[str, str, datetime | None]:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            return "", "", None

        soup = BeautifulSoup(response.content, "lxml")
        publish_dt = extract_publish_date_from_soup(soup)
        title = ""
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            title = clean_html_text(og_title.get("content"))
        if not title and soup.title:
            title = clean_html_text(soup.title.get_text())

        content_container = soup.find("div", class_=re.compile(r"article-content|news-content|detail-content|entry-content|habericerik|detay-metin", re.I))
        paragraphs = content_container.find_all("p") if content_container else soup.find_all("p")
        clean_paragraphs = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 35]
        content = clean_html_text(" ".join(clean_paragraphs))
        return title, content, publish_dt
    except Exception:
        return "", "", None

async def scrape_section_targeted(source_name: str, base_url: str, section_path: str, start_dt: datetime, end_dt: datetime) -> list[dict]:
    section_url = urljoin(base_url, section_path)
    scraped = []
    try:
        loop = asyncio.get_event_loop()
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = await loop.run_in_executor(None, partial(requests.get, section_url, headers=headers, timeout=15))
        if resp.status_code != 200:
            return []
        
        links = extract_listing_links(resp.content, base_url)
        for link in links[:40]: # Increased from 15 to 40 for better coverage
            title, content, pub_dt = await loop.run_in_executor(None, partial(scrape_article_details, link))
            if not title or not content:
                continue
            if not pub_dt:
                pub_dt = datetime.now(pytz.utc)
            if pub_dt < start_dt or pub_dt > end_dt:
                continue
            scraped.append({
                "title": title, "content": content, "url": link,
                "source": source_name, "publish_date": pub_dt.isoformat(),
            })
    except Exception as e:
        print(f"   [!] Failed scraping {section_url}: {e}")
    return scraped

async def scrape_all_sources(date_from: str | None = None, date_to: str | None = None):
    scraped_data: list[dict] = []
    now_utc = datetime.now(pytz.utc)
    start_dt = datetime.fromisoformat((date_from or "").replace("Z", "+00:00")) if date_from else (now_utc - timedelta(days=3))
    end_dt = datetime.fromisoformat((date_to or "").replace("Z", "+00:00")) if date_to else now_utc
    if start_dt.tzinfo is None: start_dt = pytz.utc.localize(start_dt)
    if end_dt.tzinfo is None: end_dt = pytz.utc.localize(end_dt)

    seen_urls_global: set[str] = set()
    tasks = []

    print("⏳ Starting parallel RSS and Section scraping...")
    for source_name, feed_url in RSS_FEEDS.items():
        tasks.append(asyncio.to_thread(scrape_rss_source_paginated, source_name, feed_url, start_dt, end_dt, 8)) # Increased from 6 to 8

    for source_name, config in SITE_CONFIGS.items():
        base = str(config["base"])
        for section in config.get("sections", []):
            tasks.append(scrape_section_targeted(source_name, base, section, start_dt, end_dt))

    results = await asyncio.gather(*tasks)
    for result_list in results:
        if not result_list: continue
        for it in result_list:
            if it["url"] not in seen_urls_global:
                seen_urls_global.add(it["url"])
                scraped_data.append(it)

    print(f"✅ Total articles collected: {len(scraped_data)}")
    return scraped_data
