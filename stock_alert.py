"""
iPhone Duo Stock Alert (Apple Store Hong Kong, in-store pickup) -> WhatsApp / Telegram

Watches EVERY iPhone Duo variant (all colours and storage sizes) at the HK
Apple Stores. When any variant becomes available for pickup, you get a
Telegram message with the model, the stores and a buy link.

Run:  python3 stock_alert.py          (loop, for a server)
      python3 stock_alert.py --once   (single pass, used by GitHub Actions)
Settings come from environment variables - see README.md.

The part numbers are read automatically from Apple's HK iPhone Duo page when
the bot starts, so you don't need to look them up. If that ever fails, paste
part numbers (e.g. "MXXXXZA/A") into MANUAL_PARTS.

Note: this uses Apple's public pickup-availability endpoint (the one the Apple
website itself calls). It isn't an official API and Apple may change it.
"""

import random
import re
import time
from datetime import datetime

import requests

# ============================ CONFIG ============================

import json
import os
import sys

# Secrets are read from environment variables (GitHub Actions secrets), never stored in the file.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
# WhatsApp via CallMeBot (free, personal use): phone incl. country code, e.g. +85212345678
WHATSAPP_PHONE = os.environ.get("WHATSAPP_PHONE", "")
WHATSAPP_APIKEY = os.environ.get("WHATSAPP_APIKEY", "")
STATE_FILE = os.environ.get("STATE_FILE", "state.json")

# Only alert for these stores (leave empty = any HK store)
STORE_FILTER = []         # e.g. ["ifc mall", "Causeway Bay", "Canton Road"]

# Fallback if automatic part-number lookup fails
MANUAL_PARTS = []         # e.g. ["MXXXXZA/A", "MYYYYZA/A"]

CHECK_EVERY_SECONDS = 60  # one full round of all variants, then wait this long

# ================================================================

BUY_PAGES = [
    "https://www.apple.com/hk/shop/buy-iphone/iphone-duo",
    "https://www.apple.com/hk/en/shop/buy-iphone/iphone-duo",
    "https://www.apple.com/hk/shop/buy-iphone/iphone-duo/7.6-inch-display-1tb-night-sky",
]
STOCK_URLS = [
    "https://www.apple.com/hk/shop/fulfillment-messages",
    "https://www.apple.com/hk/en/shop/fulfillment-messages",
]
STOCK_URL = STOCK_URLS[0]   # switched automatically if this one fails
ANCHOR_STORE = "R428"     # ifc mall; nearby HK stores are included automatically
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
    "Accept-Language": "en-HK,en;q=0.9",
}

alerted = set()           # (store, part) already notified, to avoid spam


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def whatsapp(text):
    if not WHATSAPP_PHONE or not WHATSAPP_APIKEY:
        return False
    try:
        r = requests.get("https://api.callmebot.com/whatsapp.php",
                         params={"phone": WHATSAPP_PHONE, "text": text, "apikey": WHATSAPP_APIKEY},
                         timeout=20)
        if r.status_code != 200:
            log(f"WhatsApp error: HTTP {r.status_code} {r.text[:120]}")
            return False
        return True
    except requests.RequestException as e:
        log(f"WhatsApp error: {e}")
        return False


def notify(text):
    """Send to every configured channel (WhatsApp and/or Telegram)."""
    sent = whatsapp(text)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        telegram(text)
        sent = True
    if not sent:
        log("No notification channel worked - set WHATSAPP_PHONE + WHATSAPP_APIKEY (or Telegram)")


def telegram(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text,
                  "disable_web_page_preview": True},
            timeout=10,
        )
    except requests.RequestException as e:
        log(f"Telegram error: {e}")


def find_parts():
    """Read every iPhone Duo HK part number from Apple's buy page."""
    if MANUAL_PARTS:
        return list(MANUAL_PARTS)
    found = set()
    for url in BUY_PAGES:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
        except requests.RequestException as e:
            log(f"{url}: {e}")
            continue
        if r.status_code != 200:
            log(f"{url}: HTTP {r.status_code}")
            continue
        # the page writes the slash as "/", "/" or "%2F"
        for base, _ in re.findall(r"\b(M[A-Z0-9]{4}ZA)(/|\\u002F|%2F)A\b", r.text):
            found.add(f"{base}/A")
        if found:
            log(f"Part numbers read from {url}")
            break
    return sorted(found)


