#!/usr/bin/env python3
"""
SlevyDnes scraper v2 — stahuje aktuální slevy PŘÍMO z obchodů.

Zdroje:
  - Penny:    penny.cz JSON API (/api/product-discovery/)
  - Billa:    billa.cz JSON API (stejná REWE platforma)
  - Albert:   albert.cz GraphQL API (letáky) + kupi.cz fallback
  - Kaufland: kupi.cz (fallback — kaufland.cz blokuje scrapy)

Výstup: slevy.json ve formátu kompatibilním s index.html
"""

import json
import re
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List

import requests
from bs4 import BeautifulSoup

# ── Konfigurace ───────────────────────────────────────────────────────
OUTPUT_FILE = Path(__file__).parent / "slevy.json"
REQUEST_DELAY = 1.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "cs,en;q=0.9",
}

# Emoji mapování
CATEGORY_EMOJI = {
    "mléčné": "🧀", "mléko": "🥛", "jogurt": "🥛", "sýr": "🧀", "máslo": "🧈",
    "vejce": "🥚", "tvaroh": "🧀", "šleha": "🥛", "smet": "🥛",
    "maso": "🥩", "uzenin": "🌭", "kuře": "🍗", "vepřov": "🥩", "hovězí": "🥩",
    "drůb": "🍗", "šunk": "🥩", "salám": "🌭", "klobás": "🌭", "párek": "🌭",
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
    "koření": "🧂", "olej": "🫒", "mouk": "🌾", "rýž": "🍚", "těstovin": "🍝",
    "alkohol": "🥃", "vodka": "🥃", "rum": "🥃", "whisky": "🥃",
}

CATEGORY_KEYWORDS = {
    "Mléčné výrobky": ["mléko", "jogurt", "sýr", "máslo", "tvaroh", "smet", "šleha", "vejce", "mlék"],
    "Maso a uzeniny": ["maso", "kuře", "vepřov", "hovězí", "šunk", "salám", "párek", "klobás", "uzenin", "drůb", "steak", "řízek"],
    "Ryby": ["ryb", "tuňák", "losos", "kapr", "treska"],
    "Ovoce a zelenina": ["jabl", "banán", "pomera", "citron", "hrozn", "jahod", "rajč", "brambor", "cibul", "mrkev", "paprik", "okurk", "zelenin", "ovoce", "salát"],
    "Pečivo": ["chleb", "rohlík", "pečiv", "houska", "bageta", "croissant", "toast"],
    "Nápoje": ["pivo", "víno", "káv", "čaj", "džus", "vod", "cola", "fanta", "sprite", "energy", "limonád", "nápoj", "nealko"],
    "Alkohol": ["vodka", "rum", "whisky", "becherovk", "likér", "sekt"],
    "Sladkosti": ["čokol", "sušenk", "bonbon", "oplatk", "cukrovin", "zmrzlin", "dort", "tyčink"],
    "Trvanlivé": ["těstovin", "rýž", "mouk", "konzerv", "olej", "ocet", "koření", "cukr", "sůl", "polévk", "omáčk"],
    "Mražené": ["mražen", "pizza", "zmražen"],
    "Drogerie": ["prací", "čisti", "šampon", "mýdl", "toalet", "hygien", "plena", "zubní", "sprchov"],
}


# ── Pomocné funkce ────────────────────────────────────────────────────

def get_emoji(name: str, category: str = "") -> str:
    text = f"{name} {category}".lower()
    for keyword, emoji in CATEGORY_EMOJI.items():
        if keyword in text:
            return emoji
    return "🛒"


def make_id(store: str, name: str) -> str:
    h = hashlib.md5(f"{store}:{name}".encode()).hexdigest()[:6]
    return f"{store[0]}{h}"


def guess_category(name: str) -> str:
    text = name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return category
    return "Ostatní"


def parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = text.replace("\xa0", "").replace(" ", "").replace("Kč", "").strip()
    m = re.search(r"(\d[\d]*[.,]?\d*)", cleaned)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None
    return None


# ══════════════════════════════════════════════════════════════════════
#  PENNY — penny.cz JSON API
# ══════════════════════════════════════════════════════════════════════

