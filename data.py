"""Load and compute pack EV data from the collected odds CSVs."""
import csv
from collections import OrderedDict

COLLECTED = "2026-09-21"
UPDATED = "2026-10-22"

CATEGORY_LABELS = {
    "pokemon": "Pokémon", "sneakers": "Sneakers", "onepiece": "One Piece",
    "wildcard": "Wildcard", "sports": "Sports", "baseball": "Baseball",
    "basketball": "Basketball", "football": "Football", "soccer": "Soccer",
    "hockey": "Hockey", "comics": "Comics", "watches": "Watches",
    "coins": "Coins", "limited": "Limited edition", "mtg": "Magic: The Gathering",
    "sealedbooster": "Sealed boosters",
}


def money(x):
    """$1,234.50 -> trailing .00 dropped."""
    s = "${:,.2f}".format(x)
    return s[:-3] if s.endswith(".00") else s


def pct(x, dp=1):
    return ("{:,.%df}%%" % dp).format(x)


def load_courtyard(path="courtyard_odds_2026-09-21.csv"):
    """Courtyard posts an exact EV per pack. Tiers are dollar ranges."""
    packs = OrderedDict()
    posted_ev = {}
    with open(path, encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if not row or row[0] == "platform":
                continue
            if row[0] == "EV":
                posted_ev[row[1]] = float(row[2])
                continue
            name = row[2]
            p = packs.setdefault(name, {
                "name": name, "category": row[1], "price": float(row[3]), "tiers": [],
            })
            p["tiers"].append({
                "min": float(row[4]), "max": float(row[5]), "odds": float(row[6]),
            })

    out = []
    for name, p in packs.items():
        price = p["price"]
        ev = posted_ev.get(name)
        odds_sum = sum(t["odds"] for t in p["tiers"])
        # Chance of a card worth at least roughly the pack price. Tiers often
        # start exactly at the price (e.g. $25-$50 on a $25 pack), so the
        # threshold allows a small rounding margin.
        at_or_above = sum(t["odds"] for t in p["tiers"] if t["min"] >= price * 0.95)
        floor = min(t["min"] for t in p["tiers"])
        top = max(t["max"] for t in p["tiers"])
        out.append({
            "platform": "courtyard",
            "name": name,
            "slug": slugify(name),
            "category": p["category"],
            "category_label": CATEGORY_LABELS[p["category"]],
            "price": price,
            "ev": ev,
            "ev_ratio": (ev / price) if ev else None,
            "credit_ratio": (ev / price * 0.90) if ev else None,
            "odds_sum": odds_sum,
            "at_or_above": at_or_above,
            "floor_ratio": floor / price,
            "top": top,
            "top_multiple": top / price,
            "tiers": p["tiers"],
            "spicy": "Spicy" in name,
        })
    out.sort(key=lambda r: (r["category_label"], r["price"]))
    return out


def load_packz(path="packz_odds_2026-09-21.csv"):
    """Packz publishes value RANGES only, so EV is a band, not a point."""
    packs = OrderedDict()
    with open(path, encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if not row or row[0] == "platform":
                continue
            name = row[2]
            p = packs.setdefault(name, {
                "name": name, "category": row[1], "price": float(row[3]), "tiers": [],
            })
            p["tiers"].append({
                "min": float(row[4]), "max": float(row[5]), "odds": float(row[6]),
            })

    out = []
    for name, p in packs.items():
        price = p["price"]
        lo = sum(t["min"] * t["odds"] / 100 for t in p["tiers"])
        hi = sum(t["max"] * t["odds"] / 100 for t in p["tiers"])
        mid = (lo + hi) / 2
        at_or_above = sum(t["odds"] for t in p["tiers"] if t["min"] >= price * 0.95)
        out.append({
            "platform": "packz",
            "name": name,
            "slug": slugify(name),
            "category": p["category"],
            "category_label": CATEGORY_LABELS[p["category"]],
            "price": price,
            "ev_low": lo, "ev_mid": mid, "ev_high": hi,
            "ratio_low": lo / price, "ratio_mid": mid / price, "ratio_high": hi / price,
            "credit_ratio": mid / price * 0.90,
            "odds_sum": sum(t["odds"] for t in p["tiers"]),
            "at_or_above": at_or_above,
            "top": max(t["max"] for t in p["tiers"]),
            "top_multiple": max(t["max"] for t in p["tiers"]) / price,
            "tiers": p["tiers"],
        })
    out.sort(key=lambda r: (r["category_label"], r["price"]))
    return out


# Arena Club publishes per-card hit rates and no values at all, so there is no
# EV to compute yet. These are the two checklists we collected in full.
ARENA_CLUB_PACKS = [
    {"name": "Pokémon Bronze", "price": 25, "collected": "2026-09-21",
     "tiers": [("GRAIL", 3, 0.01), ("CHASE", 8, 0.25), ("LINEUP", 50, 1.96)],
     "odds_sum": 100.03},
    {"name": "Basketball Gold", "price": 100, "collected": "2026-09-21",
     "tiers": [("GRAIL", 3, 0.02), ("CHASE", 8, 0.25), ("LINEUP", 50, 1.96)],
     "odds_sum": 100.06},
    # Re-collected a month later: an entirely different checklist, a shorter
    # Lineup, and displayed rates that no longer sum to 100%.
    {"name": "Pokémon Bronze", "price": 25, "collected": "2026-10-21",
     "tiers": [("GRAIL", 3, 0.01), ("CHASE", 8, 0.25), ("LINEUP", 24, 1.96)],
     "odds_sum": 49.07},
]


# Crown Rips publishes a minimum and maximum pull value per pack but no pull
# rates, so no expected value can be calculated. These figures are REPORTED by
# a third party, not collected by us from the platform, and the page says so.
CROWN_RIPS_PACKS = [
    ("Starter", 1, 0.10, 20),
    ("Basic", 5, 1, 100),
    ("Signature", 10, 3, 200),
    ("Bronze", 25, 8, 500),
    ("Silver", 50, 15, 1000),
    ("Gold", 100, 30, 2000),
    ("Sapphire", 250, 75, 5000),
    ("Amethyst", 500, 150, 10000),
    ("Ultimate", 1000, 300, 67200),
    ("Diamond", 2500, 850, 100000),
]
CROWN_REPORTED = "2026-07-27"

# Clutch Packs is the only platform that publishes OBSERVED results rather than
# a claim: every pack opening is recorded on the Polygon blockchain and the
# averages below are real pulls valued at the time they were pulled.
# (category, pack, price, verified_pulls, avg_pull, bands)
# bands = (10x+, 5-10x, 2-5x, 1-2x, 0.5-1x, bottom band)
CLUTCH_PACKS = [
    ("Multisport", "Liftoff", 25, 69558, 24.92, (0.3, 2.6, 7.6, 16.2, 28.0, 45.4)),
    ("Multisport", "Ascent", 100, 21127, 106.61, (0.4, 2.5, 7.6, 15.2, 28.2, 46.1)),
    ("Multisport", "Orbit", 500, 2789, 490.37, (0.2, 3.7, 6.7, 12.8, 27.9, 48.7)),
    ("Multisport", "Galaxy", 1000, 1943, 996.09, (0.5, 3.1, 6.9, 11.7, 23.7, 54.0)),
    ("Multisport", "Moonshot", 2500, 1102, 2677.53, (0.7, 3.2, 7.4, 11.4, 24.0, 53.4)),
    ("Pokémon", "Liftoff", 25, 17008, 25.71, (0.3, 2.5, 7.7, 16.9, 31.4, 41.3)),
    ("Pokémon", "Ignition", 50, 7496, 49.50, (0.3, 3.0, 8.3, 13.3, 24.9, 50.3)),
    ("Pokémon", "Ascent", 100, 4293, 97.95, (0.05, 2.8, 7.0, 14.0, 27.1, 48.9)),
    ("Pokémon", "Orbit", 500, 786, 501.44, (0.4, 3.1, 8.0, 12.2, 22.3, 54.1)),
    ("One Piece", "Liftoff", 25, 6077, 25.19, (0.1, 3.0, 7.3, 14.7, 29.7, 45.3)),
    ("One Piece", "Ignition", 50, 3248, 48.84, (0.05, 3.5, 8.9, 13.1, 19.6, 54.8)),
    ("One Piece", "Ascent", 100, 1964, 101.46, (0.3, 2.9, 7.9, 14.9, 26.0, 48.1)),
    ("One Piece", "Orbit", 500, 412, 504.45, (0.2, 3.2, 9.5, 12.9, 19.2, 55.1)),
    ("Soccer", "Liftoff", 25, 5754, 25.10, (0.1, 2.9, 8.1, 14.7, 31.3, 42.9)),
    ("Soccer", "Ascent", 100, 1619, 101.47, (0.2, 3.4, 7.5, 15.7, 24.4, 48.9)),
    ("Soccer", "Orbit", 500, 164, 460.28, (0.0, 1.8, 7.3, 16.5, 27.4, 47.0)),
    ("Football", "Ascent", 100, 3797, 99.09, (0.4, 3.0, 8.6, 12.3, 21.5, 54.2)),
    ("Football", "Apex", 350, 552, 335.22, (1.8, 2.2, 5.4, 9.8, 16.1, 64.7)),
    ("Football", "Galaxy", 1000, 127, 1011.02, (0.0, 4.7, 7.1, 12.6, 17.3, 58.3)),
    ("Basketball", "Ascent", 100, 260, 113.17, (0.0, 5.4, 8.8, 16.5, 21.5, 47.7)),
    ("Basketball", "Apex", 350, 154, 354.35, (0.6, 5.2, 3.9, 13.6, 13.6, 63.0)),
    ("Baseball", "Ascent", 100, 717, 97.23, (0.6, 2.0, 8.5, 14.5, 23.0, 51.5)),
    ("Baseball", "Apex", 350, 185, 357.95, (2.2, 3.2, 3.8, 12.4, 13.5, 64.9)),
    ("Multisport", "BookIt Sports Silver", 50, 6366, 50.38, (0.0, 1.4, 5.0, 20.2, 73.5, 0.0)),
    ("Multisport", "BookIt Sports Gold", 250, 1058, 242.36, (1.3, 2.5, 8.1, 9.0, 16.5, 62.6)),
]
CLUTCH_BAND_LABELS = ["10x+", "5–10x", "2–5x", "1–2x", "0.5–1x", "Under 0.5x"]
CLUTCH_COLLECTED = "2026-10-21"


def clutch_stats():
    tot = sum(p[3] for p in CLUTCH_PACKS)
    return {
        "n_packs": len(CLUTCH_PACKS),
        "pulls": tot,
        "w_avg": sum(p[4] / p[2] * p[3] for p in CLUTCH_PACKS) / tot,
        "below_1x": sum((p[5][4] + p[5][5]) * p[3] for p in CLUTCH_PACKS) / tot,
        "at_2x": sum((p[5][0] + p[5][1] + p[5][2]) * p[3] for p in CLUTCH_PACKS) / tot,
        "min_mult": min(p[4] / p[2] for p in CLUTCH_PACKS),
        "max_mult": max(p[4] / p[2] for p in CLUTCH_PACKS),
    }


# What each platform's buyback actually converts to. `effective` is the rate
# after any deducted fee; None where the platform publishes nothing usable.
# `cash` is True only where proceeds reach a bank account or wallet the holder
# controls, False where they are locked to platform spend, None where unknown.
BUYBACK_TERMS = [
    # name, headline, effective, cash?, payout form, who sets the valuation
    ("Arena Club", 0.90, 0.90, True,
     "Arena Club Wallet, withdrawable to a bank account or debit card via Stripe",
     "Arena Club, which also grades some of the cards itself"),
    ("Tilt Rips", 0.90, 0.90, True,
     "Wallet, withdrawable in US dollars or several cryptocurrencies",
     "&ldquo;Live market data,&rdquo; source not named; price cannot be disputed"),
    ("Packz", 0.90, 0.90, False,
     "Site credit that cannot be withdrawn and can only buy more packs",
     "Packz"),
    ("Courtyard", 0.90, 0.85, None,
     "Settles in USDC; independent tracking measured actual offers nearer 85%",
     "Courtyard"),
    ("Fanatics Instant Rips", 0.90, 0.846, False,
     "Fanatics Live credits, spendable across Fanatics Live but not withdrawable",
     "Card Ladder, a third-party sales-data service"),
    ("Crown Rips", 1.00, None, None,
     "Claimed at 100% of fair market value; form of proceeds unconfirmed",
     "Crown Rips"),
    ("Clutch Packs", None, None, None,
     "No buyback or sell-back terms disclosed anywhere",
     "Market value at the time of the pull, source not named"),
    ("MintPull", 1.00, None, False,
     "Returns are credited as &ldquo;additional pack purchase credits&rdquo; "
     "(&sect;5.5); withdrawals capped at $250 per seven days and limited to "
     "proceeds from sales",
     "&ldquo;Proprietary system&rdquo; which &ldquo;may not match published "
     "market values&rdquo; and is &ldquo;subject to change at any time&rdquo;"),
    ("Pickem", 0.90, 0.90, True,
     "USD balance, withdrawable to a bank card ($6 minimum, $2,500 per "
     "withdrawal); only sale proceeds can be withdrawn",
     "Pickem's displayed fair market value"),
    ("Packed", 1.00, 1.00, True,
     "Withdrawable to debit card, bank, PayPal or Venmo &mdash; but only "
     "within a storage window the terms set at one day",
     "Packed, via a &ldquo;semi-automated proprietary system&rdquo;; locked "
     "at the moment of the pull"),
    ("SAJA", 1.00, 1.00, True,
     "100% of displayed value, locked at the pull, good for 7 days; paid to "
     "the SAJA balance and withdrawn through Stripe. Deposited funds must be "
     "spent once before they can be withdrawn, and every withdrawal is "
     "subject to a discretionary hold",
     "<strong>Third-party market pricing services</strong> &mdash; one of "
     "only three platforms we track that does not set its own values"),
    ("LastPack", 1.00, 1.00, True,
     "The FAQ says user-initiated sellback is &ldquo;100% of fair market "
     "value, credited to your Lastpack balance,&rdquo; cashable through "
     "Coinflow or USDC-on-Solana, capped at $10,000 per 7 days (&sect;5.3a). "
     "But &sect;4.5 says the credit is &ldquo;additional pack purchase "
     "credits&rdquo; &mdash; the two contradict each other",
     "LastPack, from &ldquo;realtime sales statistics&rdquo; via a "
     "&ldquo;proprietary system&rdquo;; &sect;4.4 says it &ldquo;may not "
     "match published market values&rdquo;; locked at the time of purchase"),
    ("Underdog Rips", 0.85, None, None,
     "Underdog&rsquo;s own help centre states no rate and no payout form. "
     "Phygitals, the named third party that powers it, documents &ldquo;85% "
     "of FMV&rdquo; with &ldquo;all buyback payouts&hellip; denominated and "
     "paid in USDC&rdquo; to a wallet. We could not confirm which applies on "
     "Underdog",
     "Phygitals, from &ldquo;industry-standard pricing providers for graded "
     "collectibles&rdquo; &mdash; third-party sourced, though the providers "
     "are not named; fixed at the time of the pull"),
    ("Rip Station", 0.83, 0.83, None,
     "&ldquo;Lands in your wallet.&rdquo; The FAQ describes no withdrawal "
     "process, no minimum and no cap &mdash; the only mention of withdrawing "
     "is in the answer about the service shutting down. 83% of estimated "
     "market value, within 7 days, &ldquo;not guaranteed liquidity&rdquo;",
     "Rip Station, from &ldquo;real recent sales across the trading card "
     "market&rdquo;; the same data sets the buyback"),
    ("CatchBack", 0.90, 0.90, None,
     "90% of value, displayed beside the odds. A paid &ldquo;Boost&rdquo; "
     "add-on raises it to 110% on a winning pull and &ldquo;Insurance&rdquo; "
     "guarantees a 70%-of-price floor, each within five minutes. We could not "
     "reach the terms to confirm the payout form",
     "CatchBack; the full available-hits pool and its per-card values are "
     "published on the pack page, which is more than most"),
    ("Holofoil", 0.90, None, False,
     "Holofoil Credit only. &sect;4: credit &ldquo;cannot be withdrawn, "
     "cashed out, sold, or transferred,&rdquo; and Holofoil &ldquo;does not "
     "offer cash payouts for sell-backs, vault conversions, promotions, or "
     "returns.&rdquo; The only exit is shipping the physical card",
     "Holofoil, by its own methods; &sect;8 makes its determination "
     "&ldquo;final,&rdquo; appealable only through the obvious-error process "
     "in &sect;9"),
    ("Gotya", 0.90, 0.90, True,
     "Credited to the Wallet as internal ledger credit (&sect;20), then "
     "withdrawn to a verified bank account in the holder's own legal name "
     "(&sect;21); the free-pack page puts the cash-out floor at a $25 balance",
     "Gotya, as &ldquo;a good-faith internal estimate&rdquo; (&sect;&sect;2, "
     "14); &sect;24 refuses returns for &ldquo;Disagreement with FMV&rdquo;"),
    ("Rips by Triumph", 1.00, None, True,
     "Withdrawable to debit card, bank, PayPal or Venmo; $6 minimum, up to "
     "$10,000 a day at Triumph's discretion, Venmo capped at $4,000 per "
     "rolling 24 hours; terms say &ldquo;within two weeks,&rdquo; the FAQ "
     "says instant withdrawals average ten minutes",
     "Triumph, via &ldquo;realtime sales statistics&rdquo; and &ldquo;a "
     "proprietary system&rdquo; which &ldquo;may not match published market "
     "values&rdquo; (&sect;5.4); locked at the FMV in effect at purchase"),
    ("SwishX", 0.90, 0.88, True,
     "Wallet, withdrawn to a linked payout method and verified through "
     "Stripe. Published as &ldquo;85-90% depending on the pack&rdquo; within "
     "24 hours, dropping to &ldquo;75-80%&rdquo; on a re-quote afterwards",
     "SwishX's own fair market value, but every tier's target FMV is "
     "published on the pack page, so the figure can be checked against the "
     "posted expected value"),
    ("Rare Candy", 0.90, None, False,
     "Paid in Candy, the in-app currency. &sect;8.1: Candies &ldquo;have no "
     "cash or monetary value and are not redeemable, refundable, or "
     "exchangeable for&rdquo; dollars or any monetary payment. Every pack "
     "does guarantee a floor of 50% of the pack price in Candy",
     "Rare Candy, &ldquo;in its sole discretion&rdquo; (&sect;3); &sect;6.2 "
     "calls its valuations &ldquo;inherently subjective&rdquo; and not "
     "appraisals or guarantees"),
    ("LETSGO", 0.90, None, True,
     "Paid to PayPal, Venmo, debit card or bank transfer. The website says "
     "&ldquo;Sell at 90% of fair market value&rdquo;; the App Store listing "
     "says &ldquo;up to 90%&rdquo;",
     "Not stated on the website, the app listings or any document we could "
     "reach"),
    ("Poke-Collect", None, None, "n/a",
     "No buyback is built into the pack. A separate retail buylist pays in "
     "store credit or PayPal after a human review within 24 hours, so there "
     "is no instant liquidity and no published rate",
     "Poke-Collect's buylist, card by card; no instant algorithmic valuation "
     "and no stated percentage"),
    ("Chalkboard Pulls", 1.00, 1.00, True,
     "100% of FMV credited to the Wallet as Buyback Credit, withdrawable to an "
     "external payment method (ACH via Aeropay, typically within ten business "
     "days); deposits themselves are never withdrawable (&sect;8.2)",
     "Chalkboard, &ldquo;in its sole discretion utilizing proprietary "
     "methodologies and market data&rdquo;; FMV is &ldquo;final and "
     "non-appealable&rdquo; (&sect;7.5)"),
    ("Fast Rips", 1.00, None, False,
     "Marketing says cash to a bank; the terms say Platform Credit, "
     "non-withdrawable, with withdrawals at the company's sole discretion",
     "&ldquo;Proprietary, Platform-administered valuation used exclusively "
     "for internal Platform purposes&rdquo;"),
]


# ---------------------------------------------------------------- trust flags
# Short, scannable risk labels. Every flag must trace to a quoted term or a
# figure we published; nothing here is a vibe.
FLAGS = {
    "cash": ("Pays cash, not credit", "pos",
             "The platform’s own terms describe buyback proceeds reaching a bank account, card or wallet you control. We have not withdrawn from any platform ourselves"),
    "credit": ("Credit only", "neg",
               "Buyback pays platform credit that cannot be withdrawn"),
    "clock": ("Short clock", "neg",
              "You have under a week to decide before the platform sells the card"),
    "conflict": ("Marketing conflicts with terms", "neg",
                 "A published claim is contradicted by the platform's own terms"),
    "noodds": ("No odds published", "neg",
               "No pull rates or probabilities are published anywhere public"),
    "odds": ("Odds published", "pos",
             "Pull rates or value-band probabilities are published"),
    "ev": ("Expected value published", "pos",
           "The platform states an expected value, or publishes observed results"),
    "cap": ("Withdrawal cap", "neg",
            "Withdrawals are capped low enough to delay getting money out"),
    "offshore": ("Non-US operator", "neg",
                 "Operated outside the US under non-US law"),
    "shipdefault": ("Card ships by default", "pos",
                    "Do nothing and the card is sent to you, not sold back"),
    "forfeit": ("Can confiscate your cards", "neg",
                "Terms allow voiding transactions and forfeiting vaulted cards on suspicion alone"),
    "thirdparty": ("Third-party valuations", "pos",
                   "Card values come from an outside pricing service, not the platform itself"),
    "sidebets": ("Sells paid side bets", "neg",
                 "Optional wagers sold on top of the pack, at the moment of purchase"),
    "keepdefault": ("Keeps by default", "pos",
                    "Do nothing and you keep the card; the platform does not sell it"),
    "storefront": ("Physical storefront", "pos",
                   "Operates a real retail address, not only an app or website"),
}

PLATFORM_FLAGS = {
    "clutch-packs": ["ev", "odds"],
    "courtyard": ["ev", "odds"],
    "packz": ["odds", "credit"],
    "arena-club": ["odds", "cash"],
    "fanatics-instant-rips": ["noodds", "credit"],
    "tilt-rips": ["noodds", "cash"],
    "pickem": ["odds", "cash", "clock"],
    "packed": ["cash", "clock"],
    "crown-rips": ["noodds", "clock"],
    "fast-rips": ["noodds", "conflict", "credit"],
    "mintpull": ["noodds", "credit", "cap", "offshore", "clock"],
    "chalkboard": ["noodds", "cash", "clock"],
    "poke-collect": ["odds", "shipdefault", "storefront"],
    "letsgo": ["noodds", "cash", "conflict", "offshore"],
    "rare-candy": ["odds", "credit", "keepdefault"],
    "swishx": ["odds", "ev", "cash", "clock"],
    "triumph": ["noodds", "cash", "conflict", "clock"],
    "gotya": ["odds", "ev", "cash", "offshore"],
    "holofoil": ["odds", "credit", "clock"],
    "catchback": ["odds", "ev", "sidebets", "clock"],
    "rip-station": ["noodds", "offshore", "clock"],
    "underdog": ["odds", "ev", "clock"],
    "lastpack": ["odds", "ev", "cash", "clock"],
    "saja": ["odds", "ev", "cash", "thirdparty", "forfeit"],
}

# --------------------------------------------------------------- availability
# Per-state restrictions we can source to a platform's own published terms.
STATE_RESTRICTIONS = {
    "Illinois": ["Rips by Triumph (50/50 pack only)"],
    "Michigan": ["Pickem"],
    "Minnesota": ["Pickem"],
    "Montana": ["Pickem"],
    "Nevada": ["Pickem", "MintPull", "Rips by Triumph"],
    "North Carolina": ["Rips by Triumph (50/50 pack only)"],
    "Utah": ["Rips by Triumph (50/50 pack only)"],
    "Washington": ["Pickem", "Rare Candy"],
}

US_ONLY = ["Packz", "Packed", "Fast Rips", "MintPull", "Pickem", "Crown Rips"]
UNKNOWN_AVAILABILITY = ["Arena Club", "Clutch Packs", "Tilt Rips",
                        "Fanatics Instant Rips"]

# ------------------------------------------------------------------ changelog
# Dated record of what we collected and what changed. Newest first.
# SAJA — Silver Pack rarity rates, from the saja.com marketing page, 2026-10-23.
# SAJA publishes percentages only; no value ranges are given anywhere public,
# so no expected value can be computed from the outside.
SAJA_COLLECTED = "2026-10-23"

SAJA_PACK = {
    "name": "Silver Pack", "price": 10.00, "posted_ev": "PACK EV 100%",
    "bands": [
        ("Common", 54.5), ("Uncommon", 24.5), ("Rare", 12.0),
        ("Epic", 5.0), ("Legendary", 2.5), ("Grail", 0.5), ("God Pack", 0.1),
    ],
}


def saja_stats():
    psum = sum(q for _, q in SAJA_PACK["bands"])
    return {"psum": psum, "gap": 100.0 - psum,
            "n": len(SAJA_PACK["bands"]), "price": SAJA_PACK["price"]}


CHANGELOG = [
    ("2026-10-23", "Correction: the “Cash-out verified” label overstated what we had done",
     "That chip appeared on eleven platform pages and said “verified.” We had "
     "read each platform’s terms and help pages describing a withdrawal path; we "
     "had not withdrawn money from any of them. The label now reads “Pays cash, "
     "not credit,” and its description says plainly that we have not tested it. "
     "No underlying figure changed.",
     "/changelog/"),
    ("2026-10-23", "SAJA added — the best headline terms, and the broadest forfeiture clause",
     "100% expected value and a 100% buyback, card values from third-party "
     "pricing services, ownership passing at the pull, a free vault with no "
     "deadline, and a cash refund when SAJA prices a card above market. The "
     "same terms let SAJA void every transaction and confiscate vaulted cards "
     "on suspicion, &ldquo;without any obligation to investigate or to prove "
     "it.&rdquo;",
     "/platforms/saja/"),
    ("2026-10-23", "LastPack added — and the shared terms template turns up a third time",
     "LastPack posts a sell-back rate, min and max value, a GROSS EV and a "
     "full rarity table on every pack page, and lets you verify a pull "
     "afterwards. Its &sect;4.3 and &sect;4.4 are the same clauses we found in "
     "Triumph&rsquo;s and MintPull&rsquo;s terms. And &sect;4.5 contradicts its "
     "own FAQ about whether sell-back proceeds are cash or pack credit.",
     "/platforms/lastpack/"),
    ("2026-10-22", "Underdog Rips added, and Phygitals documented",
     "Underdog&rsquo;s help centre gives a three-day window and no buyback "
     "rate. Phygitals, the third party that sources, vaults and ships the "
     "cards, documents 85% of FMV paid in USDC &mdash; and buyback windows of "
     "30 minutes, 3 days or 7 days depending on card type. A 30-minute window "
     "would be the shortest on this site.",
     "/platforms/underdog/"),
    ("2026-10-22", "Rip Station added — an EV page with no EV on it",
     "Rip Station publishes a dedicated &ldquo;EV &amp; Odds&rdquo; page. On "
     "the day we read it, all ten packs showed &ldquo;Data unavailable &mdash; "
     "inventory not verified.&rdquo; Its buyback is 83%, the lowest advertised "
     "figure we have found, and it is operated by a Panama company under a "
     "Delaware parent.",
     "/platforms/rip-station/"),
    ("2026-10-22", "CatchBack added — the first platform selling side bets on the pack",
     "Publishes full band odds summing to exactly 100%, a posted expected "
     "value and the entire card pool with values. It also sells two optional "
     "wagers at $3.75 each on a $25 pack: a &ldquo;Boost&rdquo; that pays for "
     "itself only above $18.75 of card value, and &ldquo;Insurance&rdquo; "
     "capped at a $10.30 payout. Both expire in five minutes.",
     "/platforms/catchback/"),
    ("2026-10-22", "Holofoil added — the only platform with no cash exit at all",
     "&sect;4: Holofoil Credit &ldquo;cannot be withdrawn, cashed out, sold, or "
     "transferred,&rdquo; and there are no cash payouts for sell-backs, vault "
     "conversions, promotions or returns. &sect;10 converts vaulted cards to "
     "that same credit after 30 days. Shipping the physical card is the only "
     "way value leaves. Its &sect;5 does contractually require pull rates on "
     "every product page.",
     "/platforms/holofoil/"),
    ("2026-10-22", "Gotya added, and its central claim checks out",
     "Gotya says &ldquo;each pack&rsquo;s expected value equals its price.&rdquo; "
     "We collected five packs: every odds table sums to exactly 100%, and the "
     "midpoint expected value averages 100.5% of price. The free $10 pack is "
     "the one exception, at 92.6%. Governed by the law of England and Wales, "
     "and &sect;30 converts vaulted cards to credit after 180 days idle.",
     "/platforms/gotya/"),
    ("2026-10-22", "Rips by Triumph added — and its terms match MintPull's, clause for clause",
     "The largest platform we track, at 1M+ installs. Its FAQ headlines a "
     "&ldquo;100% BUYBACK GUARANTEE&rdquo;; &sect;5.5 of its terms says "
     "Triumph &ldquo;is under no obligation to&rdquo; offer a Return. Its "
     "&sect;5.2&ndash;5.5 share capitalised sentences and section numbering "
     "with MintPull's, verbatim.",
     "/platforms/triumph/"),
    ("2026-10-22", "SwishX added — the most complete disclosure we have found",
     "Posts an expected value on every pack, publishes per-tier odds with an "
     "explicit target FMV and the named card pool, states packs are "
     "&ldquo;designed to a 100% value target,&rdquo; and publishes its buyback "
     "band. We recomputed its posted EV from its own odds on five packs and "
     "matched it to within 0.9% every time.",
     "/platforms/swishx/"),
    ("2026-10-22", "Rare Candy Instapacks added, with full odds collected",
     "Publishes value-band pull rates for every pack on the open web, plus a "
     "guaranteed floor of 50% of the pack price. The first new odds dataset we "
     "have been able to collect since Courtyard and Packz. The catch: the "
     "exchange pays in Candy, which &sect;8.1 says has no cash value.",
     "/platforms/rare-candy/"),
    ("2026-10-22", "LETSGO added",
     "The website says &ldquo;Sell at 90% of fair market value&rdquo;; the App "
     "Store listing says &ldquo;up to 90%.&rdquo; The site names no operating "
     "company &mdash; the Google Play record lists LETSGO INTERACTIVE LTD in "
     "Ra&rsquo;anana, Israel. Its own homepage warns the platform &ldquo;may "
     "be illegal in the jurisdiction in which you are located.&rdquo;",
     "/platforms/letsgo/"),
    ("2026-10-22", "Poke-Collect added",
     "The first platform we have found whose clock ends in your favour: cards "
     "sit in the vault up to a year and are then &ldquo;shipped to you "
     "automatically for free.&rdquo; Every other platform auto-sells. Also the "
     "only operator with a physical retail address. Tier odds are published "
     "but render in-browser; not yet collected.",
     "/platforms/poke-collect/"),
    ("2026-10-22", "Chalkboard Pulls added",
     "&sect;7.1 pays 100% of FMV as withdrawable Buyback Credit &mdash; the "
     "best-documented cash terms we have read. &sect;7.5 also makes Chalkboard "
     "the sole, &ldquo;final and non-appealable&rdquo; judge of that FMV, and "
     "the decision window is a single 24-hour period.",
     "/platforms/chalkboard/"),
    ("2026-10-22", "MintPull added",
     "Terms cap withdrawals at $250 per seven days and credit returns as pack "
     "purchase credit, against a &ldquo;100% FMV guarantee&rdquo; on the "
     "homepage. Operated from Hong Kong under Hong Kong law.",
     "/platforms/mintpull/"),
    ("2026-10-22", "Pickem added",
     "Three-hour window from opening a pack before the card is sold "
     "automatically &mdash; the shortest in the category.",
     "/platforms/pickem/"),
    ("2026-10-22", "Packed added",
     "&sect;6.3 limits storage to one day. Terms require Value Band odds to be "
     "displayed, which no other platform contractually commits to.",
     "/platforms/packed/"),
    ("2026-10-22", "Fast Rips added",
     "Homepage advertises a 100% buyback paid to a bank account; &sect;6.3 of "
     "its terms says Platform Credit has no cash value outside the platform.",
     "/platforms/fast-rips/"),
    ("2026-10-22", "Buyback comparison published",
     "Five platforms advertise 90%. One pays 84.6% after fees and three pay "
     "credit that cannot be withdrawn.",
     "/guides/buyback-rates/"),
    ("2026-10-21", "Arena Club checklist rotated entirely in one month",
     "Not one card from the September $25 Pok&eacute;mon Bronze checklist "
     "appeared in the October one. The Lineup tier shrank from 50 cards to 24, "
     "and the displayed per-card rates then summed to 49.07% rather than 100%. "
     "Unresolved.",
     "/platforms/arena-club/"),
    ("2026-10-21", "Clutch Packs observed results collected",
     "158,556 verified on-chain pulls across 25 packs, averaging 1.01&times; "
     "the pack price &mdash; the only observed return data in the category.",
     "/platforms/clutch-packs/"),
    ("2026-09-21", "Courtyard and Packz odds collected",
     "All 92 Courtyard packs and all 14 Packz packs, collected first-hand and "
     "published as open data.",
     "/data/"),
]


def slugify(s):
    out = []
    for ch in s.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_/":
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


# ------------------------------------------------- structured platform table
# Single source of truth for the comparison tool. Every value here is already
# published on that platform's own page and sourced there; nothing new is
# asserted. Keys stay identical across platforms so columns line up.
#   ok   = favourable, neg = unfavourable, "" = neutral or unknown
PLATFORMS = [
    {
        "slug": "clutch-packs", "name": "Clutch Packs", "path": "/platforms/clutch-packs/",
        "blurb": "The only platform publishing observed pull results rather than its own valuations.",
        "packs": "25 measured", "prices": "$25&ndash;$2,500",
        "odds": ("Observed results, on-chain", "ok"),
        "ev": ("Observed, not posted", "ok"),
        "ret": ("1.01&times; over 158,556 pulls", "ok"),
        "buyback": ("Not disclosed", "neg"),
        "cash": ("Not disclosed", "neg"),
        "valuer": ("Market value at the pull, source not named", ""),
        "clock": ("Not stated", ""),
        "operator": "Not established in our research", "juris": ("United States", "ok"),
        "age": ("Not stated", ""), "states": ("None published", ""),
    },
    {
        "slug": "lastpack", "name": "LastPack", "path": "/platforms/lastpack/",
        "blurb": "Shows the EV, the odds, the sell-back rate and a per-pull fairness check &mdash; on a terms template whose clauses contradict its own FAQ.",
        "packs": "5 price points &times; 4 collections", "prices": "$1&ndash;$2,500",
        "odds": ("Full rarity table per pack, summing to 100%", "ok"),
        "ev": ("&ldquo;GROSS EV&rdquo; posted on every pack", "ok"),
        "ret": ("95% posted; bands imply more", ""),
        "buyback": ("100% of FMV, shown on the pack", "ok"),
        "cash": ("Yes &mdash; Coinflow or USDC; $10k per 7 days", "ok"),
        "valuer": ("LastPack; &sect;4.4 &ldquo;may not match published market values&rdquo;", "neg"),
        "clock": ("5 days, then auto-sold at the purchase-time FMV", "neg"),
        "operator": "Lotus Digital Inc., a Delaware corporation",
        "juris": ("United States &mdash; California law", "ok"),
        "age": ("18+, US phone and government ID", "ok"),
        "states": ("None published; may restrict any jurisdiction", ""),
    },
    {
        "slug": "courtyard", "name": "Courtyard", "path": "/platforms/courtyard/",
        "blurb": "Publishes an exact expected value on every pack &mdash; the strongest disclosure we have found.",
        "packs": "92", "prices": "$10&ndash;$5,000",
        "odds": ("Dollar-range odds, every pack", "ok"),
        "ev": ("Yes, exact, every pack", "ok"),
        "ret": ("95&ndash;96% posted", "ok"),
        "buyback": ("90% advertised, ~85% measured", ""),
        "cash": ("USDC, path unverified", ""),
        "valuer": ("Courtyard", "neg"),
        "clock": ("Indefinite, vaulted and insured", "ok"),
        "operator": "Courtyard", "juris": ("United States", "ok"),
        "age": ("18+", "ok"), "states": ("None published", ""),
    },
    {
        "slug": "packz", "name": "Packz", "path": "/platforms/packz/",
        "blurb": "Full published odds on every pack, built from a single template &mdash; but the buyback is credit.",
        "packs": "14", "prices": "$5&ndash;$1,000",
        "odds": ("Dollar-range odds, every pack", "ok"),
        "ev": ("No, but calculable", ""),
        "ret": ("~100% on $25+, our estimate", ""),
        "buyback": ("90%", ""),
        "cash": ("No &mdash; site credit, packs only", "neg"),
        "valuer": ("Packz", "neg"),
        "clock": ("Not stated", ""),
        "operator": "Packz", "juris": ("United States", "ok"),
        "age": ("18+", "ok"), "states": ("US only", ""),
    },
    {
        "slug": "saja", "name": "SAJA", "path": "/platforms/saja/",
        "blurb": "100% EV and a 100% buyback on third-party valuations &mdash; alongside terms that can void every transaction and forfeit your cards.",
        "packs": "Tiered, in-app", "prices": "$1&ndash;$1,000",
        "odds": ("Rarity rates published; no value ranges public", ""),
        "ev": ("&ldquo;PACK EV 100%&rdquo; claimed per pack", "ok"),
        "ret": ("100% claimed; not independently calculable", ""),
        "buyback": ("100% of value, 7-day window", "ok"),
        "cash": ("Yes &mdash; Stripe; deposits need 1&times; use first", "ok"),
        "valuer": ("<strong>Third-party market pricing services</strong>", "ok"),
        "clock": ("None on the vault; 7 days on the instant offer", "ok"),
        "operator": "Zodiac Games Company, Inc., a Delaware corporation",
        "juris": ("United States &mdash; Delaware law", "ok"),
        "age": ("18+, one account per person", "ok"),
        "states": ("None published; US-operated", ""),
    },
    {
        "slug": "holofoil", "name": "Holofoil", "path": "/platforms/holofoil/",
        "blurb": "Contractually commits to publishing pull rates, then makes shipping the card the only way value ever leaves.",
        "packs": "4 types", "prices": "$9.20&ndash;$26.26, dynamic",
        "odds": ("Per-card rates, required by &sect;5", "ok"),
        "ev": ("No, not calculable", ""),
        "ret": ("Not calculable", ""),
        "buyback": ("90% of Holofoil's estimated value", ""),
        "cash": ("No &mdash; credit &ldquo;cannot be withdrawn&rdquo; (&sect;4)", "neg"),
        "valuer": ("Holofoil; &sect;8 calls its determination &ldquo;final&rdquo;", "neg"),
        "clock": ("30 days, then converted to credit (&sect;10)", "neg"),
        "operator": "First Edition TCG LLC, an Oregon company",
        "juris": ("United States &mdash; Oregon law", "ok"),
        "age": ("18+ or local majority", "ok"),
        "states": ("US and Canada only", ""),
    },
    {
        "slug": "arena-club", "name": "Arena Club", "path": "/platforms/arena-club/",
        "blurb": "Every pull is a graded slab, with per-card odds but no card values attached.",
        "packs": "9 tiers &times; 9 categories", "prices": "$25&ndash;$5,000",
        "odds": ("Per-card hit rates, no values", ""),
        "ev": ("No, not calculable", "neg"),
        "ret": ("Not calculable", "neg"),
        "buyback": ("90%", ""),
        "cash": ("Yes &mdash; bank or debit via Stripe", "ok"),
        "valuer": ("Arena Club, which grades some cards itself", "neg"),
        "clock": ("Indefinite, vaulted", "ok"),
        "operator": "Arena Club", "juris": ("United States", "ok"),
        "age": ("18+", "ok"), "states": ("None published", ""),
    },
    {
        "slug": "poke-collect", "name": "Poke-Collect", "path": "/platforms/poke-collect/",
        "blurb": "A real card shop selling digital packs. The only vault that ships you the card instead of selling it.",
        "packs": "4", "prices": "$9.99&ndash;$38.99",
        "odds": ("Per-tier chances, on the web", "ok"),
        "ev": ("Not yet collected", ""),
        "ret": ("Not yet calculated", ""),
        "buyback": ("None on the pack", "neg"),
        "cash": ("Buylist only &mdash; credit or PayPal", ""),
        "valuer": ("Buylist, reviewed card by card", ""),
        "clock": ("1 year, then shipped to you free", "ok"),
        "operator": "Poke-Collect, Madison, Alabama", "juris": ("United States", "ok"),
        "age": ("None stated", "neg"), "states": ("US shipping only", ""),
    },
    {
        "slug": "underdog", "name": "Underdog Rips", "path": "/platforms/underdog/",
        "blurb": "A major fantasy operator entering rips on third-party rails that publish an EV, provable fairness and outsourced valuations.",
        "packs": "Not published", "prices": "&ldquo;Various price points&rdquo;",
        "odds": ("Claimed &ldquo;up front&rdquo;; we could not read figures", ""),
        "ev": ("Phygitals shows an EV per pack; unverified", ""),
        "ret": ("Not calculable", "neg"),
        "buyback": ("85% per Phygitals; Underdog states none", ""),
        "cash": ("USDC per Phygitals; unconfirmed on Underdog", ""),
        "valuer": ("Third-party pricing providers, unnamed", "ok"),
        "clock": ("3 days on Underdog; 30 min to 7 days on Phygitals", "neg"),
        "operator": "Underdog Sports, with Phygitals sourcing and vaulting",
        "juris": ("United States", "ok"),
        "age": ("Not established", ""),
        "states": ("&ldquo;Not available in all states&rdquo;; no list found", ""),
    },
    {
        "slug": "fanatics-instant-rips", "name": "Fanatics Instant Rips",
        "path": "/platforms/fanatics-instant-rips/",
        "blurb": "The largest brand here, and the only one using third-party card valuations.",
        "packs": "5 categories", "prices": "$10&ndash;$2,500",
        "odds": ("Checklist only, no pull rates", "neg"),
        "ev": ("No, not calculable", "neg"),
        "ret": ("Not calculable", "neg"),
        "buyback": ("90% advertised, 84.6% after fees", "neg"),
        "cash": ("No &mdash; Fanatics Live credit", "neg"),
        "valuer": ("Card Ladder, a third party", "ok"),
        "clock": ("Indefinite, free vaulting", "ok"),
        "operator": "Fanatics", "juris": ("United States", "ok"),
        "age": ("18+", "ok"), "states": ("None published", ""),
    },
    {
        "slug": "crown-rips", "name": "Crown Rips", "path": "/platforms/crown-rips/",
        "blurb": "A rip feature inside a sweepstakes casino, in closed beta. Lowest disclosed floor we have seen.",
        "packs": "10 reported", "prices": "$1&ndash;$2,500",
        "odds": ("Min and max value only", "neg"),
        "ev": ("No, not calculable", "neg"),
        "ret": ("Not calculable", "neg"),
        "buyback": ("100% claimed, unverified", ""),
        "cash": ("Unconfirmed", ""),
        "valuer": ("Crown Rips", "neg"),
        "clock": ("7 days, reportedly, then auto-sold", ""),
        "operator": "Crown Rips", "juris": ("United States", "ok"),
        "age": ("18+", "ok"), "states": ("None published", ""),
    },
    {
        "slug": "tilt-rips", "name": "Tilt Rips", "path": "/platforms/tilt-rips/",
        "blurb": "The largest catalogue and the least odds disclosure, with a good cash route attached.",
        "packs": "~60", "prices": "$0.10&ndash;$3,000",
        "odds": ("Top prizes only, no rates", "neg"),
        "ev": ("No, not calculable", "neg"),
        "ret": ("Not calculable", "neg"),
        "buyback": ("90%", ""),
        "cash": ("Yes &mdash; US dollars or crypto", "ok"),
        "valuer": ("&ldquo;Live market data,&rdquo; unnamed; cannot be disputed", "neg"),
        "clock": ("Indefinite, free vaulting", "ok"),
        "operator": "Tilt Rips", "juris": ("United States", "ok"),
        "age": ("18+", "ok"), "states": ("None published", ""),
    },
    {
        "slug": "pickem", "name": "Pickem", "path": "/platforms/pickem/",
        "blurb": "A rip product inside a social casino, with the shortest decision window in the category.",
        "packs": "Not published", "prices": "$1&ndash;$250",
        "odds": ("Per-card rates, in-app only", ""),
        "ev": ("No, not calculable", "neg"),
        "ret": ("Not calculable", "neg"),
        "buyback": ("90%, 100% on first pack", ""),
        "cash": ("Yes &mdash; bank card, $2,500 cap", "ok"),
        "valuer": ("Pickem's displayed FMV", "neg"),
        "clock": ("3 hours, then auto-sold", "neg"),
        "operator": "Pickem", "juris": ("United States", "ok"),
        "age": ("18+", "ok"),
        "states": ("Excludes MI, MN, MT, NV, WA", "ok"),
    },
    {
        "slug": "packed", "name": "Packed", "path": "/platforms/packed/",
        "blurb": "The only platform whose terms contractually oblige it to publish Value Band odds.",
        "packs": "21", "prices": "Not published",
        "odds": ("Required by its own terms; in-app only", ""),
        "ev": ("No, not calculable", "neg"),
        "ret": ("Not calculable", "neg"),
        "buyback": ("100%", "ok"),
        "cash": ("Yes &mdash; card, bank, PayPal, Venmo", "ok"),
        "valuer": ("Packed, semi-automated, locked at the pull", "neg"),
        "clock": ("1 day, then returned to Packed", "neg"),
        "operator": "Packed", "juris": ("United States", "ok"),
        "age": ("18+", "ok"), "states": ("None published", ""),
    },
    {
        "slug": "chalkboard", "name": "Chalkboard Pulls", "path": "/platforms/chalkboard/",
        "blurb": "The best-documented cash route here, on a valuation its terms call final and non-appealable.",
        "packs": "Not published", "prices": "Not published",
        "odds": ("Shown in-app before purchase", ""),
        "ev": ("No, not calculable", "neg"),
        "ret": ("Not calculable", "neg"),
        "buyback": ("100%", "ok"),
        "cash": ("Yes &mdash; ACH via Aeropay", "ok"),
        "valuer": ("Chalkboard, sole discretion, non-appealable", "neg"),
        "clock": ("24 hours, then auto-buyback", "neg"),
        "operator": "Taild Sports, Inc.", "juris": ("United States", "ok"),
        "age": ("18+", "ok"), "states": ("Not published", "neg"),
    },
    {
        "slug": "rip-station", "name": "Rip Station", "path": "/platforms/rip-station/",
        "blurb": "Built an expected-value page and left it empty. The lowest advertised buyback in the category, stated plainly.",
        "packs": "10 listed", "prices": "$25&ndash;$500",
        "odds": ("A page exists; every figure read unavailable", "neg"),
        "ev": ("&ldquo;Data unavailable &mdash; inventory not verified&rdquo;", "neg"),
        "ret": ("Not calculable", "neg"),
        "buyback": ("83% &mdash; the lowest advertised anywhere", "neg"),
        "cash": ("Unconfirmed; &ldquo;lands in your wallet&rdquo;", ""),
        "valuer": ("Rip Station, from recent market sales", ""),
        "clock": ("7 days from each rip", ""),
        "operator": "Byzantine Port Technologies Inc. (Panama), under Byzantion Inc. (Delaware)",
        "juris": ("Panama, under a Delaware parent", "neg"),
        "age": ("18+ or local majority", "ok"),
        "states": ("Sanctioned and prohibited jurisdictions only", ""),
    },
    {
        "slug": "fast-rips", "name": "Fast Rips", "path": "/platforms/fast-rips/",
        "blurb": "Advertises a 100% cash buyback its own Terms of Use do not describe.",
        "packs": "7", "prices": "Not published",
        "odds": ("None published anywhere", "neg"),
        "ev": ("No, not calculable", "neg"),
        "ret": ("Not calculable", "neg"),
        "buyback": ("100% advertised", ""),
        "cash": ("No per its terms &mdash; Platform Credit", "neg"),
        "valuer": ("Internal platform valuation", "neg"),
        "clock": ("Not stated", ""),
        "operator": "Fast Rips", "juris": ("United States", "ok"),
        "age": ("18+", "ok"), "states": ("None published", ""),
    },
    {
        "slug": "mintpull", "name": "MintPull", "path": "/platforms/mintpull/",
        "blurb": "A 100% FMV guarantee credited as pack credit, with withdrawals capped at $250 a week.",
        "packs": "Not published", "prices": "Not published",
        "odds": ("None published; terms warn distribution is unequal", "neg"),
        "ev": ("No, not calculable", "neg"),
        "ret": ("Not calculable", "neg"),
        "buyback": ("100% advertised, paid as pack credit", "neg"),
        "cash": ("Sale proceeds only, $250 per 7 days", "neg"),
        "valuer": ("&ldquo;Proprietary system,&rdquo; may not match market", "neg"),
        "clock": ("7 days, then auto-returned", ""),
        "operator": "Arcane Answers Studio Limited",
        "juris": ("Hong Kong", "neg"),
        "age": ("18+", "ok"), "states": ("Excludes Nevada", ""),
    },
    {
        "slug": "triumph", "name": "Rips by Triumph", "path": "/platforms/triumph/",
        "blurb": "The largest platform we track. Headlines a 100% buyback guarantee its own &sect;5.5 says it is under no obligation to offer.",
        "packs": "Not published", "prices": "Not published",
        "odds": ("None published; terms warn distribution is unequal", "neg"),
        "ev": ("No, not calculable", "neg"),
        "ret": ("Not calculable", "neg"),
        "buyback": ("100% of FMV claimed in the FAQ", ""),
        "cash": ("Yes &mdash; debit, bank, PayPal or Venmo", "ok"),
        "valuer": ("Triumph, &ldquo;proprietary&rdquo;; &ldquo;may not match published market values&rdquo;", "neg"),
        "clock": ("7 days, then auto-returned at the locked FMV", ""),
        "operator": "Triumph TCG, LLC; Google Play lists Triumph Labs, Inc., Claymont, DE",
        "juris": ("United States &mdash; Delaware law", "ok"),
        "age": ("18+ in the terms; store rating 17+", "ok"),
        "states": ("Excludes Nevada; 50/50 pack limited in IL, UT, NC", "ok"),
    },
    {
        "slug": "swishx", "name": "SwishX", "path": "/platforms/swishx/",
        "blurb": "Posts an expected value, the odds behind it and the card pool. The pack is worth what you paid; the exit costs 12&ndash;22%.",
        "packs": "20 listed, 5 collected", "prices": "$25&ndash;$500",
        "odds": ("Per-tier rates with target FMVs, on the web", "ok"),
        "ev": ("Yes, posted per pack, and it checks out", "ok"),
        "ret": ("101% posted; 88% sold back in 24h", "ok"),
        "buyback": ("85&ndash;90%, then 75&ndash;80%", ""),
        "cash": ("Yes &mdash; withdrawn via Stripe", "ok"),
        "valuer": ("SwishX, but target FMVs are published per tier", ""),
        "clock": ("24 hours at the top rate, then a lower one", "neg"),
        "operator": "Not named; &ldquo;Powered by Swish Breaks&rdquo;",
        "juris": ("United States", "ok"),
        "age": ("18+, one account each", "ok"),
        "states": ("None published", ""),
    },
    {
        "slug": "gotya", "name": "Gotya", "path": "/platforms/gotya/",
        "blurb": "Says each pack's expected value equals its price. We checked five packs and it does &mdash; then the clock is a 180-day dormancy clause.",
        "packs": "10 listed, 5 collected", "prices": "$15&ndash;$100",
        "odds": ("Value bands per pack, on the web, summing to 100%", "ok"),
        "ev": ("&ldquo;Average item value&rdquo; posted per pack", "ok"),
        "ret": ("~100.5% midpoint; ~90% round trip", "ok"),
        "buyback": ("90% standing offer", "ok"),
        "cash": ("Yes &mdash; Wallet, then bank at a $25 floor", "ok"),
        "valuer": ("Gotya, &ldquo;good-faith internal estimate&rdquo;; no dispute route (&sect;24)", "neg"),
        "clock": ("None, but 180 days idle converts cards to credit", ""),
        "operator": "VBR GROUP LLP (London) with Gotya Collect LLC (Wyoming)",
        "juris": ("England and Wales", "neg"),
        "age": ("18+", "ok"),
        "states": ("None; sanctions jurisdictions only", ""),
    },
    {
        "slug": "catchback", "name": "CatchBack", "path": "/platforms/catchback/",
        "blurb": "Publishes the odds, the EV and the whole card pool &mdash; then sells you two side bets on the result.",
        "packs": "10 levels &times; 6 categories", "prices": "$5&ndash;$500+",
        "odds": ("Bands plus the full card pool, on the web", "ok"),
        "ev": ("Posted, but 7% above its own bands", ""),
        "ret": ("97.2% midpoint; $26.00 posted on $25", ""),
        "buyback": ("90%, or 110% with a paid Boost", ""),
        "cash": ("Not confirmed &mdash; terms unreachable", ""),
        "valuer": ("CatchBack, but the pool and its values are published", ""),
        "clock": ("5 minutes on both paid add-ons", "neg"),
        "operator": "Not established; terms hosted on a third-party docs subdomain",
        "juris": ("Not established", ""),
        "age": ("Not established", ""),
        "states": ("None published", ""),
    },
    {
        "slug": "rare-candy", "name": "Rare Candy", "path": "/platforms/rare-candy/",
        "blurb": "Publishes value-band odds and a guaranteed 50% floor on every pack &mdash; and pays in a currency with no cash value.",
        "packs": "8 collected", "prices": "$4.99&ndash;$499.99",
        "odds": ("Value-band rates, every pack, on the web", "ok"),
        "ev": ("No, but calculable", ""),
        "ret": ("~98&ndash;123%, our estimate", ""),
        "buyback": ("Up to 90%, plus a 50% floor", ""),
        "cash": ("No &mdash; Candy has no cash value (&sect;8.1)", "neg"),
        "valuer": ("Rare Candy, sole discretion; calls it &ldquo;inherently subjective&rdquo;", "neg"),
        "clock": ("48 hours, then you keep the card", "ok"),
        "operator": "Rare Candy Auctions, Inc., a Delaware corporation",
        "juris": ("United States &mdash; Texas law", "ok"),
        "age": ("18+", "ok"), "states": ("Excludes Washington", "ok"),
    },
    {
        "slug": "letsgo", "name": "LETSGO", "path": "/platforms/letsgo/",
        "blurb": "The buyback is described as 90% on the website and &ldquo;up to 90%&rdquo; on the App Store.",
        "packs": "Not published", "prices": "Not published",
        "odds": ("In-app only, nothing on the web", "neg"),
        "ev": ("No, not calculable", "neg"),
        "ret": ("Not calculable", "neg"),
        "buyback": ("90%, or &ldquo;up to&rdquo; 90%", "neg"),
        "cash": ("Yes &mdash; PayPal, Venmo, card, bank", "ok"),
        "valuer": ("Not stated anywhere we could reach", "neg"),
        "clock": ("No limit stated", ""),
        "operator": "LETSGO INTERACTIVE LTD, not named on its own site",
        "juris": ("Israel", "neg"),
        "age": ("18+", "ok"),
        "states": ("None; warns it &ldquo;may be illegal&rdquo; where you are", "neg"),
    },
]

# Row order and labels for the comparison tool.
COMPARE_ROWS = [
    ("packs", "Packs measured"),
    ("prices", "Price range"),
    ("odds", "Odds published"),
    ("ev", "Expected value"),
    ("ret", "Return"),
    ("buyback", "Buyback rate"),
    ("cash", "Can the money leave"),
    ("valuer", "Who sets the card's value"),
    ("clock", "How long you can hold a card"),
    ("operator", "Operator"),
    ("juris", "Jurisdiction"),
    ("age", "Age requirement"),
    ("states", "State restrictions"),
]


# ------------------------------------------------------------- Rare Candy
# Instapacks. Collected from packs.rarecandy.com on 2026-10-22. Unusually,
# the bands are stated as TOTAL PACK VALUE rather than per card, and every
# pack publishes a guaranteed floor paid in Candy if you exchange the whole
# pack. 100 Candy = $1, confirmed on every pack page.
# (name, price, guaranteed_candy, [(label, lo, hi, probability_pct)])
RARECANDY_PACKS = [
    ("Deep Blue", 4.99, 250, [
        ("Common", 1, 5, 59.8), ("Uncommon", 5, 7, 22.1),
        ("Rare", 7, 8, 5.3), ("Epic", 8, 10, 10.9),
        ("Legendary", 10, 112, 1.9)]),
    ("Wings &amp; Flames Chase", 9.99, 500, [
        ("Common", 5, 8, 49.6), ("Uncommon", 8, 15, 35.2),
        ("Rare", 15, 16, 5.0), ("Epic", 16, 17, 6.6),
        ("Legendary", 17, 236, 3.6)]),
    ("Single Strike: Iconic Legends", 24.99, 1250, [
        ("Common", 9, 22, 55.9), ("Uncommon", 22, 33, 28.8),
        ("Rare", 33, 39, 8.5), ("Epic", 39, 49, 5.3),
        ("Legendary", 49, 720, 1.5)]),
    ("Single Strike: Fan Favorites", 49.99, 2500, [
        ("Common", 20, 52, 59.9), ("Uncommon", 52, 70, 24.5),
        ("Rare", 70, 74, 7.2), ("Epic", 74, 133, 6.7),
        ("Legendary", 133, 1435, 1.7)]),
    ("Boosted Pack: Iconic Pokemon", 49.99, 2500, [
        ("Common", 28, 59, 59.5), ("Uncommon", 59, 74, 25.1),
        ("Rare", 74, 83, 8.7), ("Epic", 83, 88, 4.8),
        ("Legendary", 88, 2251, 1.9)]),
    ("Single Strike: Collector's Passport", 99.99, 5000, [
        ("Common", 35, 89, 59.9), ("Uncommon", 89, 166, 24.4),
        ("Rare", 166, 202, 8.3), ("Epic", 202, 229, 5.9),
        ("Legendary", 229, 3860, 1.5)]),
    ("Single Strike: Modern Collector Gallery", 249.99, 12500, [
        ("Common", 100, 255, 60.0), ("Uncommon", 255, 322, 24.9),
        ("Rare", 322, 358, 7.0), ("Epic", 358, 796, 6.6),
        ("Legendary", 796, 4736, 1.5)]),
    ("Only Slabs: Vintage &amp; Gold Star Chase", 499.99, 25000, [
        ("Common", 175, 325, 60.0), ("Uncommon", 325, 677, 24.9),
        ("Rare", 677, 892, 8.5), ("Epic", 892, 1554, 5.1),
        ("Legendary", 1554, 16416, 1.5)]),
]

# The exchange pays "up to 90%" of FMV, and only in Candy, which section 8.1
# of the terms says has no cash value.
RC_EXCHANGE = 0.90
RC_CANDY_PER_DOLLAR = 100


def rarecandy_rows():
    """Midpoint, floor and ceiling EV for every Instapack."""
    out = []
    for name, price, guar, bands in RARECANDY_PACKS:
        mid = sum((lo + hi) / 2.0 * p / 100.0 for _l, lo, hi, p in bands)
        low = sum(lo * p / 100.0 for _l, lo, hi, p in bands)
        high = sum(hi * p / 100.0 for _l, lo, hi, p in bands)
        psum = sum(p for _l, _lo, _hi, p in bands)
        out.append({
            "name": name, "price": price, "bands": bands,
            "guar": guar, "guar_usd": guar / float(RC_CANDY_PER_DOLLAR),
            "mid": mid, "low": low, "high": high, "psum": psum,
            "ratio_mid": mid / price, "ratio_low": low / price,
            "ratio_high": high / price,
            # What the midpoint is worth once exchanged, in Candy, at 90%.
            "candy_mid": mid * RC_EXCHANGE / price,
            "floor_ratio": (guar / float(RC_CANDY_PER_DOLLAR)) / price,
        })
    return out


def rarecandy_stats():
    rows = rarecandy_rows()
    n = len(rows)
    return {
        "n": n,
        "mid_avg": sum(r["ratio_mid"] for r in rows) / n,
        "low_avg": sum(r["ratio_low"] for r in rows) / n,
        "high_avg": sum(r["ratio_high"] for r in rows) / n,
        "candy_avg": sum(r["candy_mid"] for r in rows) / n,
        "floor_avg": sum(r["floor_ratio"] for r in rows) / n,
        "min_price": min(r["price"] for r in rows),
        "max_price": max(r["price"] for r in rows),
        "legendary_min": min(b[3] for r in rows for b in r["bands"]
                             if b[0] == "Legendary"),
        "legendary_max": max(b[3] for r in rows for b in r["bands"]
                             if b[0] == "Legendary"),
    }


# ---------------------------------------------------------------- SwishX
# Collected from swishx.co on 2026-10-22. SwishX posts an expected value on
# every pack, publishes per-tier odds with an explicit target FMV, names the
# card pool, and states a buyback rate band. Its FAQ says packs are "designed
# to a 100% value target."
# (name, price, stated_ev, [(tier, fmv_lo, fmv_hi, target, odds_pct)])
SWISHX_PACKS = [
    ("Multi Bronze", 25.00, 24.84, [
        ("X Factor", 1700, 2000, 1875, 0.04),
        ("Legendary", 100, 125, 125, 1.0),
        ("Epic", 35, 60, 47.50, 5.0),
        ("Prime", 25, 40, 30, 44.0),
        ("Core Collection", 10, 20, 15, 50.0)]),
    ("Multi Perfect 10", 50.00, 51.20, [
        ("X Factor", 2700, 3300, 3000, 0.04),
        ("Legendary", 700, 900, 800, 0.10),
        ("Epic", 150, 200, 175, 3.5),
        ("Prime", 58, 85, 70, 30.0),
        ("Core Collection", 28, 40, 33.50, 67.0)]),
    ("Multi Gold", 100.00, 102.32, [
        ("X Factor", 7125, 7875, 7500, 0.04),
        ("Legendary", 400, 500, 450, 1.0),
        ("Epic", 160, 250, 200, 10.0),
        ("Prime", 120, 150, 130, 30.0),
        ("Core Collection", 57, 63, 60, 59.0)]),
    ("Multi Platinum", 250.00, 250.62, [
        ("X Factor", 9500, 13000, 12500, 0.02),
        ("Legendary", 4500, 5500, 5000, 0.05),
        ("Epic", 688.75, 761.25, 725, 5.0),
        ("Prime", 332.50, 367.50, 350, 25.0),
        ("Core Collection", 166.25, 183.75, 175, 70.0)]),
    ("Multi Sapphire", 500.00, 505.68, [
        ("X Factor", 20000, 30000, 25000, 0.01),
        ("Legendary", 9500, 10500, 10000, 0.05),
        ("Epic", 1425, 1575, 1500, 5.0),
        ("Prime", 665, 735, 700, 25.0),
        ("Core Collection", 332.50, 367.50, 350, 70.0)]),
]

# Published buyback bands, from the SwishX FAQ.
SWISHX_BUYBACK_FAST = (0.85, 0.90)   # within the 24-hour window
SWISHX_BUYBACK_SLOW = (0.75, 0.80)   # on a re-quote afterwards


def swishx_rows():
    """Posted EV against the price, and what a full sell-back nets."""
    out = []
    for name, price, stated, tiers in SWISHX_PACKS:
        psum = sum(t[4] for t in tiers)
        calc = sum(t[3] * t[4] / 100.0 for t in tiers)
        # Odds are published rounded; normalising makes calc comparable.
        norm = calc / (psum / 100.0)
        out.append({
            "name": name, "price": price, "stated": stated, "tiers": tiers,
            "psum": psum, "calc": calc, "norm": norm,
            "posted_ratio": stated / price,
            "calc_ratio": norm / price,
            "fast_lo": stated * SWISHX_BUYBACK_FAST[0] / price,
            "fast_hi": stated * SWISHX_BUYBACK_FAST[1] / price,
            "slow_lo": stated * SWISHX_BUYBACK_SLOW[0] / price,
            "slow_hi": stated * SWISHX_BUYBACK_SLOW[1] / price,
        })
    return out


def swishx_stats():
    rows = swishx_rows()
    n = len(rows)
    return {
        "n": n,
        "posted_avg": sum(r["posted_ratio"] for r in rows) / n,
        "calc_avg": sum(r["calc_ratio"] for r in rows) / n,
        "fast_avg": sum((r["fast_lo"] + r["fast_hi"]) / 2 for r in rows) / n,
        "slow_avg": sum((r["slow_lo"] + r["slow_hi"]) / 2 for r in rows) / n,
        "max_oversum": max(r["psum"] for r in rows),
        "min_oversum": min(r["psum"] for r in rows),
        "min_price": min(r["price"] for r in rows),
        "max_price": max(r["price"] for r in rows),
        "max_gap": max(abs(r["stated"] - r["norm"]) / r["price"] for r in rows),
    }


# ----------------------------------------------------------------- Gotya
# Collected from gotya.com on 2026-10-22. Gotya states "each pack's expected
# value equals its price" and publishes a value-band table plus an "Average
# item value" on every pack page. Bands are stated per card (one card per
# pack). Odds are recalculated from live vault inventory, so they move.
# (name, price, stated_avg, [(lo, hi, odds_pct)])
GOTYA_PACKS = [
    ("Free $10 Pack", 10.00, 10.00, [
        (3, 5, 42.7), (6, 10, 40.0), (12, 24, 13.2),
        (32, 60, 4.0), (80, 200, 0.10)]),
    ("Pok&eacute;mon Rookie Pack", 15.00, 15.00, [
        (11, 13, 47.0), (13, 15, 40.8), (15, 30, 10.0),
        (30, 60, 2.0), (60, 240, 0.20)]),
    ("Pok&eacute;mon Trainer Pack", 25.00, 25.00, [
        (17, 21, 40.0), (21, 25, 39.0), (25, 50, 17.8),
        (50, 100, 3.0), (100, 400, 0.20)]),
    ("Football Trainer Pack", 25.00, 25.00, [
        (18, 21, 40.0), (21, 25, 37.9), (25, 50, 20.0),
        (50, 100, 2.0), (100, 400, 0.10)]),
    ("Pok&eacute;mon Elite Pack", 50.00, 50.00, [
        (35, 45, 58.0), (45, 50, 21.3), (50, 100, 17.5),
        (100, 200, 3.0), (200, 800, 0.20)]),
]

GOTYA_BUYBACK = 0.90


def gotya_rows():
    out = []
    for name, price, stated, bands in GOTYA_PACKS:
        mid = sum((lo + hi) / 2.0 * p / 100.0 for lo, hi, p in bands)
        low = sum(lo * p / 100.0 for lo, hi, p in bands)
        high = sum(hi * p / 100.0 for lo, hi, p in bands)
        psum = sum(p for _lo, _hi, p in bands)
        out.append({
            "name": name, "price": price, "stated": stated, "bands": bands,
            "mid": mid, "low": low, "high": high, "psum": psum,
            "ratio_mid": mid / price, "ratio_low": low / price,
            "ratio_high": high / price,
            "vs_claim": mid / stated,
            "round_trip": mid * GOTYA_BUYBACK / price,
        })
    return out


def gotya_stats():
    rows = gotya_rows()
    n = len(rows)
    paid = [r for r in rows if not r["name"].startswith("Free")]
    return {
        "n": n, "n_paid": len(paid),
        "mid_avg": sum(r["ratio_mid"] for r in rows) / n,
        "paid_avg": sum(r["ratio_mid"] for r in paid) / len(paid),
        "free_ratio": [r["ratio_mid"] for r in rows if r["name"].startswith("Free")][0],
        "trip_avg": sum(r["round_trip"] for r in rows) / n,
        "all_sum_100": all(abs(r["psum"] - 100.0) < 0.05 for r in rows),
        "min_price": min(r["price"] for r in rows),
        "max_price": max(r["price"] for r in rows),
    }


# -------------------------------------------------------------- CatchBack
# Collected from the live catchbackcards.com pack builder on 2026-10-22:
# $25 Base Pack, Pokemon category, Standard risk. CatchBack posts an expected
# value, publishes value-band odds AND the full available-hits pool with
# per-tier values. It also sells two optional side bets on top of the pack.
CATCHBACK_PACK = {
    "name": "Base Pack", "category": "Pokemon", "risk": "Standard",
    "price": 25.00, "posted_ev": 26.00, "buyback": 0.90,
    "bands": [(5, 25, 72.00), (25, 50, 23.17), (50, 100, 3.57),
              (100, 200, 1.02), (200, 300, 0.24)],
    # Observed pool, lowest and highest value seen in each tier.
    "pool": [("Legendary", 206, 298), ("Epic", 101, 200), ("Rare", 51, 98),
             ("Uncommon", 25, 50), ("Starter", 8, 21)],
}

# The two paid add-ons, both priced at $3.75 on a $25 pack.
CATCHBACK_ADDONS = {
    "boost": {"cost": 3.75, "rate": 1.10, "base": 0.90, "window_min": 5},
    "insurance": {"cost": 3.75, "floor_pct": 0.70, "window_min": 5},
}


def catchback_stats():
    p = CATCHBACK_PACK
    bands = p["bands"]
    mid = sum((lo + hi) / 2.0 * q / 100.0 for lo, hi, q in bands)
    low = sum(lo * q / 100.0 for lo, hi, q in bands)
    high = sum(hi * q / 100.0 for lo, hi, q in bands)
    psum = sum(q for _lo, _hi, q in bands)

    b = CATCHBACK_ADDONS["boost"]
    # Boost lifts the buyback from 90% to 110%: +20 points of card value.
    uplift = b["rate"] - b["base"]
    boost_breakeven = b["cost"] / uplift

    i = CATCHBACK_ADDONS["insurance"]
    floor_usd = p["price"] * i["floor_pct"]
    # Insurance only pays when 90% of the card's value falls under the floor.
    ins_threshold = floor_usd / p["buyback"]
    starter_lo = [t[1] for t in p["pool"] if t[0] == "Starter"][0]
    ins_max_payout = floor_usd - starter_lo * p["buyback"]

    return {
        "price": p["price"], "posted": p["posted_ev"],
        "mid": mid, "low": low, "high": high, "psum": psum,
        "posted_ratio": p["posted_ev"] / p["price"],
        "mid_ratio": mid / p["price"],
        "gap": (p["posted_ev"] - mid) / mid,
        "trip_posted": p["posted_ev"] * p["buyback"] / p["price"],
        "trip_mid": mid * p["buyback"] / p["price"],
        "addon_cost": b["cost"], "addon_pct": b["cost"] / p["price"],
        "both_pct": (b["cost"] + i["cost"]) / p["price"],
        "boost_breakeven": boost_breakeven,
        "ins_floor": floor_usd, "ins_threshold": ins_threshold,
        "ins_max_payout": ins_max_payout,
        "bottom_share": bands[0][2],
    }


# -------------------------------------------------------------- LastPack
# Collected from the live lastpack.com pack builder on 2026-10-23. Each pack
# page displays a sell-back rate, min and max value, a "GROSS EV" figure and
# a full rarity table. A volatility selector (Steady / Balanced / Wild)
# changes the distribution; the posted GROSS EV stayed 95% on both.
LASTPACK_PACKS = [
    {"name": "Iron Pack", "collection": "Riftbound", "vol": "Balanced",
     "price": 1.00, "gross_ev_pct": 95.0, "sellback": 1.00,
     "min_val": 0.50, "max_val": 122.25,
     "bands": [("Common", 0.50, 0.70, 30.0), ("Uncommon", 0.70, 1.00, 45.0),
               ("Rare", 1.00, 1.50, 16.3), ("Epic", 1.50, 3.00, 6.0),
               ("Mythic", 3.00, 8.00, 2.2), ("Grail", 8.00, 122.25, 0.5)]},
    {"name": "Noobie Pack", "collection": "Pok&eacute;mon", "vol": "Steady",
     "price": 1.00, "gross_ev_pct": 95.0, "sellback": 1.00,
     "min_val": 0.70, "max_val": 500.00,
     "bands": [("Common", 0.70, 0.70, 0.0), ("Uncommon", 0.70, 1.00, 70.0),
               ("Rare", 1.00, 1.50, 22.0), ("Epic", 1.50, 3.00, 6.0),
               ("Mythic", 3.00, 8.00, 1.9), ("Grail", 8.00, 500.00, 0.1)]},
]


def lastpack_rows():
    out = []
    for p in LASTPACK_PACKS:
        bands = p["bands"]
        mid = sum((lo + hi) / 2.0 * q / 100.0 for _l, lo, hi, q in bands)
        # Top band is enormously wide; value it at its floor as a sanity check.
        topfloor = sum(((lo + hi) / 2.0 if lab != "Grail" else lo) * q / 100.0
                       for lab, lo, hi, q in bands)
        psum = sum(q for _l, _lo, _hi, q in bands)
        grail = [b for b in bands if b[0] == "Grail"][0]
        out.append(dict(p, mid=mid, topfloor=topfloor, psum=psum,
                        ratio_mid=mid / p["price"],
                        ratio_topfloor=topfloor / p["price"],
                        posted_ratio=p["gross_ev_pct"] / 100.0,
                        grail_width=grail[2] / grail[1],
                        grail_pct=grail[3]))
    return out


def lastpack_stats():
    rows = lastpack_rows()
    n = len(rows)
    return {
        "n": n,
        "posted": rows[0]["gross_ev_pct"],
        "all_same_ev": len({r["gross_ev_pct"] for r in rows}) == 1,
        "all_sum_100": all(abs(r["psum"] - 100.0) < 0.05 for r in rows),
        "mid_avg": sum(r["ratio_mid"] for r in rows) / n,
        "topfloor_avg": sum(r["ratio_topfloor"] for r in rows) / n,
        "sellback": rows[0]["sellback"],
        "max_grail_width": max(r["grail_width"] for r in rows),
    }
