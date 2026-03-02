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
    "albert": {"url": "https://www.kupi.cz/letaky/albert", "storeName": "Albert", "store": "albert"},
    "penny":  {"url": "https://www.kupi.cz/letaky/penny-market", "storeName": "Penny", "store": "penny"},
    "billa":  {"url": "https://www.kupi.cz/letaky/billa", "storeName": "Billa", "store": "billa"},
    "kaufland": {"url": "https://www.kupi.cz/letaky/kaufland", "storeName": "Kaufland", "store": "kaufland"},
}

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


def scrape_listing(store_key: str, store_info: dict) -> List[str]:
    """Stáhne listing stránku obchodu a vrátí seznam URL na detaily produktů."""
    print(f"\n📦 Stahuji listing: {store_info['storeName']} ...")
    soup = fetch_page(store_info["url"])
    if not soup:
        return []

    product_links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("/sleva/"):
            full_url = f"https://www.kupi.cz{href}"
            if full_url not in product_links:
                product_links.append(full_url)

    print(f"  Nalezeno {len(product_links)} odkazů na produkty")
    return product_links


def scrape_product_detail(url: str, store_info: dict) -> Optional[dict]:
    """Stáhne detail produktu a extrahuje data z JSON-LD a HTML."""
    soup = fetch_page(url)
    if not soup:
        return None

    product = None

    # 1) Zkus JSON-LD
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
        return None

    name = product.get("name", "").strip()
    if not name:
        return None

    # Ceny z offers
    offers = product.get("offers", {})
    price_new = None
    valid_until = None

    if offers.get("@type") == "AggregateOffer":
        price_new = parse_price(str(offers.get("lowPrice", "")))
        valid_until = offers.get("priceValidUntil")
    elif offers.get("@type") == "Offer":
        price_new = parse_price(str(offers.get("price", "")))
        valid_until = offers.get("priceValidUntil")

    if not price_new:
        return None

    # 2) Původní cena — hledej v HTML
    price_old = None
    # Hledej přeškrtnutou cenu nebo text "Běžná cena"
    for el in soup.find_all(["s", "del", "span"]):
        text = el.get_text(strip=True)
        if "Kč" in text or re.search(r"\d+[.,]\d{2}", text):
            cls = " ".join(el.get("class", []))
            if "original" in cls or "old" in cls or "strike" in cls or el.name in ("s", "del"):
                p = parse_price(text)
                if p and p > price_new:
                    price_old = p
                    break

    # Záložní: hledej "Běžná cena" text
    if not price_old:
        for el in soup.find_all(string=re.compile(r"[Bb]ěžná\s+cena|[Pp]ůvodní\s+cena|[Pp]řed\s+slevou")):
            parent = el.parent
            if parent:
                p = parse_price(parent.get_text())
                if p and p > price_new:
                    price_old = p
                    break

    # Pokud nemáme původní cenu, zkusíme najít procento slevy
    if not price_old:
        discount_match = soup.find(string=re.compile(r"-?\s*\d+\s*%"))
        if discount_match:
            pct_match = re.search(r"(\d+)\s*%", discount_match)
            if pct_match:
                pct = int(pct_match.group(1))
                if 5 <= pct <= 90:
                    price_old = round(price_new / (1 - pct / 100), 2)

    # Pokud stále nemáme, zkus "běžně stojí X Kč" v textu stránky
    if not price_old:
        page_text = soup.get_text()
        m = re.search(r"běžně\s+stojí\s+([\d\s,]+)\s*Kč", page_text, re.I)
        if m:
            p = parse_price(m.group(1))
            if p and p > price_new:
                price_old = p

    # Pokud stále nemáme, odhadni 30% slevu jako fallback
    if not price_old:
        price_old = round(price_new * 1.43, 2)

    # Kategorie — breadcrumb na kupi.cz: Slevy > Kategorie > Podkategorie
    category = ""
    # Hledej breadcrumb odkazy (href začíná /slevy/)
    breadcrumb_links = soup.find_all("a", href=re.compile(r"^/slevy/"))
    if breadcrumb_links:
        # Vezmi poslední kategorii (nejkonkrétnější)
        for link in reversed(breadcrumb_links):
            text = link.get_text(strip=True)
            if text and text != "Slevy" and len(text) < 40:
                category = text
                break

    # Záložní: hledej text "v kategorii X"
    if not category:
        page_text = soup.get_text()
        m = re.search(r"v\s+kategorii\s+\[?([^\].\n]+)", page_text, re.I)
        if m:
            category = m.group(1).strip()

    if not category:
        category = "Ostatní"

    # Platnost — hledej "platí do" text pro konkrétní obchod
    if not valid_until:
        page_text = soup.get_text()
        # Hledej datum ve formátu "do DD. MM." nebo "platí do DATUM"
        m = re.search(
            r"platí\s+do\s+\w+\s+(\d{1,2})\.\s*(\d{1,2})\.",
            page_text, re.I
        )
        if m:
            day, month = int(m.group(1)), int(m.group(2))
            year = datetime.now().year
            try:
                valid_until = f"{year}-{month:02d}-{day:02d}"
            except ValueError:
                pass

    # Popis — zkus gramáž/objem z textu
    desc = ""
    page_text = soup.get_text()
    # Hledej gramáž: "120 g", "500 ml", "1 l", "1 kg" atd.
    size_match = re.search(
        r"(\d+(?:[.,]\d+)?\s*(?:g|kg|ml|l|cl|ks|pcs))\b",
        page_text, re.I
    )
    if size_match:
        desc = size_match.group(1).strip()

    # Pokud nic, vezmi desc z JSON-LD ale zkrať
    if not desc:
        raw_desc = product.get("description", "")
        if raw_desc:
            # Vezmi jen první větu nebo max 60 znaků
            first_sentence = raw_desc.split(".")[0]
            desc = first_sentence[:60]

    emoji = get_emoji(name, category)

    # Obrázek produktu z JSON-LD
    image = ""
    img_raw = product.get("image")
    if isinstance(img_raw, list) and img_raw:
        image = img_raw[0] if isinstance(img_raw[0], str) else img_raw[0].get("url", "")
    elif isinstance(img_raw, str):
        image = img_raw
    elif isinstance(img_raw, dict):
        image = img_raw.get("url", "")

    # Záložní: hledej og:image meta tag
    if not image:
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            image = og["content"]

    return {
        "id": make_id(store_info["store"], name),
        "name": name,
        "desc": desc[:80] if desc else "",
        "store": store_info["store"],
        "storeName": store_info["storeName"],
        "category": category,
        "emoji": emoji,
        "image": image,
        "priceNew": price_new,
        "priceOld": price_old,
        "validUntil": valid_until or "",
        "url": url,
    }


