#!/usr/bin/env python3
"""Submit every page to IndexNow. Run after a deploy.

    python3 indexnow.py

IndexNow notifies Bing, Yandex, Seznam and Naver within minutes. Google does
not participate, so use Search Console for Google.
"""
import json
import urllib.request

KEY = "0e70e4ee2f9418e242c9b285c48147ff"
HOST = "packev.xyz"
URLS = [
    "https://packev.xyz/",
    "https://packev.xyz/platforms/",
    "https://packev.xyz/platforms/courtyard/",
    "https://packev.xyz/platforms/packz/",
    "https://packev.xyz/platforms/arena-club/",
    "https://packev.xyz/platforms/clutch-packs/",
    "https://packev.xyz/platforms/fanatics-instant-rips/",
    "https://packev.xyz/platforms/crown-rips/",
    "https://packev.xyz/platforms/tilt-rips/",
    "https://packev.xyz/compare/courtyard-vs-packz/",
    "https://packev.xyz/guides/chase-card-odds/",
    "https://packev.xyz/guides/bonus-offers/",
    "https://packev.xyz/platforms/mintpull/",
    "https://packev.xyz/legal/",
    "https://packev.xyz/guides/withdrawals/",
    "https://packev.xyz/changelog/",
    "https://packev.xyz/alternatives/courtyard/",
    "https://packev.xyz/alternatives/fanatics-instant-rips/",
    "https://packev.xyz/alternatives/packz/",
    "https://packev.xyz/platforms/pickem/",
    "https://packev.xyz/platforms/packed/",
    "https://packev.xyz/platforms/fast-rips/",
    "https://packev.xyz/platforms/chalkboard/",
    "https://packev.xyz/platforms/poke-collect/",
    "https://packev.xyz/platforms/letsgo/",
    "https://packev.xyz/platforms/rare-candy/",
    "https://packev.xyz/platforms/swishx/",
    "https://packev.xyz/platforms/triumph/",
    "https://packev.xyz/platforms/gotya/",
    "https://packev.xyz/platforms/holofoil/",
    "https://packev.xyz/platforms/catchback/",
    "https://packev.xyz/platforms/rip-station/",
    "https://packev.xyz/platforms/underdog/",
    "https://packev.xyz/platforms/lastpack/",
    "https://packev.xyz/platforms/saja/",
    "https://packev.xyz/compare/",
    "https://packev.xyz/guides/buyback-rates/",
    "https://packev.xyz/calculator/",
    "https://packev.xyz/methodology/",
    "https://packev.xyz/is-card-ripping-gambling/",
    "https://packev.xyz/data/"
]

payload = json.dumps({
    "host": HOST,
    "key": KEY,
    "keyLocation": "https://" + HOST + "/" + KEY + ".txt",
    "urlList": URLS,
}).encode()

req = urllib.request.Request(
    "https://api.indexnow.org/IndexNow",
    data=payload,
    headers={"Content-Type": "application/json; charset=utf-8"},
)
with urllib.request.urlopen(req) as r:
    print("IndexNow responded " + str(r.status) + " for "
          + str(len(URLS)) + " URLs")
    print("200 or 202 means accepted.")
