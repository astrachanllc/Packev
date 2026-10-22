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
    "cash": ("Cash-out verified", "pos",
             "Buyback proceeds reach a bank account, card or wallet you control"),
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
CHANGELOG = [
    ("2026-10-22", "Rips by Triumph added &mdash; and its terms match MintPull's, clause for clause",
     "The largest platform we track, at 1M+ installs. Its FAQ headlines a "
     "&ldquo;100% BUYBACK GUARANTEE&rdquo;; &sect;5.5 of its terms says "
     "Triumph &ldquo;is under no obligation to&rdquo; offer a Return. Its "
     "&sect;5.2&ndash;5.5 share capitalised sentences and section numbering "
     "with MintPull's, verbatim.",
     "/platforms/triumph/"),
    ("2026-10-22", "SwishX added &mdash; the most complete disclosure we have found",
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
