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
    Mandatory PDF Requirement:
    - HTML tag temizliği yapılmalıdır.
    - Fazla boşluklar temizlenmelidir.
    - Gereksiz özel karakterler temizlenmelidir.
    """
    if not raw_html:
        return ""
    # Remove HTML tags using bs4
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ")
    
    # Remove extra spaces and newlines
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
        
        # Most news sites put content in <p> tags inside an article or content div.
        # We will extract all <p> text that belongs to the main body.
        paragraphs = soup.find_all('p')
        content = " ".join([p.get_text() for p in paragraphs])
        
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