def main():
    print("=" * 60)
    print("🛒 SlevyDnes Scraper — kupi.cz")
    print(f"   {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("=" * 60)

    all_products = []
    seen_names = set()

    for store_key, store_info in STORES.items():
        product_urls = scrape_listing(store_key, store_info)
        time.sleep(REQUEST_DELAY)

        # Omez na max 15 produktů per obchod
        max_per_store = 15
        count = 0

        for url in product_urls:
            if count >= max_per_store:
                break

            time.sleep(REQUEST_DELAY)
            product = scrape_product_detail(url, store_info)

            if product and product["name"] not in seen_names:
                seen_names.add(product["name"])
                all_products.append(product)
                count += 1
                print(f"  ✅ {product['name']} — {product['priceNew']} Kč"
                      f" (bylo {product['priceOld']} Kč)")
            elif product:
                print(f"  ⏭️  Duplicita: {product['name']}")
            else:
                print(f"  ❌ Nepodařilo se zpracovat: {url.split('/')[-1]}")

        print(f"  → {store_info['storeName']}: {count} produktů")

    # Ulož JSON
    print(f"\n💾 Ukládám {len(all_products)} produktů do {OUTPUT_FILE}")
    OUTPUT_FILE.write_text(
        json.dumps(all_products, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✅ Hotovo! Soubor: {OUTPUT_FILE}")
    print(f"   Celkem: {len(all_products)} produktů")
    for store_key, store_info in STORES.items():
        n = sum(1 for p in all_products if p["store"] == store_key)
        print(f"   {store_info['storeName']}: {n}")


if __name__ == "__main__":
    main()
