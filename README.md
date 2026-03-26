# Yazlab 2 - Proje 1 (Kocaeli Haber Harita Sistemi)

Bu proje, **Kocaeli yerel haber sitelerinden** (PDF’de verilen 5 kaynak) son haberleri otomatik çekip **MongoDB**’ye kaydeder; haber türünü sınıflandırır, metinden konum çıkarır, **Google Geocoding** ile koordinat üretir ve **Google Maps** üzerinde görselleştirir.

## Özellikler (PDF ile uyumlu)
- **Kaynaklar**: Çağdaş Kocaeli, Özgür Kocaeli, Ses Kocaeli, Yeni Kocaeli, Bizim Yaka (RSS + detay sayfa içerik çekimi)
- **Zaman aralığı**: Varsayılan **son 3 gün**; UI'da tarih aralığı seçip filtreleyebilirsiniz
- **Alanlar**: kategori, başlık, içerik, yayın tarihi, konum metni + lat/lng, ilçe, kaynak(lar) ve link(ler)
- **Dedup**:
  - Aynı URL tekrar kaydedilmez
  - Farklı sitelerde aynı içerik: embedding benzerliği **>= 0.90** ise tek haber olarak tutulur ve **sources[]** listesine eklenir
- **Konum**: Metinden mahalle/cadde/sokak/ilçe adayları çıkarılır, bulunamazsa haber haritada gösterilmez
- **Geocoding**: API anahtarı `.env` ile saklanır; gereksiz tekrarlar için **MongoDB geocache** kullanılır
- **Harita**: Kocaeli merkez; kategoriye göre farklı renk/sembol; marker tıklayınca başlık/tarih/konum/kaynaklar + "Habere Git"
- **Dinamik filtre**: sayfa yenilenmeden marker'lar güncellenir
## Kurulum

### 1) Sanal ortam ve bağımlılıklar

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) MongoDB
- Lokal MongoDB çalıştırın: `mongodb://localhost:27017`

### 3) Google API anahtarları (.env)
Proje kök dizinine `.env` dosyası oluşturun (gitignore’da zaten var):

```env
# Geocoding için
GOOGLE_MAPS_API_KEY=YOUR_KEY

# Frontend Google Maps JS için (isterseniz aynı anahtar olabilir)
GOOGLE_MAPS_JS_API_KEY=YOUR_KEY

# Opsiyonel: backend açılır açılmaz scraping tetiklensin
SCRAPE_ON_STARTUP=true
```

> Not: `frontend/index.html` içinde **hardcoded key yoktur**. Frontend, anahtarı backend’deki `/api/config` endpoint’inden alıp Google Maps JS’i dinamik yükler.

## Çalıştırma

### Backend (FastAPI)

```bash
.\.venv\Scripts\python.exe backend\main.py
```

Arayüz: `http://localhost:8000/app`

### Manuel scraping
- UI'daki **"Yeni Haberleri Çek"** butonu `POST /api/scrape` çağırır.
- İsterseniz tarih aralığına göre: UI tarih alanlarını seçip butona basın (backend `--date-from/--date-to` ile runner'ı çağırır).

### Scraper’ı terminalden çalıştırma

```bash
.\.venv\Scripts\python.exe backend\scraper_runner.py
```

Tarih aralığı ile:

```bash
.\.venv\Scripts\python.exe backend\scraper_runner.py --date-from 2026-03-16T00:00:00Z --date-to 2026-03-19T23:59:59Z
```

## API
- `GET /api/news?category=...&district=...&source=...&date_from=...&date_to=...`
- `POST /api/scrape?date_from=...&date_to=...`
- `GET /api/config` (frontend bootstrap için)

