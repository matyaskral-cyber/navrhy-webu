#!/usr/bin/env python3
"""
M+P Král — Sync skladu z Pohody do Supabase
=============================================

Tento skript čte skladové zásoby z Pohody a nahrává je do Supabase,
odkud je čte webová aplikace pro odběratele.

SETUP:
1. Nainstaluj Python 3.8+
2. pip install requests pyodbc
3. Uprav CONFIG sekci níže (SQL Server připojení)
4. Spusť: python sync_pohoda.py
5. Pro automatický sync: Plánovač úloh (Task Scheduler) každých 15 min

ALTERNATIVNÍ METODY ČTENÍ Z POHODY:
A) SQL Server (doporučeno pro Pohoda Komplet) — ODBC připojení
B) mServer XML API — TCP socket komunikace
C) XML export — Pohoda exportuje XML, skript ho načte

Tento skript podporuje všechny 3 metody. Zvol v CONFIG.
"""

import json
import sys
import os
import time
import hashlib
from datetime import datetime

try:
    import requests
except ImportError:
    print("CHYBA: Nainstaluj requests: pip install requests")
    sys.exit(1)

# ============================================
# CONFIG — UPRAV PODLE SVÉ POHODY
# ============================================

# Supabase (kam se nahrávají data)
SUPABASE_URL = "https://mpydvkooqlgeyjlmylkv.supabase.co"
SUPABASE_KEY = "sb_publishable_vznr30ToMNhAS84CKLIllw_7GBjzP8J"

# Metoda čtení z Pohody: "sql", "mserver", nebo "xml"
METODA = "sql"

# --- SQL Server připojení (pro METODA = "sql") ---
SQL_SERVER = "localhost\\SQLPOHODA"  # Název SQL Server instance
SQL_DATABASE = "StwPh_12345678_2026"  # Název databáze (StwPh_ICO_ROK)
SQL_USER = ""  # Prázdné = Windows auth
SQL_PASSWORD = ""

# --- mServer (pro METODA = "mserver") ---
MSERVER_HOST = "localhost"
MSERVER_PORT = 6661
MSERVER_ICO = "12345678"  # IČO firmy v Pohodě

# --- XML export (pro METODA = "xml") ---
XML_EXPORT_PATH = r"C:\Pohoda-Export\sklad.xml"

# ============================================


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


# ==========================================
# METODA A: SQL Server (Pohoda Komplet)
# ==========================================
def read_stock_sql():
    """Čte zásoby přímo z SQL Server databáze Pohody."""
    try:
        import pyodbc
    except ImportError:
        print("CHYBA: Nainstaluj pyodbc: pip install pyodbc")
        sys.exit(1)

    if SQL_USER:
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};UID={SQL_USER};PWD={SQL_PASSWORD}"
    else:
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};Trusted_Connection=yes"

    log(f"Připojuji se k SQL Server: {SQL_SERVER}/{SQL_DATABASE}")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Pohoda SQL tabulky:
    # sZasoba — hlavní tabulka zásob
    # sZasobaSkl — skladové pohyby
    # sSklad — sklady
    # sSkupZas — skupiny zásob (kategorie)
    query = """
    SELECT
        z.Kod AS kod,
        z.Nazev AS nazev,
        z.MJ AS jednotka,
        ISNULL(z.StkMnozstvi, 0) AS mnozstvi,
        ISNULL(z.NakupCena, 0) AS cena_nakup,
        ISNULL(z.ProdejCena, 0) AS cena,
        sk.Nazev AS kategorie,
        z.Poznamka AS poznamka
    FROM sZasoba z
    LEFT JOIN sSkupZas sk ON z.RefSkupZas = sk.ID
    WHERE z.StkMnozstvi IS NOT NULL
    ORDER BY z.Nazev
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()

    items = []
    for row in rows:
        item = dict(zip(columns, row))
        # Ošetři datové typy
        item['mnozstvi'] = float(item.get('mnozstvi', 0) or 0)
        item['cena'] = float(item.get('cena', 0) or 0)
        item['cena_nakup'] = float(item.get('cena_nakup', 0) or 0)
        item['kod'] = str(item.get('kod', '')).strip()
        item['nazev'] = str(item.get('nazev', '')).strip()
        item['jednotka'] = str(item.get('jednotka', 'ks')).strip() or 'ks'
        item['kategorie'] = str(item.get('kategorie', '')).strip()
        item['poznamka'] = str(item.get('poznamka', '')).strip()
        items.append(item)

    log(f"Načteno {len(items)} položek z SQL")
    return items


# ==========================================
# METODA B: mServer XML API
# ==========================================
def read_stock_mserver():
    """Čte zásoby přes Pohoda mServer XML API."""
    import socket

    request_xml = f"""<?xml version="1.0" encoding="Windows-1250"?>
