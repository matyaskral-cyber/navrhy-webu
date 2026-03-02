#!/usr/bin/env python3
"""
SlevyDnes scraper — stahuje aktuální slevy z kupi.cz
pro Albert, Penny, Billa a Kaufland.

Výstup: slevy.json ve formátu kompatibilním s index.html
"""

import json
import re
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

import requests
from bs4 import BeautifulSoup

# ── Konfigurace ───────────────────────────────────────────────────────
STORES = {
    "albert":   {"storeName": "Albert",   "store": "albert"},
    "penny":    {"storeName": "Penny",    "store": "penny"},
    "billa":    {"storeName": "Billa",    "store": "billa"},
    "kaufland": {"storeName": "Kaufland", "store": "kaufland"},
}

# Zdroje odkazů — letáky + kategorie
LISTING_URLS = {
    "albert":   ["https://www.kupi.cz/letaky/albert",        "https://www.kupi.cz/slevy/albert"],
    "penny":    ["https://www.kupi.cz/letaky/penny-market",   "https://www.kupi.cz/slevy/penny-market"],
    "billa":    ["https://www.kupi.cz/letaky/billa",          "https://www.kupi.cz/slevy/billa"],
    "kaufland": ["https://www.kupi.cz/letaky/kaufland",       "https://www.kupi.cz/slevy/kaufland"],
}

# Kategorie na kupi.cz — procházet pro víc produktů
CATEGORY_URLS = [
    "https://www.kupi.cz/slevy/mlecne-vyrobky-a-vejce",
    "https://www.kupi.cz/slevy/maso-drubez-a-ryby",
    "https://www.kupi.cz/slevy/ovoce-a-zelenina",
    "https://www.kupi.cz/slevy/nealko-napoje",
    "https://www.kupi.cz/slevy/pivo",
    "https://www.kupi.cz/slevy/alkohol",
    "https://www.kupi.cz/slevy/kava",
    "https://www.kupi.cz/slevy/sladkosti-a-slane-snacky",
    "https://www.kupi.cz/slevy/pecivo",
    "https://www.kupi.cz/slevy/konzervy",
    "https://www.kupi.cz/slevy/drogerie",
    "https://www.kupi.cz/slevy/mrazene-a-instantni-potraviny",
    "https://www.kupi.cz/slevy/vareni-a-peceni",
    "https://www.kupi.cz/slevy/masla",
    "https://www.kupi.cz/slevy/lahudky",
    "https://www.kupi.cz/slevy/mazlicci",
    "https://www.kupi.cz/slevy/domacnost",
    "https://www.kupi.cz/slevy/drubez",
]

OUTPUT_FILE = Path(__file__).parent / "slevy.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "cs,en;q=0.9",
}

# Emoji mapování podle kategorie
CATEGORY_EMOJI = {
    "mléčné": "🧀", "mléko": "🥛", "jogurt": "🥛", "sýr": "🧀", "máslo": "🧈",
    "maso": "🥩", "uzenin": "🌭", "kuře": "🍗", "vepřov": "🥩", "hovězí": "🥩",
    "ryb": "🐟", "tuňák": "🐟", "losos": "🐟",
    "ovoce": "🍎", "zelenin": "🥦", "brambor": "🥔", "rajč": "🍅", "jabl": "🍎",
    "banán": "🍌", "jahod": "🍓", "citron": "🍋", "hrozn": "🍇", "pomera": "🍊",
    "pečiv": "🍞", "chleb": "🍞", "rohlík": "🥐", "croissant": "🥐",
    "nápoj": "🥤", "pivo": "🍺", "víno": "🍷", "káv": "☕", "čaj": "🍵",
    "džus": "🧃", "vod": "💧", "cola": "🥤", "energy": "🥤", "limonád": "🥤",
    "čokol": "🍫", "cukrovin": "🍬", "sušenk": "🍪", "zmrzlin": "🍦",
    "konzerv": "🥫", "hotov": "🍲", "polévk": "🍲",
    "mražen": "🧊", "pizza": "🍕",
    "čisti": "🧼", "prací": "🧺", "šampon": "🧴", "mýdl": "🧼", "hygien": "🧻",
    "elektr": "📺", "domác": "🏠",
    "koření": "🧂", "olej": "🫒", "mouk": "🌾", "rýž": "🍚", "těstovin": "🍝",
    "alkohol": "🥃", "vodka": "🥃", "rum": "🥃", "whisky": "🥃", "becherovk": "🥃",
}

