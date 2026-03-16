from backend.services.nlp import classify_news

title = "Sahte Para, Uyuşturucu ve Ruhsatsız Silah Ele Geçirildi"
content = "Kocaeli'de polis ekipleri tarafından düzenlenen operasyonda sahte para ve uyuşturucu ele geçirildi. Şüpheliler gözaltına alındı."

category = classify_news(content, title=title)
print(f"Result: {category}")
