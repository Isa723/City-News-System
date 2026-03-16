from pymongo import MongoClient
import sys

def check():
    try:
        client = MongoClient('mongodb://localhost:27017')
        db = client.kocaeli_news
        news_items = list(db.news.find({}, {'title': 1, 'category': 1, 'url': 1}))
        
        print(f"Total News in DB: {len(news_items)}")
        print("-" * 50)
        
        # Check specific problematic ones
        target_title = "Sahte Para, Uyuşturucu ve Ruhsatsız Silah Ele Geçirildi"
        
        for item in news_items:
            cat = item.get('category')
            title = item.get('title')
            url = item.get('url')
            
            # Print all categorized items to review
            if cat != 'Diğer':
                print(f"[{cat}] {title}")
                
            if target_title in title:
                print(f"\n>>> FOUND TARGET: [{cat}] {title}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