REQUEST_DELAY = 1.0  # sekunda mezi requesty


def get_emoji(name: str, category: str) -> str:
    """Vrátí emoji podle názvu/kategorie produktu."""
    text = f"{name} {category}".lower()
    for keyword, emoji in CATEGORY_EMOJI.items():
        if keyword in text:
            return emoji
    return "🛒"


def make_id(store: str, name: str) -> str:
    """Vygeneruje unikátní ID pro produkt."""
    h = hashlib.md5(f"{store}:{name}".encode()).hexdigest()[:6]
    return f"{store[0]}{h}"


def fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Stáhne stránku a vrátí BeautifulSoup objekt."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        print(f"  [CHYBA] {url}: {e}")
        return None


def parse_price(text: str) -> Optional[float]:
    """Extrahuje cenu z textu jako float."""
    if not text:
        return None
    # Najdi číslo s desetinnou čárkou nebo tečkou
    m = re.search(r"(\d[\d\s]*[.,]?\d*)", text.replace("\xa0", "").replace(" ", ""))
    if m:
        price_str = m.group(1).replace(",", ".")
        try:
            return float(price_str)
        except ValueError:
            return None
    return None


def scrape_links_from_page(url: str) -> List[str]:
    """Stáhne stránku a vrátí seznam unikátních /sleva/ odkazů."""
    soup = fetch_page(url)
    if not soup:
        return []

    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("/sleva/"):
            full_url = f"https://www.kupi.cz{href}"
            if full_url not in links:
                links.append(full_url)
    return links


def scrape_product_offers(url: str, soup: Optional[BeautifulSoup] = None) -> List[dict]:
    """Extrahuje produkty z JSON-LD — vrátí seznam (jeden per obchod)."""
    if soup is None:
        soup = fetch_page(url)
        if not soup:
            return []

    product = None
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get("@type") == "Product":
                product = data
                break
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        product = item
                        break
        except (json.JSONDecodeError, TypeError):
            continue

    if not product:
        return []

    name = product.get("name", "").strip()
    if not name:
        return []

    # ── Společné atributy ──
    # Kategorie
    category = ""
    breadcrumb_links = soup.find_all("a", href=re.compile(r"^/slevy/"))
    if breadcrumb_links:
        for link in reversed(breadcrumb_links):
            text = link.get_text(strip=True)
            if text and text != "Slevy" and len(text) < 40:
                category = text
                break
    if not category:
        category = "Ostatní"

    # Popis (gramáž)
    desc = ""
    page_text = soup.get_text()
    size_match = re.search(r"(\d+(?:[.,]\d+)?\s*(?:g|kg|ml|l|cl|ks|pcs))\b", page_text, re.I)
    if size_match:
        desc = size_match.group(1).strip()
    if not desc:
        raw_desc = product.get("description", "")
        if raw_desc:
            desc = raw_desc.split(".")[0][:60]

    # Obrázek
    image = ""
    img_raw = product.get("image")
    if isinstance(img_raw, list) and img_raw:
        image = img_raw[0] if isinstance(img_raw[0], str) else img_raw[0].get("url", "")
    elif isinstance(img_raw, str):
        image = img_raw
    elif isinstance(img_raw, dict):
        image = img_raw.get("url", "")
    if not image:
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            image = og["content"]

    emoji = get_emoji(name, category)

    # Původní cena z HTML
    price_old_html = None
    for el in soup.find_all(["s", "del", "span"]):
        text = el.get_text(strip=True)
        if "Kč" in text or re.search(r"\d+[.,]\d{2}", text):
            cls = " ".join(el.get("class", []))
            if "original" in cls or "old" in cls or "strike" in cls or el.name in ("s", "del"):
                p = parse_price(text)
                if p and p > 0:
                    price_old_html = p
                    break

    if not price_old_html:
        for el in soup.find_all(string=re.compile(r"běžně\s+stojí", re.I)):
            parent = el.parent
            if parent:
                m = re.search(r"([\d\s,]+)\s*Kč", parent.get_text())
                if m:
                    price_old_html = parse_price(m.group(1))
                    break

    # ── Nabídky per obchod ──
    STORE_MAP = {
        "albert": STORES["albert"], "penny": STORES["penny"], "penny market": STORES["penny"],
        "billa": STORES["billa"], "kaufland": STORES["kaufland"],
    }

    offers_raw = product.get("offers", {})
    offer_list = offers_raw.get("offers", [])

    # Fallback: single offer
    if not offer_list:
        if offers_raw.get("@type") in ("Offer", "AggregateOffer"):
            offer_list = [offers_raw]

    results = []
    seen_stores = set()

    for offer in offer_list:
        price_new = parse_price(str(offer.get("price", offer.get("lowPrice", ""))))
        if not price_new:
            continue

        valid_until = offer.get("priceValidUntil", "")

        # Zjisti obchod
        offered_by = str(offer.get("offeredBy", "")).strip().lower()
        seller = offer.get("seller", {})
        if isinstance(seller, dict):
            offered_by = offered_by or seller.get("name", "").strip().lower()

        store_info = STORE_MAP.get(offered_by)
        if not store_info:
            # Zkus částečnou shodu
            for key, info in STORE_MAP.items():
                if key in offered_by or offered_by in key:
                    store_info = info
                    break

        if not store_info:
            continue

        store_key = store_info["store"]
        if store_key in seen_stores:
            continue
        seen_stores.add(store_key)

        price_old = price_old_html if (price_old_html and price_old_html > price_new) else round(price_new * 1.43, 2)

        results.append({
            "id": make_id(store_key, name),
            "name": name,
            "desc": desc[:80] if desc else "",
            "store": store_key,
            "storeName": store_info["storeName"],
            "category": category,
            "emoji": emoji,
            "image": image,
            "priceNew": price_new,
            "priceOld": price_old,
            "validUntil": valid_until or "",
            "url": url,
        })

    return results