def check(part):
    """Return (product title, [stores with pickup available])."""
    params = {"pl": "true", "mts.0": "regular", "parts.0": part,
              "store": ANCHOR_STORE, "searchNearby": "true"}
    global STOCK_URL
    r = requests.get(STOCK_URL, params=params,
                     headers={**HEADERS, "Accept": "application/json"}, timeout=15)
    if r.status_code == 404:
        for alt in STOCK_URLS:
            if alt != STOCK_URL:
                r = requests.get(alt, params=params,
                                 headers={**HEADERS, "Accept": "application/json"}, timeout=15)
                if r.ok:
                    STOCK_URL = alt
                    break
    if r.status_code == 541:
        # Apple answers 541 while store pickup isn't open yet for this model
        return part, None
    r.raise_for_status()
    stores = r.json()["body"]["content"]["pickupMessage"]["stores"]

    title, hits = part, []
    for s in stores:
        info = s.get("partsAvailability", {}).get(part, {})
        title = (info.get("messageTypes", {}).get("regular", {})
                 .get("storePickupProductTitle") or title)
        name = s.get("storeName", "?")
        if STORE_FILTER and not any(f.lower() in name.lower() for f in STORE_FILTER):
            continue
        if info.get("pickupDisplay") == "available":
            hits.append(name)
    return title, hits


def load_state():
    try:
        with open(STATE_FILE) as f:
            d = json.load(f)
        return {"alerted": {tuple(x) for x in d.get("alerted", [])},
                "pickup_open": set(d.get("pickup_open", [])),
                "started": bool(d.get("started")), "noparts_told": bool(d.get("noparts_told"))}
    except (OSError, ValueError):
        return {"alerted": set(), "pickup_open": set(), "started": False}


def save_state(st):
    with open(STATE_FILE, "w") as f:
        json.dump({"alerted": sorted(st["alerted"]), "pickup_open": sorted(st["pickup_open"]),
                   "started": st["started"], "noparts_told": st.get("noparts_told", False)}, f)


def one_round(parts, st):
    """Check every variant once. Returns True if pickup is open for at least one."""
    alerted, pickup_open = st["alerted"], st["pickup_open"]
    not_open = 0
    for part in parts:
        try:
            title, hits = check(part)
        except Exception as e:
            log(f"{part}: check failed ({e})")
            time.sleep(3)
            continue
        if hits is None:
            not_open += 1
            time.sleep(random.uniform(1, 2))
            continue
        if part not in pickup_open:
            pickup_open.add(part)
            if len(pickup_open) == 1:
                notify("📣 Apple 已開放 iPhone Duo 店舖取貨查詢，bot 而家開始睇庫存")
        if not hits:
            for key in [k for k in alerted if k[1] == part]:
                alerted.discard(key)       # stock gone: allow a fresh alert if it returns
        else:
            new = [h for h in hits if (h, part) not in alerted]
            if new:
                link = f"https://www.apple.com/hk/en/shop/product/{part.replace('/', '%2F')}"
                msg = f"🚨 有貨 IN STOCK\n{title}\n分店: {', '.join(hits)}\n{link}"
                log(msg.replace("\n", " | "))
                notify(msg)
                alerted.update((h, part) for h in new)
        time.sleep(random.uniform(1, 2))
    if not_open == len(parts):
        log("Store pickup not open yet for iPhone Duo (normal before launch) - still watching")
    return not_open < len(parts)


def main():
    once = "--once" in sys.argv          # GitHub Actions: one pass per scheduled run
    st = load_state()
    try:
        parts = find_parts()
    except Exception as e:
        parts = []
        log(f"Could not read part numbers from Apple's page ({e})")
    if not parts:
        # Don't spam: tell the user once per state lifetime
        if not st.get("noparts_told"):
            notify("❌ No iPhone Duo part numbers found. Add them to MANUAL_PARTS in stock_alert.py.")
            st["noparts_told"] = True
            save_state(st)
        log("No part numbers found")
        return 1 if once else 0

    log(f"Watching {len(parts)} iPhone Duo variants: {', '.join(parts)}")
    if not st["started"]:
        notify(f"✅ iPhone Duo alert started - watching {len(parts)} variants")
        st["started"] = True
    save_state(st)

    if once:
        # Keep checking for RUN_SECONDS (default 280) so one 5-minute Actions run covers the whole gap.
        deadline = time.time() + float(os.environ.get("RUN_SECONDS", "280"))
        gap = float(os.environ.get("ROUND_GAP_SECONDS", "12"))
        while True:
            one_round(parts, st)
            save_state(st)
            if time.time() + gap + 15 > deadline:
                break
            time.sleep(gap + random.uniform(0, 4))
        if os.environ.get("HEARTBEAT") == "1":
            notify("💚 iPhone Duo watcher is running. 未有新貨 / no new stock" if not st["alerted"]
                   else "💚 iPhone Duo watcher is running")
        return 0

    while True:
        one_round(parts, st)
        save_state(st)
        time.sleep(CHECK_EVERY_SECONDS + random.uniform(0, 15))


if __name__ == "__main__":
    sys.exit(main())
