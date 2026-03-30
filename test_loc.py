from backend.services.geocoding import extract_location_info

title = "İzmit’te feci kaza: 2 yaralı"
text = "Kocaeli'nin İzmit ilçesinde meydana gelen trafik kazasında 2 kişi yaralandı. Olay yerine itfaiye ve sağlık ekipleri sevk edildi."

info = extract_location_info(title, text)
print(f"Info: {info}")