def main():
    print("=" * 60)
    print("🛒 SlevyDnes Scraper — kupi.cz")
    print(f"   {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("=" * 60)

    all_product_urls = set()

    # 1) Sbírání odkazů z letáků a obchodů
    for store_key, urls in LISTING_URLS.items():
        for url in urls:
            print(f"\n📦 Listing: {url}")
            links = scrape_links_from_page(url)
            before = len(all_product_urls)
            all_product_urls.update(links)
            print(f"  +{len(all_product_urls) - before} nových (celkem {len(all_product_urls)})")
            time.sleep(REQUEST_DELAY * 0.5)

    # 2) Sbírání odkazů z kategorií
    print("\n📂 Procházím kategorie...")
    for url in CATEGORY_URLS:
        cat_name = url.split("/")[-1]
        links = scrape_links_from_page(url)
        before = len(all_product_urls)
        all_product_urls.update(links)
        added = len(all_product_urls) - before
        if added > 0:
            print(f"  {cat_name}: +{added} nových")
        time.sleep(REQUEST_DELAY * 0.5)

    print(f"\n🔗 Celkem unikátních odkazů: {len(all_product_urls)}")

    # 3) Stahování detailů produktů
    all_products = []
    seen_names = set()
    skipped = 0

    for i, url in enumerate(sorted(all_product_urls), 1):
        if i % 20 == 0:
            print(f"\n  ... zpracováno {i}/{len(all_product_urls)}")

        time.sleep(REQUEST_DELAY)
        soup = fetch_page(url)
        if not soup:
            continue

        offers = scrape_product_offers(url, soup=soup)
        if not offers:
            skipped += 1
            continue

        for product in offers:
            dedup_key = f"{product['store']}:{product['name']}"
            if dedup_key in seen_names:
                skipped += 1
                continue

            seen_names.add(dedup_key)
            all_products.append(product)
            print(f"  ✅ [{product['storeName']}] {product['name']} — "
                  f"{product['priceNew']} Kč (bylo {product['priceOld']} Kč)")

    # Ulož JSON
    print(f"\n💾 Ukládám {len(all_products)} produktů do {OUTPUT_FILE}")
    OUTPUT_FILE.write_text(
        json.dumps(all_products, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n✅ Hotovo! Soubor: {OUTPUT_FILE}")
    print(f"   Celkem: {len(all_products)} produktů (přeskočeno: {skipped})")
    for store_key, store_info in STORES.items():
        n = sum(1 for p in all_products if p["store"] == store_key)
        print(f"   {store_info['storeName']}: {n}")


if __name__ == "__main__":
    main()