<dat:dataPack version="2.0" id="SkladExport" ico="{MSERVER_ICO}" application="KSH-Sklad" note="Export skladu"
    xmlns:dat="http://www.stormware.cz/schema/version_2/data.xsd"
    xmlns:lst="http://www.stormware.cz/schema/version_2/list.xsd"
    xmlns:ftr="http://www.stormware.cz/schema/version_2/filter.xsd"
    xmlns:stk="http://www.stormware.cz/schema/version_2/stock.xsd"
    xmlns:typ="http://www.stormware.cz/schema/version_2/type.xsd">
  <dat:dataPackItem id="li1" version="2.0">
    <lst:listStockRequest version="2.0" stockVersion="2.0">
      <lst:requestStock>
      </lst:requestStock>
    </lst:listStockRequest>
  </dat:dataPackItem>
</dat:dataPack>"""

    log(f"Připojuji se na mServer: {MSERVER_HOST}:{MSERVER_PORT}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30)
    sock.connect((MSERVER_HOST, MSERVER_PORT))

    data = request_xml.encode('windows-1250')
    # mServer protocol: 10 bytes header (length)
    header = f"{len(data):010d}".encode('ascii')
    sock.sendall(header + data)

    # Read response
    resp_header = sock.recv(10)
    resp_len = int(resp_header.decode('ascii'))
    resp_data = b''
    while len(resp_data) < resp_len:
        chunk = sock.recv(min(4096, resp_len - len(resp_data)))
        if not chunk:
            break
        resp_data += chunk
    sock.close()

    resp_xml = resp_data.decode('windows-1250')

    # Parse XML response
    import xml.etree.ElementTree as ET
    items = []

    # Remove namespaces for easier parsing
    resp_clean = resp_xml
    for ns_prefix in ['dat:', 'lst:', 'stk:', 'typ:', 'ftr:']:
        resp_clean = resp_clean.replace(ns_prefix, '')

    root = ET.fromstring(resp_clean)
    for stock in root.iter('stock'):
        header = stock.find('.//stockHeader')
        if header is None:
            continue

        item = {
            'kod': (header.findtext('code') or '').strip(),
            'nazev': (header.findtext('name') or '').strip(),
            'jednotka': (header.findtext('unit') or 'ks').strip(),
            'mnozstvi': float(header.findtext('count') or 0),
            'cena': float(header.findtext('.//sellingPrice/price') or header.findtext('.//purchasingPrice/price') or 0),
            'kategorie': (header.findtext('.//storage/ids') or '').strip(),
        }
        items.append(item)

    log(f"Načteno {len(items)} položek z mServeru")
    return items


# ==========================================
# METODA C: XML export soubor
# ==========================================
def read_stock_xml():
    """Čte zásoby z XML exportu Pohody."""
    import xml.etree.ElementTree as ET

    if not os.path.exists(XML_EXPORT_PATH):
        log(f"CHYBA: Soubor nenalezen: {XML_EXPORT_PATH}")
        log("Exportuj sklad z Pohody: Soubor → Datová komunikace → XML export → Zásoby")
        return []

    log(f"Čtu XML export: {XML_EXPORT_PATH}")
    tree = ET.parse(XML_EXPORT_PATH)
    root = tree.getroot()

    # Remove namespaces
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]

    items = []
    for stock in root.iter('stock'):
        header = stock.find('.//stockHeader')
        if header is None:
            continue

        item = {
            'kod': (header.findtext('code') or '').strip(),
            'nazev': (header.findtext('name') or '').strip(),
            'jednotka': (header.findtext('unit') or 'ks').strip(),
            'mnozstvi': float(header.findtext('count') or 0),
            'cena': float(header.findtext('.//sellingPrice') or header.findtext('.//purchasingPrice') or 0),
            'kategorie': (header.findtext('.//storage/ids') or '').strip(),
        }
        items.append(item)

    log(f"Načteno {len(items)} položek z XML")
    return items


# ==========================================
# UPLOAD DO SUPABASE
# ==========================================
def upload_to_supabase(items):
    """Nahraje položky do Supabase tabulky 'sklad'."""
    log(f"Nahrávám {len(items)} položek do Supabase...")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    now = datetime.utcnow().isoformat() + "Z"

    # Prepare data — upsert by 'kod'
    payload = []
    for item in items:
        payload.append({
            "kod": item['kod'],
            "nazev": item['nazev'],
            "mnozstvi": item['mnozstvi'],
            "jednotka": item['jednotka'],
            "cena": item.get('cena', 0),
            "kategorie": item.get('kategorie', ''),
            "poznamka": item.get('poznamka', ''),
            "updated_at": now,
        })

    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(payload), batch_size):
        batch = payload[i:i+batch_size]
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/sklad",
            headers=headers,
            json=batch,
        )

        if resp.status_code in (200, 201):
            log(f"  Batch {i//batch_size + 1}: {len(batch)} položek OK")
        else:
            log(f"  CHYBA batch {i//batch_size + 1}: {resp.status_code} - {resp.text}")
            return False

    # Smaž položky co už v Pohodě nejsou
    current_kody = {item['kod'] for item in items}
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/sklad?select=kod",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    )
    if resp.status_code == 200:
        db_items = resp.json()
        to_delete = [item['kod'] for item in db_items if item['kod'] not in current_kody]
        if to_delete:
            for kod in to_delete:
                requests.delete(
                    f"{SUPABASE_URL}/rest/v1/sklad?kod=eq.{kod}",
                    headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
                )
            log(f"  Smazáno {len(to_delete)} zastaralých položek")

    log("Upload dokončen!")
    return True


# ==========================================
# MAIN
# ==========================================
def main():
    print("=" * 50)
    log("M+P Král — Sync skladu Pohoda → Supabase")
    print("=" * 50)
    log(f"Metoda: {METODA}")

    # 1. Načti data z Pohody
    if METODA == "sql":
        items = read_stock_sql()
    elif METODA == "mserver":
        items = read_stock_mserver()
    elif METODA == "xml":
        items = read_stock_xml()
    else:
        log(f"Neznámá metoda: {METODA}")
        sys.exit(1)

    if not items:
        log("Žádné položky k nahrání!")
        return

    # 2. Nahraj do Supabase
    upload_to_supabase(items)

    print("=" * 50)
    log("Hotovo!")


def add_test_data():
    """Nahraje testovací data pro ověření funkčnosti."""
    log("Nahrávám testovací data...")

    test_items = [
        {"kod": "PP-001", "nazev": "Pracovní kalhoty KLASIK modré", "mnozstvi": 45, "jednotka": "ks", "cena": 890, "kategorie": "Pracovní oděvy"},
        {"kod": "PP-002", "nazev": "Pracovní kalhoty KLASIK černé", "mnozstvi": 32, "jednotka": "ks", "cena": 890, "kategorie": "Pracovní oděvy"},
        {"kod": "PP-003", "nazev": "Pracovní blůza KLASIK modrá", "mnozstvi": 28, "jednotka": "ks", "cena": 750, "kategorie": "Pracovní oděvy"},
        {"kod": "PP-010", "nazev": "Montérky lacl PROFI modré", "mnozstvi": 15, "jednotka": "ks", "cena": 1290, "kategorie": "Pracovní oděvy"},
        {"kod": "PP-011", "nazev": "Montérky lacl PROFI černé", "mnozstvi": 8, "jednotka": "ks", "cena": 1290, "kategorie": "Pracovní oděvy"},
        {"kod": "PP-020", "nazev": "Reflexní vesta žlutá EN ISO 20471", "mnozstvi": 120, "jednotka": "ks", "cena": 89, "kategorie": "Reflexní oděvy"},
        {"kod": "PP-021", "nazev": "Reflexní vesta oranžová EN ISO 20471", "mnozstvi": 85, "jednotka": "ks", "cena": 89, "kategorie": "Reflexní oděvy"},
        {"kod": "PP-030", "nazev": "Reflexní bunda FLASH zimní", "mnozstvi": 5, "jednotka": "ks", "cena": 2490, "kategorie": "Reflexní oděvy"},
        {"kod": "PP-031", "nazev": "Reflexní kalhoty FLASH", "mnozstvi": 3, "jednotka": "ks", "cena": 1890, "kategorie": "Reflexní oděvy"},
        {"kod": "RK-001", "nazev": "Rukavice LATEX vel. M", "mnozstvi": 200, "jednotka": "pár", "cena": 45, "kategorie": "Rukavice"},
        {"kod": "RK-002", "nazev": "Rukavice LATEX vel. L", "mnozstvi": 150, "jednotka": "pár", "cena": 45, "kategorie": "Rukavice"},
        {"kod": "RK-003", "nazev": "Rukavice NITRIL vel. L", "mnozstvi": 0, "jednotka": "pár", "cena": 55, "kategorie": "Rukavice"},
        {"kod": "RK-010", "nazev": "Rukavice kožené DRIVER", "mnozstvi": 25, "jednotka": "pár", "cena": 189, "kategorie": "Rukavice"},
        {"kod": "OB-001", "nazev": "Pracovní obuv FIRWIN S3 černá", "mnozstvi": 18, "jednotka": "pár", "cena": 1690, "kategorie": "Pracovní obuv"},
        {"kod": "OB-002", "nazev": "Pracovní obuv FIRWIN S3 hnědá", "mnozstvi": 12, "jednotka": "pár", "cena": 1690, "kategorie": "Pracovní obuv"},
        {"kod": "OB-010", "nazev": "Holínky PVC zelené", "mnozstvi": 0, "jednotka": "pár", "cena": 490, "kategorie": "Pracovní obuv"},
        {"kod": "OB-011", "nazev": "Holínky PVC bílé (potravinářské)", "mnozstvi": 6, "jednotka": "pár", "cena": 590, "kategorie": "Pracovní obuv"},
        {"kod": "HL-001", "nazev": "Přilba VERTEX žlutá", "mnozstvi": 30, "jednotka": "ks", "cena": 350, "kategorie": "Ochrana hlavy"},
        {"kod": "HL-002", "nazev": "Přilba VERTEX bílá", "mnozstvi": 22, "jednotka": "ks", "cena": 350, "kategorie": "Ochrana hlavy"},
        {"kod": "HL-010", "nazev": "Čepice zimní pletená reflexní", "mnozstvi": 50, "jednotka": "ks", "cena": 129, "kategorie": "Ochrana hlavy"},
        {"kod": "OC-001", "nazev": "Brýle ochranné VISITOR čiré", "mnozstvi": 80, "jednotka": "ks", "cena": 69, "kategorie": "Ochrana očí"},
        {"kod": "OC-002", "nazev": "Brýle ochranné VISITOR tmavé", "mnozstvi": 0, "jednotka": "ks", "cena": 79, "kategorie": "Ochrana očí"},
        {"kod": "RE-001", "nazev": "Respirátor FFP2 (balení 10ks)", "mnozstvi": 40, "jednotka": "bal", "cena": 199, "kategorie": "Ochrana dýchání"},
        {"kod": "RE-002", "nazev": "Respirátor FFP3 s ventilem", "mnozstvi": 2, "jednotka": "ks", "cena": 89, "kategorie": "Ochrana dýchání"},
        {"kod": "PL-001", "nazev": "Plášť VISITOR bílý jednorázový", "mnozstvi": 500, "jednotka": "ks", "cena": 25, "kategorie": "Jednorázové oděvy"},
        {"kod": "PL-002", "nazev": "Návleky na boty jednorázové (100ks)", "mnozstvi": 10, "jednotka": "bal", "cena": 149, "kategorie": "Jednorázové oděvy"},
        {"kod": "ZD-001", "nazev": "Zdravotnický plášť bílý vel. M", "mnozstvi": 20, "jednotka": "ks", "cena": 690, "kategorie": "Zdravotnické oděvy"},
        {"kod": "ZD-002", "nazev": "Zdravotnický plášť bílý vel. L", "mnozstvi": 15, "jednotka": "ks", "cena": 690, "kategorie": "Zdravotnické oděvy"},
        {"kod": "ZD-003", "nazev": "Kalhoty zdravotnické bílé vel. L", "mnozstvi": 10, "jednotka": "ks", "cena": 490, "kategorie": "Zdravotnické oděvy"},
        {"kod": "DT-001", "nazev": "Dětský plášť bílý (laboratorní)", "mnozstvi": 0, "jednotka": "ks", "cena": 390, "kategorie": "Dětské oděvy"},
    ]

    upload_to_supabase(test_items)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        add_test_data()
    else:
        main()