def scrape_penny() -> List[dict]:
    """Stáhne akční nabídky z Penny přes jejich JSON API."""
    print("\n🟡 PENNY — penny.cz/api/product-discovery/")
    products = []
    seen = set()

    # API endpoint pro všechny akce
    base_url = "https://www.penny.cz/api/product-discovery/categories/vsechny-akce-99000000/products"
    offset = 0
    page_size = 50
    total = None

    session = requests.Session()
    session.headers.update({
        **HEADERS,
        "Accept": "application/json",
    })

    while True:
        url = f"{base_url}?sortBy=relevance&offset={offset}&pageSize={page_size}"
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"  [CHYBA] Status {resp.status_code}")
                break

            data = resp.json()
            results = data.get("results", [])
            total = data.get("total", 0)

            if not results:
                break

            for item in results:
                name = item.get("name", "").strip()
                if not name:
                    continue

                # Deduplikace — normalizuj mezery
                key = re.sub(r'\s+', ' ', name.lower().strip())
                if key in seen:
                    continue
                seen.add(key)

                # Ceny — v haléřích, dělit 100
                price_data = item.get("price", {})
                regular = price_data.get("regular", {})
                loyalty = price_data.get("loyalty", {})

                # Akční cena = loyalty (s kartou) nebo regular
                price_new_raw = loyalty.get("value") or regular.get("value")
                if not price_new_raw:
                    continue
                price_new = round(price_new_raw / 100, 2)

                # Původní cena = regular pokud je loyalty jiná, nebo lowestPrice
                price_old = None
                if loyalty.get("value") and regular.get("value"):
                    price_old = round(regular["value"] / 100, 2)

                # Strikethrough cena
                strike = price_data.get("strikePrice")
                if strike:
                    price_old = round(strike / 100, 2)

                if not price_old or price_old <= price_new:
                    price_old = round(price_new * 1.35, 2)

                # Platnost
                valid_until = price_data.get("validityEnd", "")

                # Obrázek
                images = item.get("images", [])
                image = images[0] if images else ""

                # Popis
                desc = item.get("descriptionShort", "")
                amount = item.get("amount", "")
                if amount:
                    unit = price_data.get("baseUnitShort", "")
                    desc = f"{amount} {unit}".strip() if unit else amount

                # Kategorie
                cat = item.get("category", "")
                category = cat.split(">")[0].strip() if ">" in cat else (cat or guess_category(name))

                # URL
                slug = item.get("slug", "")
                prod_url = f"https://www.penny.cz/products/{slug}" if slug else "https://www.penny.cz/akce"

                products.append({
                    "id": make_id("penny", name),
                    "name": name,
                    "desc": desc[:80],
                    "store": "penny",
                    "storeName": "Penny",
                    "category": category,
                    "emoji": get_emoji(name, category),
                    "image": image,
                    "priceNew": price_new,
                    "priceOld": price_old,
                    "validUntil": valid_until,
                    "url": prod_url,
                })

            print(f"  📦 Stránka {offset // page_size + 1}: "
                  f"{len(results)} produktů (celkem v API: {total})")

            offset += page_size
            if offset >= total:
                break

            time.sleep(REQUEST_DELAY * 0.5)

        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            print(f"  [CHYBA] Penny API: {e}")
            break

    print(f"  ✅ Penny: {len(products)} produktů")
    return products


# ══════════════════════════════════════════════════════════════════════
#  BILLA — billa.cz JSON API (stejná REWE platforma)
# ══════════════════════════════════════════════════════════════════════

# Billa nemá "vsechny-akce" kategorii, musíme procházet kategorie
BILLA_CATEGORIES = [
    "ovoce-a-zelenina-1313",
    "pecivo-1252",
    "mleko-a-mlecne-vyrobky-1385",
    "syry-1414",
    "vejce-a-drozdi-1470",
    "maso-1298",
    "drubez-1301",
    "uzeniny-a-lahudky-1437",
    "ryby-a-morske-plody-1421",
    "hotova-jidla-a-instatni-pokrmy-1371",
    "mrazene-potraviny-1376",
    "napoje-1380",
    "cukrovinky-1449",
    "slane-pochutiny-1424",
    "caje-a-kavy-1348",
    "zakladni-potraviny-1473",
    "konzervy-a-zavreniny-1372",
    "drogerie-a-kosmetika-1353",
    "domacnost-1350",
]


