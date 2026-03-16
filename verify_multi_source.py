from pymongo import MongoClient

def verify():
    client = MongoClient('mongodb://localhost:27017')
    db = client.kocaeli_news
    news_list = list(db.news.find({}))
    
    multi_source = [n for n in news_list if len(n.get('sources', [])) > 1]
    
    print(f"Total News in DB: {len(news_list)}")
    print(f"Items with more than 1 source: {len(multi_source)}")
    
    for n in multi_source:
        print(f"\n[MUTLI-SOURCE] {n['title']}")
        for s in n['sources']:
            print(f"  - {s['name']}: {s['url']}")

if __name__ == "__main__":
    verify()
