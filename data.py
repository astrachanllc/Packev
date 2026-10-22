"""Load and compute pack EV data from the collected odds CSVs."""
import csv
from collections import OrderedDict

COLLECTED = "2026-09-21"
UPDATED = "2026-10-21"

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