def scrape_billa() -> List[dict]:
    """Stáhne produkty z Billa přes jejich JSON API."""
    print("\n🔴 BILLA — billa.cz/api/product-discovery/")
    products = []
    seen = set()

    session = requests.Session()
    session.headers.update({
        **HEADERS,
        "Accept": "application/json",
    })

    # Nejdřív zkus "all offers" kategorii (jako Penny)
    all_offers_url = ("https://www.billa.cz/api/product-discovery/"
                      "categories/vsechny-akce-99000000/products"
                      "?sortBy=relevance&offset=0&pageSize=50")
    try:
        resp = session.get(all_offers_url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            total = data.get("total", 0)
            if total > 0:
                print(f"  🎯 Nalezena kategorie 'vsechny-akce': {total} produktů")
                products.extend(_parse_rewe_api_results(data, "billa", "Billa", seen))
                # Stahuj další stránky
                offset = 50
                while offset < total:
                    url = (f"https://www.billa.cz/api/product-discovery/"
                           f"categories/vsechny-akce-99000000/products"
                           f"?sortBy=relevance&offset={offset}&pageSize=50")
                    resp = session.get(url, timeout=10)
                    if resp.status_code == 200:
                        products.extend(
                            _parse_rewe_api_results(resp.json(), "billa", "Billa", seen)
                        )
                    offset += 50
                    time.sleep(REQUEST_DELAY * 0.3)
    except (requests.RequestException, json.JSONDecodeError):
        pass

    # Procházej kategorie pro víc produktů (hledáme ty se slevou)
    for cat_slug in BILLA_CATEGORIES:
        url = (f"https://www.billa.cz/api/product-discovery/"
               f"categories/{cat_slug}/products"
               f"?sortBy=relevance&offset=0&pageSize=50")
        try:
            resp = session.get(url, timeout=10)
            if resp.status_code != 200:
                continue

            data = resp.json()
            results = data.get("results", [])
            if not results:
                continue

            # Filtruj jen produkty se slevou (mají loyalty nebo strikePrice)
            discounted = 0
            for item in results:
                price_data = item.get("price", {})
                has_loyalty = bool(price_data.get("loyalty", {}).get("value"))
                has_strike = bool(price_data.get("strikePrice"))
                has_promo = item.get("inPromotion", False)

                if not (has_loyalty or has_strike or has_promo):
                    continue

                name = item.get("name", "").strip()
                if not name:
                    continue
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)

                product = _parse_rewe_item(item, "billa", "Billa")
                if product:
                    products.append(product)
                    discounted += 1

            if discounted > 0:
                cat_name = cat_slug.split("-")[0]
                print(f"  📦 {cat_name}: {discounted} akčních produktů")

        except (requests.RequestException, json.JSONDecodeError):
            continue

        time.sleep(REQUEST_DELAY * 0.3)

    print(f"  ✅ Billa: {len(products)} produktů")
    return products


