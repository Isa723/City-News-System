import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import asyncio
import re

# The 5 requested local news sources
RSS_FEEDS = {
    "Çağdaş Kocaeli": "https://www.cagdaskocaeli.com.tr/rss",
    "Özgür Kocaeli": "https://www.ozgurkocaeli.com.tr/rss",
    "Ses Kocaeli": "https://www.seskocaeli.com/rss",
    "Yeni Kocaeli": "https://www.yenikocaeli.com/rss",
    "Bizim Yaka": "https://www.bizimyaka.com/rss"
}

def clean_html_text(raw_html):
    """
    Mandatory PDF Requirement (Section 4):
    - HTML tag temizliği yapılmalıdır.
    - Fazla boşluklar temizlenmelidir.
    - Gereksiz özel karakterler temizlenmelidir.
    - Metin normalizasyonu (Lowercasing, char cleanup).
    """
    if not raw_html:
        return ""
        
    # 1. Remove HTML tags using bs4
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ")
    
    # 2. Text Normalization (Correctly handling Turkish chars for lowercasing if needed later)
    # Removing non-printable and unusual control characters
    text = "".join(ch for ch in text if ch.isprintable())
    
    # 3. Special Character Cleanup
    # Removing excessive non-standard chars while keeping punctuation
    text = re.sub(r'[^\w\s\.\,!\?\-\:\(\)]', ' ', text)
    
    # 4. Remove extra spaces and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def scrape_article_content(url):
    """
    Fetches the actual article HTML and extracts paragraphs 
    since RSS only provides a short summary.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""
            
        soup = BeautifulSoup(response.content, "lxml")
        
        # Try to find the main article container first
        # Common classes for these 5 Kocaeli sites
        content_container = soup.find('div', class_=re.compile(r'article-content|news-content|detail-content|entry-content|habericerik|detay-metin', re.I))
        
        if content_container:
            # If we found a container, only get <p> from inside it
            paragraphs = content_container.find_all('p')
        else:
            # Fallback: exclude common non-article areas then get <p>
            for junk in soup.find_all(['footer', 'nav', 'aside', 'header']):
                junk.decompose()
            paragraphs = soup.find_all('p')

        # Filter out very short strings and common boilerplate
        clean_paragraphs = []
        boilerplate_patterns = [
            r'tıklayın', r'takip edin', r'abone olun', r'yazılı haber',
            r'copyright', r'tüm hakları', r'haber merkez', r'reklam'
        ]
        
        for p in paragraphs:
            text = p.get_text().strip()
            # Length filter + ensure it's not a common boilerplate line
            if len(text) > 40: 
                is_junk = any(re.search(pat, text, re.I) for pat in boilerplate_patterns)
                if not is_junk:
                    clean_paragraphs.append(text)

        content = " ".join(clean_paragraphs)
        
        return clean_html_text(content)
    except Exception as e:
        print(f"Error scraping article {url}: {e}")
        return ""

def parse_date(date_str):
    """ Parses RSS date format to python datetime """
    try:
        # standard RSS string: "Mon, 01 Jan 2026 12:00:00 +0300"
        dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        return dt
    except Exception:
        # Fallback to current time if unparseable
        return datetime.now(pytz.utc)

async def scrape_all_sources():
    """
    Main entry point for scraping.
    Fetches the 5 RSS feeds, gets items from the last 3 days,
    and returns a list of dictionaries with raw news data.
    """
    scraped_data = []
    
    # PDF Requirement: Son 3 günlük zaman dilimi
    three_days_ago = datetime.now(pytz.utc) - timedelta(days=3)
    
    for source_name, feed_url in RSS_FEEDS.items():
        print(f"[*] Scraping strictly from: {source_name}")
        feed = feedparser.parse(feed_url)
        
        for entry in feed.entries:
            # Parse Date
            pub_date_str = getattr(entry, 'published', None)
            if pub_date_str:
                pub_date = parse_date(pub_date_str)
            else:
                continue
                
            # Filter for last 3 days only
            if pub_date < three_days_ago:
                continue
                
            # Extract basic data
            title = clean_html_text(entry.title)
            url = entry.link
            
            # Fetch Full Content
            content = scrape_article_content(url)
            
            if len(content) < 50:
                # If scraping failed or content is too short, skip
                continue
                
            news_item = {
                "title": title,
                "content": content,
                "url": url,
                "source": source_name,
                "publish_date": pub_date.isoformat(),
            }
            scraped_data.append(news_item)
            
    return scraped_data
