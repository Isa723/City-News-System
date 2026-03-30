"""
One-shot Cloudflare clearance via SeleniumBase UC, then reuse with requests.
"""
from __future__ import annotations

import time
from urllib.parse import urlparse

from seleniumbase import Driver

# Reuse cookies across HTTP requests in this process
cookie_cache: dict[str, str] = {}
global_ua = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)


def harvest_cloudflare_cookies(domains: list[str]) -> bool:
    """
    Headed Chrome (UC mode), visit each origin, pass Turnstile if shown,
    store cf_clearance (and __cf_bm when present) for requests reuse.
    """
    global global_ua
    print("\n--- [Cloudflare Bypass] Spinning up SeleniumBase harvester ---")
    driver = None
    try:
        driver = Driver(uc=True, headless=False)
    except Exception as e:
        print(f"Failed to start SeleniumBase driver: {e}")
        return False

    harvested_count = 0
    try:
        for domain in domains:
            print(f"Harvesting clearance for {domain}...")
            driver.uc_open_with_reconnect(domain, 4)
            try:
                driver.uc_gui_click_captcha()
                print(" Clicked Turnstile widget.")
            except Exception:
                pass
            time.sleep(5)

            parts: list[str] = []
            for cookie in driver.get_cookies():
                name = cookie.get("name") or ""
                if name in ("cf_clearance", "__cf_bm") and cookie.get("value"):
                    parts.append(f"{name}={cookie['value']}")

            if parts:
                domain_key = urlparse(domain).netloc.replace("www.", "")
                cookie_cache[domain_key] = "; ".join(parts)
                print(f" Successfully harvested cookies for {domain_key}")
                harvested_count += 1
            else:
                print(
                    f" No cf_clearance/__cf_bm for {domain}. "
                    "IP block, slow load, or no Cloudflare on this URL."
                )

        global_ua = driver.execute_script("return navigator.userAgent;") or global_ua
    except Exception as e:
        print(f"Error during harvesting: {e}")
    finally:
        if driver:
            driver.quit()

    print(f"--- [Cloudflare Bypass] Harvested {harvested_count}/{len(domains)} origins ---\n")
    return harvested_count > 0


def get_bypass_headers(url: str) -> dict[str, str]:
    """Headers matching the UC browser; attach harvested Cloudflare cookies if any."""
    headers = {
        "User-Agent": global_ua,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    domain_key = urlparse(url).netloc.replace("www.", "")
    if domain_key in cookie_cache:
        headers["Cookie"] = cookie_cache[domain_key]
    return headers


def is_cookie_valid(domain_url: str) -> bool:
    domain_key = urlparse(domain_url).netloc.replace("www.", "")
    return domain_key in cookie_cache
