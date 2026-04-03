"""
scraper.py — Listing discovery + parallel article fetch using requests.

Cloudflare: harvest cf_clearance (and __cf_bm) once per origin via SeleniumBase UC,
then reuse on all HTTP requests for that host.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, time
from urllib.parse import urlparse, urljoin

import pytz
import requests as _requests
from bs4 import BeautifulSoup

from services.cf_bypass import get_bypass_headers, harvest_cloudflare_cookies

# Fix Unicode printing issues on CMD
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def default_last_three_calendar_days_iso() -> tuple[str, str]:
    """
    Inclusive window: today, yesterday, and the day before (Europe/Istanbul calendar).
    Returned as UTC ISO strings for the API / DB pipeline.
    """
    tz = pytz.timezone("Europe/Istanbul")
    today = datetime.now(tz).date()
    start_local = tz.localize(datetime.combine(today - timedelta(days=2), time.min))
    end_local = tz.localize(datetime.combine(today, time(23, 59, 59, 999999)))
    start_utc = start_local.astimezone(pytz.UTC)
    end_utc = end_local.astimezone(pytz.UTC)
    return (
        start_utc.isoformat().replace("+00:00", "Z"),
        end_utc.isoformat().replace("+00:00", "Z"),
    )


def _request_headers(url: str, referer: str | None = None) -> dict[str, str]:
    h = get_bypass_headers(url)
    netloc = urlparse(url).netloc
    scheme = urlparse(url).scheme or "https"
    h["Referer"] = referer or f"{scheme}://{netloc}/"
    return h


def _is_yenikocaeli(url: str) -> bool:
    return "yenikocaeli.com" in urlparse(url).netloc.lower()


def _http_get(url: str, *, referer: str | None = None) -> _requests.Response:
    """
    Yeni Kocaeli is often down or very slow: short timeout, no retries — fail fast.
    Other sites use a slightly longer budget and one retry.
    """
    headers = _request_headers(url, referer=referer)
    if _is_yenikocaeli(url):
        timeout = (5, 14)  # (connect, read) seconds — bail out quickly
        attempts = 1
    else:
        timeout = (12, 28)
        attempts = 2

    last_err: Exception | None = None
    for i in range(attempts):
        try:
            return _requests.get(url, headers=headers, timeout=timeout)
        except (_requests.exceptions.Timeout, _requests.exceptions.ConnectionError) as e:
            last_err = e
            if i + 1 < attempts:
                time.sleep(1.5 * (i + 1))
    assert last_err is not None
    raise last_err


# Archive listings use /2, /3, … after the first page; cap to avoid runaway requests.
ARCHIVE_LISTING_MAX_PAGES = 15


def _merge_listing_links(
    soup: BeautifulSoup,
    base_url: str,
    base_host: str,
    art_pat: re.Pattern[str],
    links: list[str],
    link_set: set[str],
) -> int:
    """Append new article URLs from one listing page; return how many were new."""
    added = 0
    for a in soup.find_all("a", href=True):
        href = str(a["href"]).strip()
        full = urljoin(base_url + "/", href).split("#")[0].split("?")[0].rstrip("/")
        full_host = urlparse(full).netloc.replace("www.", "")
        if full_host == base_host and art_pat.search(full) and full not in link_set:
            link_set.add(full)
            links.append(full)
            added += 1
    return added


SITE_CONFIGS = [
    {
        "source": "Çağdaş Kocaeli",
        "base_url": "https://www.cagdaskocaeli.com.tr",
        "archive_pagination": True,
        "listing_urls": [
            "https://www.cagdaskocaeli.com.tr/arsiv/kocaeli-gundem-haberleri",
            "https://www.cagdaskocaeli.com.tr/arsiv/kocaeli-asayis-haberleri",
            "https://www.cagdaskocaeli.com.tr/arsiv/yasam",
            "https://www.cagdaskocaeli.com.tr/arsiv/kultur-sanat",
            "https://www.cagdaskocaeli.com.tr/arsiv/guncel",
        ],
        "article_pat": re.compile(r"/(haber|foto)/\d+", re.I),
    },
    {
        "source": "Özgür Kocaeli",
        "base_url": "https://www.ozgurkocaeli.com.tr",
        "archive_pagination": True,
        "listing_urls": [
            "https://www.ozgurkocaeli.com.tr/arsiv/kocaeli-haberleri",
            "https://www.ozgurkocaeli.com.tr/arsiv/kocaeli-asayis-haberleri",
            "https://www.ozgurkocaeli.com.tr/arsiv/guncel",
            "https://www.ozgurkocaeli.com.tr/arsiv/son-dakika",
            "https://www.ozgurkocaeli.com.tr/arsiv/kocaeli-yasam-haberleri",
        ],
        "article_pat": re.compile(r"/haber/\d+", re.I),
    },
    {
        "source": "Ses Kocaeli",
        "base_url": "https://www.seskocaeli.com",
        "archive_pagination": True,
        "listing_urls": [
            "https://www.seskocaeli.com/arsiv/kocaeli-son-dakika-haberler",
            "https://www.seskocaeli.com/arsiv/kocaeli-asayis-haberleri",
            "https://www.seskocaeli.com/arsiv/kocaeli-yasam-haberleri",
        ],
        "article_pat": re.compile(r"/haber/\d+", re.I),
    },
    {
        "source": "Bizim Yaka",
        "base_url": "https://www.bizimyaka.com",
        "archive_pagination": True,
        "listing_urls": [
            "https://www.bizimyaka.com/arsiv/kocaeli-son-dakika-haberleri",
            "https://www.bizimyaka.com/arsiv/kocaeli-asayis-haberleri",
            "https://www.bizimyaka.com/arsiv/yasam-haberleri",
        ],
        "article_pat": re.compile(r"/haber/\d+", re.I),
    },
]

_TR_MONTHS = {
    "ocak": 1,
    "şubat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "eylül": 9,
    "ekim": 10,
    "kasım": 11,
    "aralık": 12,
}

_EN_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def _localize_istanbul(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(pytz.utc)
    return pytz.timezone("Europe/Istanbul").localize(dt).astimezone(pytz.utc)


def _parse_date(raw: str | None) -> datetime | None:
    """Parse human / meta date strings to UTC. Never use scrape time as substitute."""
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None

    # ISO-8601 only when it actually looks like ISO (avoid fromisoformat on random text)
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        try:
            iso = s.strip().replace("Z", "+00:00")
            main, sep, tz = iso.partition("+")
            main = main.strip()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", main):
                iso = main + "T00:00:00" + ("+" + tz if sep else "")
            elif re.match(r"^\d{4}-\d{2}-\d{2} \d", main) and "T" not in main[:13]:
                iso = main.replace(" ", "T", 1) + ("+" + tz if sep else "")
            dt = datetime.fromisoformat(iso)
            return _localize_istanbul(dt)
        except ValueError:
            pass

    sl = s.lower()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%d.%m.%Y",
        "%d/%m/%Y",
    ):
        try:
            chunk = sl[:40]
            dt = datetime.strptime(chunk, fmt)
            return _localize_istanbul(dt)
        except ValueError:
            continue

    # "25 Mart 2026 - 22:10" / "25 Mar 2026 - 22:10" / "25 mart 2026 22:10"
    m = re.search(
        r"(\d{1,2})\s+([a-zçğıöşü]{3,9}|[a-z]{3,9})\s+(\d{4})\s*(?:[-–]\s*)?(?:(\d{1,2})\s*:\s*(\d{2}))?",
        sl,
    )
    if m:
        try:
            day, mon_str, year = int(m.group(1)), m.group(2), int(m.group(3))
            hour = int(m.group(4)) if m.group(4) else 0
            minute = int(m.group(5)) if m.group(5) else 0
            month = _TR_MONTHS.get(mon_str) or _EN_MONTHS.get(mon_str[:3])
            if month:
                dt = datetime(year, month, day, hour, minute)
                return _localize_istanbul(dt)
        except (ValueError, TypeError):
            pass
    return None


def _json_ld_collect_dates(obj: object) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = str(k).lower()
            if lk in ("datepublished", "datecreated", "uploaddate") and isinstance(v, str):
                found.append(v)
            found.extend(_json_ld_collect_dates(v))
    elif isinstance(obj, list):
        for x in obj:
            found.extend(_json_ld_collect_dates(x))
    return found


def _extract_publish_datetime(soup: BeautifulSoup, html: str) -> datetime | None:
    """Best-effort from meta, JSON-LD, <time>, then visible date patterns near the top."""
    _META_PRIMARY = frozenset(
        {
            "article:published_time",
            "og:published_time",
            "publish-date",
            "publishdate",
            "date",
            "dc.date.issued",
            "sailthru.date",
            "parsely-pub-date",
        }
    )
    og_updated: datetime | None = None
    for tag in soup.find_all("meta"):
        prop = (tag.get("property") or tag.get("name") or "").strip().lower()
        content = tag.get("content")
        if not content:
            continue
        dt = _parse_date(content)
        if not dt:
            continue
        if prop in _META_PRIMARY:
            return dt
        if prop == "og:updated_time":
            og_updated = dt

    for script in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for ds in _json_ld_collect_dates(data):
            dt = _parse_date(ds)
            if dt:
                return dt

    for t in soup.find_all("time"):
        dt = _parse_date(t.get("datetime"))
        if dt:
            return dt
        dt = _parse_date(t.get_text(" ", strip=True))
        if dt:
            return dt

    # Visible line like listing pages: "25 Mar 2026 - 22:10" in first 6k of body text
    blob = soup.get_text(" ", strip=True)[:6000]
    for rx in (
        r"\b(\d{1,2}\s+(?:Mart|Ocak|Şubat|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+\d{4}\s*[-–]\s*\d{1,2}:\d{2})\b",
        r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\s*[-–]\s*\d{1,2}:\d{2})\b",
    ):
        m = re.search(rx, blob, re.I)
        if m:
            dt = _parse_date(m.group(1))
            if dt:
                return dt

    if og_updated:
        return og_updated

    return None


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\xa0", " ")
    t = re.sub(r"[\r\n\t]+", " ", t)
    t = re.sub(r"[ ]{2,}", " ", t).strip()
    return t


def _is_noise_paragraph(p: str) -> bool:
    pl = (p or "").lower()
    if len(pl) < 30:
        return True
    ad_markers = (
        "reklam",
        "sponsor",
        "sponsored",
        "google news",
        "bizi takip edin",
        "abone ol",
        "bildirimleri aç",
        "yorum yap",
        "etiketler:",
        "ilgili haber",
        "tüm hakları saklıdır",
        "kaynak:",
    )
    return any(m in pl for m in ad_markers)


def _fetch_article(url: str, source: str) -> dict | None:
    try:
        r = _http_get(url)
        if r.status_code != 200:
            return None
        s = BeautifulSoup(r.text, "lxml")

        og = s.find("meta", property="og:title")
        title = (
            og["content"]
            if og and og.get("content")
            else (s.find("h1").get_text(strip=True) if s.find("h1") else s.title.get_text(strip=True))
        )
        title = _normalize_text(title)

        c_div = s.select_one(
            ".news-content, .article-content, .entry-content, article, .haber-metni, .habericerik"
        )
        if c_div:
            paras_raw = [p.get_text(" ", strip=True) for p in c_div.find_all("p")]
            paras = []
            for pr in paras_raw:
                ptxt = _normalize_text(pr)
                if _is_noise_paragraph(ptxt):
                    continue
                paras.append(ptxt)
            content = " ".join(paras) if paras else _normalize_text(c_div.get_text(separator=" ", strip=True))
        else:
            fallback = []
            for p in s.find_all("p"):
                ptxt = _normalize_text(p.get_text(" ", strip=True))
                if _is_noise_paragraph(ptxt):
                    continue
                fallback.append(ptxt)
                if len(fallback) >= 10:
                    break
            content = " ".join(fallback)
        content = _normalize_text(content)

        if not title:
            return None

        pub_dt = _extract_publish_datetime(s, r.text)
        if not pub_dt:
            # Wrong dates break the 3-day rule and the map — drop article instead of guessing.
            return None

        return {
            "title": title,
            "content": content,
            "url": url,
            "source": source,
            "publish_date": pub_dt.astimezone(pytz.utc).isoformat(),
        }
    except Exception:
        return None


def _scrape_sync(start_dt: datetime, end_dt: datetime) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()

    origins = list(dict.fromkeys(str(s["base_url"]).rstrip("/") + "/" for s in SITE_CONFIGS))
    harvest_cloudflare_cookies(origins)

    print(f"⏳ SCRAPING RANGE (UTC): {start_dt.isoformat()} … {end_dt.isoformat()}")

    for site in SITE_CONFIGS:
        source = str(site["source"])
        base_url = str(site["base_url"]).rstrip("/")
        art_pat = site["article_pat"]
        listing_referer = base_url + "/"

        print(f"\n🌐 [{source}] Fetching listing pages...")
        links: list[str] = []
        link_set: set[str] = set()
        base_host = urlparse(base_url).netloc.replace("www.", "")
        paginate = bool(site.get("archive_pagination", True))
        skip_rest_of_site = False  # Yeni Kocaeli: one failed open → skip entire source

        for listing_base in site["listing_urls"]:
            if skip_rest_of_site:
                break
            root = str(listing_base).rstrip("/")
            page = 1
            while True:
                if not paginate and page > 1:
                    break
                l_url = root if page == 1 else f"{root}/{page}"
                try:
                    r = _http_get(l_url, referer=listing_referer)
                    if r.status_code != 200:
                        if page == 1:
                            print(f"   [!] HTTP {r.status_code} {l_url}")
                            if source == "Yeni Kocaeli":
                                print("   ⏭️  Yeni Kocaeli unreachable — skipping this source.")
                                skip_rest_of_site = True
                        break
                    s = BeautifulSoup(r.text, "lxml")
                    added = _merge_listing_links(s, base_url, base_host, art_pat, links, link_set)
                    if added:
                        print(f"   Listing p{page}: {l_url} -> +{added} new links")
                    if added == 0:
                        break
                    if not paginate:
                        break
                    if page >= ARCHIVE_LISTING_MAX_PAGES:
                        break
                    page += 1
                except Exception as e:
                    if page == 1:
                        print(f"   [!] Error on {l_url}: {e}")
                        if source == "Yeni Kocaeli":
                            print("   ⏭️  Yeni Kocaeli unreachable — skipping this source.")
                            skip_rest_of_site = True
                    break

        if not links:
            continue

        workers = 6 if source == "Yeni Kocaeli" else 10
        print(f"   ⚡ Fetching {len(links)} articles in parallel (workers={workers})...")
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(_fetch_article, l, source) for l in links]
            for f in as_completed(futures):
                res = f.result()
                if not res:
                    continue
                dt = datetime.fromisoformat(res["publish_date"].replace("Z", "+00:00"))
                if start_dt <= dt <= end_dt:
                    if res["url"] not in seen:
                        seen.add(res["url"])
                        results.append(res)
                        try:
                            print(f"   ✅ {res['title'][:65]}...")
                        except Exception:
                            pass

    print(f"\n✅ Scrape finished. Items in date window: {len(results)}")
    return results


async def scrape_all_sources(date_from: str | None = None, date_to: str | None = None) -> list[dict]:
    if not date_from and not date_to:
        date_from, date_to = default_last_three_calendar_days_iso()
    now = datetime.now(pytz.utc)
    s_dt = datetime.fromisoformat(date_from.replace("Z", "+00:00")) if date_from else now - timedelta(days=3)
    e_dt = datetime.fromisoformat(date_to.replace("Z", "+00:00")) if date_to else now
    if s_dt.tzinfo is None:
        s_dt = pytz.utc.localize(s_dt)
    else:
        s_dt = s_dt.astimezone(pytz.utc)
    if e_dt.tzinfo is None:
        e_dt = pytz.utc.localize(e_dt)
    else:
        e_dt = e_dt.astimezone(pytz.utc)
    return await asyncio.to_thread(_scrape_sync, s_dt, e_dt)