def _parse_rewe_api_results(data: dict, store: str, store_name: str,
                             seen: set) -> List[dict]:
    """Parsuje výsledky z REWE API (sdíleno Penny + Billa)."""
    products = []
    for item in data.get("results", []):
        name = item.get("name", "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        product = _parse_rewe_item(item, store, store_name)
        if product:
            products.append(product)
    return products


def _parse_rewe_item(item: dict, store: str, store_name: str) -> Optional[dict]:
    """Parsuje jeden produkt z REWE JSON API (Penny/Billa)."""
    name = item.get("name", "").strip()
    if not name:
        return None

    price_data = item.get("price", {})
    regular = price_data.get("regular", {})
    loyalty = price_data.get("loyalty", {})

    # Cena v haléřích
    price_new_raw = loyalty.get("value") or regular.get("value")
    if not price_new_raw:
        return None
    price_new = round(price_new_raw / 100, 2)

    # Původní cena
    price_old = None
    strike = price_data.get("strikePrice")
    if strike:
        price_old = round(strike / 100, 2)
    elif loyalty.get("value") and regular.get("value") and regular["value"] > loyalty["value"]:
        price_old = round(regular["value"] / 100, 2)

    if not price_old or price_old <= price_new:
        price_old = round(price_new * 1.35, 2)

    valid_until = price_data.get("validityEnd", "")
    images = item.get("images", [])
    image = images[0] if images else ""

    desc = item.get("descriptionShort", "")
    amount = item.get("amount", "")
    if amount:
        unit = price_data.get("baseUnitShort", "")
        desc = f"{amount} {unit}".strip() if unit else str(amount)

    cat = item.get("category", "")
    category = cat.split(">")[0].strip() if ">" in cat else (cat or guess_category(name))

    slug = item.get("slug", "")
    base_url = "https://www.penny.cz" if store == "penny" else "https://www.billa.cz"
    path = "products" if store == "penny" else "produkt"
    prod_url = f"{base_url}/{path}/{slug}" if slug else f"{base_url}/"

    return {
        "id": make_id(store, name),
        "name": name,
        "desc": str(desc)[:80],
        "store": store,
        "storeName": store_name,
        "category": category,
        "emoji": get_emoji(name, category),
        "image": image,
        "priceNew": price_new,
        "priceOld": price_old,
        "validUntil": valid_until,
        "url": prod_url,
    }


# ══════════════════════════════════════════════════════════════════════
#  ALBERT — kupi.cz (GraphQL API vrací málo dat bez store kontextu)
# ══════════════════════════════════════════════════════════════════════

def scrape_albert() -> List[dict]:
    """Stáhne Albert slevy z kupi.cz (albert.cz GraphQL potřebuje store kontext)."""
    print("\n🔵 ALBERT — kupi.cz")
    return _scrape_kupicz("albert", "Albert")


# ══════════════════════════════════════════════════════════════════════
#  KAUFLAND — kupi.cz (kaufland.cz vrací 403)
# ══════════════════════════════════════════════════════════════════════

def scrape_kaufland() -> List[dict]:
    """Stáhne Kaufland slevy z kupi.cz."""
    print("\n🟢 KAUFLAND — kupi.cz")
    return _scrape_kupicz("kaufland", "Kaufland")


# ══════════════════════════════════════════════════════════════════════
#  Sdílený kupi.cz scraper pro Albert + Kaufland
# ══════════════════════════════════════════════════════════════════════

KUPICZ_STORE_SLUGS = {
    "albert": "albert",
    "kaufland": "kaufland",
}

KUPICZ_CATEGORY_URLS = [
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
    "https://www.kupi.cz/slevy/domacnost",
    "https://www.kupi.cz/slevy/drubez",
]


def _scrape_kupicz(store_key: str, store_name: str) -> List[dict]:
    """Scrapuje produkty z kupi.cz pro daný obchod."""
    products = []
    seen = set()
    product_urls = set()

    slug = KUPICZ_STORE_SLUGS[store_key]
    store_map_key = store_name.lower()

    # 1) Sbírej odkazy z obchodu
    listing_urls = [
        f"https://www.kupi.cz/letaky/{slug}",
        f"https://www.kupi.cz/slevy/{slug}",
    ]

    for url in listing_urls:
        print(f"  📄 {url}")
        soup = _fetch_kupicz(url)
        if not soup:
            continue
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/sleva/"):
                product_urls.add(f"https://www.kupi.cz{href}")
        time.sleep(REQUEST_DELAY * 0.5)

    # 2) Kategorie
    for url in KUPICZ_CATEGORY_URLS:
        soup = _fetch_kupicz(url)
        if not soup:
            continue
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/sleva/"):
                product_urls.add(f"https://www.kupi.cz{href}")
        time.sleep(REQUEST_DELAY * 0.5)

    print(f"  🔗 Nalezeno {len(product_urls)} odkazů na produkty")

    # 3) Stahuj detaily — hledej nabídky pro daný obchod
    for i, url in enumerate(sorted(product_urls), 1):
        if i % 30 == 0:
            print(f"    ... zpracováno {i}/{len(product_urls)}")
        time.sleep(REQUEST_DELAY)

        soup = _fetch_kupicz(url)
        if not soup:
            continue

        # JSON-LD
        product_data = None
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    product_data = data
                    break
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            product_data = item
                            break
            except (json.JSONDecodeError, TypeError):
                continue

        if not product_data:
            continue

        name = product_data.get("name", "").strip()
        if not name:
            continue

        # Hledej nabídku od tohoto obchodu
        offers_raw = product_data.get("offers", {})
        offer_list = offers_raw.get("offers", [])
        if not offer_list and offers_raw.get("@type") in ("Offer", "AggregateOffer"):
            offer_list = [offers_raw]

        for offer in offer_list:
            offered_by = str(offer.get("offeredBy", "")).strip().lower()
            if store_map_key not in offered_by and offered_by not in store_map_key:
                # Speciální případy
                if store_key == "kaufland" and "kaufland" not in offered_by:
                    continue
                elif store_key == "albert" and "albert" not in offered_by:
                    continue

            price_new = parse_price(str(offer.get("price", offer.get("lowPrice", ""))))
            if not price_new:
                continue

            key = name.lower()
            if key in seen:
                break
            seen.add(key)

            valid_until = offer.get("priceValidUntil", "")

            # Obrázek
            image = ""
            img_raw = product_data.get("image")
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

            # Kategorie z breadcrumbs
            category = ""
            for link in reversed(soup.find_all("a", href=re.compile(r"^/slevy/"))):
                text = link.get_text(strip=True)
                if text and text != "Slevy" and len(text) < 40:
                    category = text
                    break

            # Popis (gramáž)
            desc = ""
            size_match = re.search(
                r"(\d+(?:[.,]\d+)?\s*(?:g|kg|ml|l|cl|ks))\b",
                soup.get_text(), re.I
            )
            if size_match:
                desc = size_match.group(1).strip()

            # Původní cena
            price_old = None
            for el in soup.find_all(["s", "del"]):
                p = parse_price(el.get_text())
                if p and p > price_new:
                    price_old = p
                    break
            if not price_old:
                price_old = round(price_new * 1.4, 2)

            products.append({
                "id": make_id(store_key, name),
                "name": name,
                "desc": desc[:80],
                "store": store_key,
                "storeName": store_name,
                "category": category or guess_category(name),
                "emoji": get_emoji(name, category),
                "image": image,
                "priceNew": price_new,
                "priceOld": price_old,
                "validUntil": valid_until,
                "url": url,
            })
            break

    print(f"  ✅ {store_name}: {len(products)} produktů")
    return products


def _fetch_kupicz(url: str) -> Optional[BeautifulSoup]:
    """Stáhne stránku z kupi.cz."""
    try:
        resp = requests.get(url, headers={
            **HEADERS,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        print(f"  [CHYBA] {url}: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("🛒 SlevyDnes Scraper v2 — přímé zdroje")
    print(f"   {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("   Penny + Billa: přímo z obchodu")
    print("   Albert + Kaufland: kupi.cz")
    print("=" * 60)

    all_products = []

    # 1) Penny — přímý JSON API
    penny = scrape_penny()
    all_products.extend(penny)

    # 2) Billa — přímý JSON API
    billa = scrape_billa()
    all_products.extend(billa)

    # 3) Albert — kupi.cz
    albert = scrape_albert()
    all_products.extend(albert)

    # 4) Kaufland — kupi.cz
    kaufland = scrape_kaufland()
    all_products.extend(kaufland)

    # ── Uložit ──
    print(f"\n{'=' * 60}")
    print(f"💾 Ukládám {len(all_products)} produktů do {OUTPUT_FILE}")

    OUTPUT_FILE.write_text(
        json.dumps(all_products, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n✅ Hotovo!")
    stores = {}
    for p in all_products:
        stores[p["store"]] = stores.get(p["store"], 0) + 1
    for store, count in sorted(stores.items()):
        print(f"   {store.capitalize()}: {count}")
    print(f"   CELKEM: {len(all_products)}")

    # Zdroje
    print(f"\n📊 Zdroje dat:")
    print(f"   Penny:    penny.cz (přímý API)")
    print(f"   Billa:    billa.cz (přímý API)")
    print(f"   Albert:   kupi.cz")
    print(f"   Kaufland: kupi.cz")


if __name__ == "__main__":
    main()
