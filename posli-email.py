#!/usr/bin/env python3
"""
KSH Partners — odesílání emailů
Spuštění: python3 posli-email.py komu@email.cz "Předmět" "Text emailu"
Nebo:     python3 posli-email.py   (interaktivní režim)
"""

import os
import smtplib
import ssl
import subprocess
import sys
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

# ============================================
SMTP_SERVER = "smtp.seznam.cz"
SMTP_PORT = 465
EMAIL = "info@ksh-partners.cz"
JMENO = "Matyáš Král"
# ============================================



def heslo():
    """Heslo pro aplikace k info@ (Seznam): proměnná KSH_INFO_HESLO, jinak Klíčenka:
    security add-generic-password -s ksh-info-smtp -a info@ksh-partners.cz -w"""
    h = os.environ.get("KSH_INFO_HESLO")
    if not h:
        r = subprocess.run(["security", "find-generic-password", "-s", "ksh-info-smtp", "-a", EMAIL, "-w"],
                           capture_output=True, text=True)
        h = r.stdout.strip()
    if not h:
        sys.exit("Chybí heslo: nastav KSH_INFO_HESLO, nebo ho ulož do Klíčenky (viz heslo() v tomto souboru).")
    return h


PODPIS = """
--
Matyáš Král
KSH Partners s.r.o.
Tel: 774 982 675
Email: info@ksh-partners.cz"""


def posli(komu, predmet, text, s_podpisem=True):
    if s_podpisem:
        text = text + PODPIS

    msg = MIMEText(text, "plain", "utf-8")
    msg["Subject"] = Header(predmet, "utf-8")
    msg["From"] = formataddr((str(Header(JMENO, "utf-8")), EMAIL))
    msg["To"] = komu

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(EMAIL, heslo())
            server.sendmail(EMAIL, komu, msg.as_string())
        print(f"Odesláno → {komu}")
    except Exception as e:
        print(f"Chyba: {e}")


def main():
    # Režim s argumenty: python3 posli-email.py komu@email.cz "Předmět" "Text"
    if len(sys.argv) == 4:
        posli(sys.argv[1], sys.argv[2], sys.argv[3])
        return

    # Interaktivní režim
    print("KSH Partners — Odeslat email")
    print("=" * 40)

    komu = input("Komu (email): ").strip()
    if not komu:
        print("Zadej email.")
        return

    predmet = input("Předmět: ").strip()
    if not predmet:
        print("Zadej předmět.")
        return

    print("Text (prázdný řádek = konec):")
    radky = []
    while True:
        r = input()
        if r == "":
            break
        radky.append(r)

    text = "\n".join(radky)

    if not text:
        print("Prázdný text, nic neodesláno.")
        return

    print(f"\n--- Náhled ---")
    print(f"Komu: {komu}")
    print(f"Předmět: {predmet}")
    print(f"Text:\n{text}{PODPIS}")
    print(f"--- Konec ---\n")

    potvrdit = input("Odeslat? (ano/ne): ").strip().lower()
    if potvrdit == "ano":
        posli(komu, predmet, text)
    else:
        print("Zrušeno.")


if __name__ == "__main__":
    main()
