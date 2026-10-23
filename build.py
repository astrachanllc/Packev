#!/usr/bin/env python3
"""Build the static PackEV site. Every table is rendered into the HTML here,
so crawlers that do not run JavaScript still see the numbers."""
import os
import shutil
from collections import Counter

from data import (load_courtyard, load_packz, ARENA_CLUB_PACKS, BUYBACK_TERMS,
                  FLAGS, PLATFORM_FLAGS, STATE_RESTRICTIONS, CHANGELOG,
                  CROWN_RIPS_PACKS, CLUTCH_PACKS, CLUTCH_BAND_LABELS,
                  CLUTCH_COLLECTED, clutch_stats, PLATFORMS, COMPARE_ROWS,
                  RARECANDY_PACKS, rarecandy_rows, rarecandy_stats,
                  SWISHX_PACKS, swishx_rows, swishx_stats,
                  GOTYA_PACKS, gotya_rows, gotya_stats, GOTYA_BUYBACK,
                  CATCHBACK_PACK, CATCHBACK_ADDONS, catchback_stats,
                  LASTPACK_PACKS, lastpack_rows, lastpack_stats,
                  SAJA_PACK, saja_stats, SAJA_COLLECTED,
                  money, pct, COLLECTED, UPDATED)
from layout import page, faq_block, jsonld, BASE_URL, SITE_NAME, E

OUT = "site"
INDEXNOW_KEY = "0e70e4ee2f9418e242c9b285c48147ff"
CY = load_courtyard()
PZ = load_packz()

# ---------------------------------------------------------------- stats
cy_ratios = Counter(round(p["ev_ratio"], 4) for p in CY if p["ev_ratio"])
CY_N = len(CY)
CY_AT_95 = cy_ratios[0.95]
CY_MIN_PRICE = min(p["price"] for p in CY)
CY_MAX_PRICE = max(p["price"] for p in CY)
CY_HIT_LO = min(p["at_or_above"] for p in CY)
CY_HIT_HI = max(p["at_or_above"] for p in CY)

PZ_N = len(PZ)
pz_std = [p for p in PZ if p["price"] >= 25]
PZ_STD_MID = sum(p["ratio_mid"] for p in pz_std) / len(pz_std)
PZ_COMMON = next(p for p in PZ if p["price"] == 5)
PZ_UNCOMMON = next(p for p in PZ if p["price"] == 10)
PZ_HIT = pz_std[0]["at_or_above"]

CL = clutch_stats()

# ---------------------------------------------------------------- affiliates
# Outbound links we earn from. `offer` describes what the READER gets; `we_get`
# describes what we get, and is shown to the reader too. Leave a platform out
# entirely rather than linking without terms.
AFFILIATE = {
    "packz": {
        "name": "Packz",
        "url": "https://packz.io/?ref=BMMI93WM",
        "kind": "referral link",
        "offer": "a scratch card worth either $7 or $100 in bonus funds after "
                 "your first pack purchase, which pays out automatically "
                 "within 48 hours if you don't scratch it",
        "we_get": "the same scratch card",
    },
    "packed": {
        "name": "Packed",
        "url": "https://playpacked.onelink.me/vPDF/MM44FA",
        "code": "MM44FA",
        "kind": "referral code",
        "offer": "free packs on signup, per Packed's own wording",
        "we_get": "a referral credit when you sign up and buy",
    },
}


def affiliate_cta(key):
    """Render a disclosed outbound link, or nothing if we have no deal."""
    a = AFFILIATE.get(key)
    if not a:
        return ""
    code = ('<p class="small">Code: <code>%s</code></p>' % E(a["code"])
            if a.get("code") else "")
    return (
        '<div class="affiliate">'
        '<p><strong>Signing up with our %s:</strong> %s gives you %s. '
        'We get %s, which is why this is marked as a %s and not a '
        'recommendation.</p>'
        '%s'
        '<p class="small muted">Using it costs you nothing extra and changes '
        'nothing on this page. Read the findings above before you decide &mdash; '
        'we would rather you skip the link than buy a pack you regret.</p>'
        '<p><a class="btn primary" href="%s" rel="sponsored nofollow noopener" '
        'target="_blank">Visit %s</a></p>'
        '</div>' % (E(a["kind"]), E(a["name"]), a["offer"], E(a["we_get"]),
                    E(a["kind"]), code, E(a["url"]), E(a["name"]))
    )


def pages_written(path, content):
    full = os.path.join(OUT, path.strip("/"), "index.html") if path != "/" \
        else os.path.join(OUT, "index.html")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


# ================================================================== tables
def courtyard_table():
    rows = []
    for p in CY:
        rows.append(
            '<tr data-cat="{cat}">'
            '<td class="name">{name}</td>'
            '<td>{cat}</td>'
            '<td class="num">{price}</td>'
            '<td class="num">{ev}</td>'
            '<td class="num"><strong>{ratio}</strong></td>'
            '<td class="num">{credit}</td>'
            '<td class="num">{hit}</td>'
            '<td class="num">{top}</td>'
            "</tr>".format(
                cat=E(p["category_label"]), name=E(p["name"]),
                price=money(p["price"]), ev=money(p["ev"]),
                ratio=pct(p["ev_ratio"] * 100, 0),
                credit=pct(p["credit_ratio"] * 100, 1),
                hit=pct(p["at_or_above"], 1), top=money(p["top"]),
            ))
    cats = sorted({p["category_label"] for p in CY})
    options = "".join('<option>%s</option>' % E(c) for c in cats)
    return """
<div class="filter-bar">
  <label for="cyFilter">Filter by category</label>
  <select id="cyFilter"><option value="">All categories ({n} packs)</option>{options}</select>
</div>
<div class="table-wrap">
<table id="cyTable">
<caption>Expected value as published by Courtyard, collected {collected}. "At 90% buyback" applies Courtyard's advertised instant-offer rate to the posted EV.</caption>
<thead><tr>
<th scope="col">Pack</th><th scope="col">Category</th><th scope="col" class="num">Price</th>
<th scope="col" class="num">Posted EV</th><th scope="col" class="num">Return</th>
<th scope="col" class="num">At 90% buyback</th>
<th scope="col" class="num">Chance of &ge; price</th><th scope="col" class="num">Top prize</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>
</div>
<script>
document.getElementById('cyFilter').addEventListener('change',function(e){{
  var v=e.target.value;
  document.querySelectorAll('#cyTable tbody tr').forEach(function(tr){{
    tr.hidden = !!v && tr.dataset.cat !== v;
  }});
}});
</script>
""".format(rows="".join(rows), options=options, n=CY_N, collected=COLLECTED)


def packz_table():
    rows = []
    for p in PZ:
        rows.append(
            '<tr><td class="name">{name}</td><td>{cat}</td>'
            '<td class="num">{price}</td><td class="num">{mid}</td>'
            '<td class="num"><strong>{ratio}</strong></td>'
            '<td class="num">{band}</td><td class="num">{credit}</td>'
            '<td class="num">{hit}</td></tr>'.format(
                name=E(p["name"]), cat=E(p["category_label"]),
                price=money(p["price"]), mid=money(p["ev_mid"]),
                ratio=pct(p["ratio_mid"] * 100, 0),
                band="%s&ndash;%s" % (pct(p["ratio_low"] * 100, 0).rstrip("%"),
                                      pct(p["ratio_high"] * 100, 0)),
                credit=pct(p["credit_ratio"] * 100, 0),
                hit=pct(p["at_or_above"], 1),
            ))
    return """
<div class="table-wrap">
<table>
<caption>Calculated from the odds Packz publishes on each pack page, collected {collected}. Packz shows value ranges rather than exact card values, so the headline figure assumes cards sit at the middle of their range and the band shows the full span.</caption>
<thead><tr>
<th scope="col">Pack</th><th scope="col">Category</th><th scope="col" class="num">Price</th>
<th scope="col" class="num">Avg. card value</th><th scope="col" class="num">Return</th>
<th scope="col" class="num">Possible range</th><th scope="col" class="num">As 90% credit</th>
<th scope="col" class="num">Chance of &ge; price</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>
</div>
""".format(rows="".join(rows), collected=COLLECTED)


# ================================================================== pages
def build_home():
    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Every card ripping site, one honest number.</h1>
    <p class="lede">Online pack ripping sites publish odds. They rarely publish the number that decides whether a pack is worth buying: how much of your money comes back, on average, per pack. We calculate it from each platform's own disclosures.</p>
  </div>

  <div class="finding">
    <p class="big">Clutch Packs publishes {clutchpulls} real pack openings verified on-chain, and they average {clutch:.2f} times the pack price &mdash; yet {clutchbelow} of those pulls came back worth less than the pack cost. Courtyard posts an expected value of 95% of the price on {cy95} of its {cyn} packs. Packz's published odds work out to about {pzstd}. Arena Club and Crown Rips publish no values at all.</p>
    <p class="small muted">Odds collected {collected}. These are the platforms' own figures and valuations, not independently verified sale prices.</p>
  </div>

  <div class="stats">
    <div class="stat"><b>{clutchpulls}</b><span>Real pulls analysed</span></div>
    <div class="stat"><b>{totpacks}</b><span>Packs measured across 5 platforms</span></div>
    <div class="stat"><b>95%</b><span>Courtyard's most common posted return</span></div>
    <div class="stat"><b class="neg">{clutchbelow}</b><span>Of real pulls worth less than the pack</span></div>
  </div>

  <h2>Transparency ranking</h2>
  <p>We rank on transparency first, because it is the one thing a buyer can verify before spending anything. A platform that publishes observed results is making the strongest claim available. One that publishes an expected value is making a checkable commitment. One that publishes only ranges, or per-card hit rates with no values, is not.</p>

  <div class="table-wrap">
  <table class="plain">
  <caption>Transparency ranking as of {collected2}. Full scored ratings follow once buyback terms and card valuations are verified.</caption>
  <thead><tr><th scope="col">#</th><th scope="col">Platform</th><th scope="col">What it discloses</th><th scope="col">Return</th><th scope="col">Buyback</th></tr></thead>
  <tbody>
    <tr><td class="num">1</td><td class="name"><a href="/platforms/clutch-packs/">Clutch Packs</a></td><td>Observed pull results, verified on-chain, plus a full 100-card pool per pack</td><td><strong>{clutch:.2f}&times;</strong> observed over {clutchpulls} pulls</td><td>Not disclosed</td></tr>
    <tr><td class="num">2</td><td class="name"><a href="/platforms/swishx/">SwishX</a></td><td>Posted expected value per pack, per-tier odds with target card values, the named card pool, and a published buyback band</td><td><strong>101%</strong> posted; ~88% sold back within 24h</td><td>85&ndash;90%, then 75&ndash;80%; withdrawable</td></tr>
    <tr><td class="num">3</td><td class="name"><a href="/platforms/lastpack/">LastPack</a></td><td>Sell-back rate, min/max value, a posted EV and a full rarity table on every pack, plus a per-pull fairness check</td><td><strong>95%</strong> posted; bands imply more</td><td>100% of FMV &mdash; though &sect;4.5 calls it pack credit</td></tr>
    <tr><td class="num">4</td><td class="name"><a href="/platforms/courtyard/">Courtyard</a></td><td>Exact expected value and dollar-range odds on every pack</td><td>95&ndash;96% claimed</td><td>90% advertised</td></tr>
    <tr><td class="num">5</td><td class="name"><a href="/platforms/gotya/">Gotya</a></td><td>Value bands on every pack page summing to exactly 100%, plus a stated average item value that reconciles with them</td><td><strong>~100.5%</strong> midpoint; ~90% round trip</td><td>90% standing offer, withdrawable to a bank</td></tr>
    <tr><td class="num">6</td><td class="name"><a href="/platforms/catchback/">CatchBack</a></td><td>Band odds summing to exactly 100%, a posted EV and the entire card pool with values &mdash; but nothing about the company</td><td>97.2% midpoint; $26.00 posted on a $25 pack</td><td>90%, or 110% with a paid add-on</td></tr>
    <tr><td class="num">7</td><td class="name"><a href="/platforms/rare-candy/">Rare Candy</a></td><td>Value-band pull rates on every pack, on the open web, plus a guaranteed 50% floor and named top hits</td><td>~98&ndash;123%, our estimate</td><td>Up to 90%, in Candy with no cash value</td></tr>
    <tr><td class="num">8</td><td class="name"><a href="/platforms/packz/">Packz</a></td><td>Dollar-range odds, no expected value</td><td>~{pzstd} on $25+ packs, our estimate</td><td>90%, site credit only</td></tr>
    <tr><td class="num">9</td><td class="name"><a href="/platforms/saja/">SAJA</a></td><td>Third-party card values, ownership at the pull, a free vault with no deadline, and a cash remedy when its own price is too high &mdash; but rarity percentages with no value ranges</td><td><strong>100%</strong> claimed; not calculable</td><td>100% of value, 7 days &mdash; and terms that can confiscate it</td></tr>
    <tr><td class="num">10</td><td class="name"><a href="/platforms/holofoil/">Holofoil</a></td><td>&sect;5 contractually requires pull rates on every product page, and they are there &mdash; per card, with values, but not joined up</td><td>Not calculable</td><td>90% in credit that &sect;4 says cannot be cashed out</td></tr>
    <tr><td class="num">11</td><td class="name"><a href="/platforms/arena-club/">Arena Club</a></td><td>Per-card hit rates, no card values, no expected value</td><td>Not calculable</td><td>90% of card value, withdrawable</td></tr>
    <tr><td class="num">12</td><td class="name"><a href="/platforms/poke-collect/">Poke-Collect</a></td><td>Per-tier pull chances and a card pool published on the web; render in-browser, not yet collected</td><td>Not yet calculated</td><td>None &mdash; a separate buylist pays store credit or PayPal</td></tr>
    <tr><td class="num">13</td><td class="name"><a href="/platforms/underdog/">Underdog Rips</a></td><td>Claims odds up front; the rate, payout form and valuation are documented by its supplier rather than by Underdog</td><td>Not calculable</td><td>None stated; 85% of FMV per Phygitals</td></tr>
    <tr><td class="num">14</td><td class="name"><a href="/platforms/fanatics-instant-rips/">Fanatics Instant Rips</a></td><td>Checklist of contents, no pull rates; third-party card valuations</td><td>Not calculable</td><td>84.6% effective, credit only</td></tr>
    <tr><td class="num">15</td><td class="name"><a href="/platforms/crown-rips/">Crown Rips</a></td><td>Minimum and maximum pull value only, no rates</td><td>Not calculable</td><td>100% claimed, unverified</td></tr>
    <tr><td class="num">16</td><td class="name"><a href="/platforms/tilt-rips/">Tilt Rips</a></td><td>Top prizes only, no rates and no floor</td><td>Not calculable</td><td>90%, withdrawable in cash or crypto</td></tr>
    <tr><td class="num">17</td><td class="name"><a href="/platforms/pickem/">Pickem</a></td><td>Per-card pull rates in-app only; nothing published on the web</td><td>Not calculable</td><td>90%, withdrawable &mdash; within a three-hour window</td></tr>
    <tr><td class="num">18</td><td class="name"><a href="/platforms/packed/">Packed</a></td><td>Terms require Value Band odds to be shown, but nothing is published on the web</td><td>Not calculable</td><td>100%, withdrawable &mdash; within a one-day window</td></tr>
    <tr><td class="num">19</td><td class="name"><a href="/platforms/chalkboard/">Chalkboard Pulls</a></td><td>Odds shown in-app before purchase, nothing on the web; terms warn distribution is likely unequal and odds change as packs sell</td><td>Not calculable</td><td>100%, withdrawable &mdash; on an FMV the terms call &ldquo;final and non-appealable&rdquo;</td></tr>
    <tr><td class="num">20</td><td class="name"><a href="/platforms/triumph/">Rips by Triumph</a></td><td>No prices or odds published; names its entity and its restricted states, and its clauses match MintPull&rsquo;s verbatim</td><td>Not calculable</td><td>&ldquo;100% guarantee&rdquo; in the FAQ; &sect;5.5 says no obligation</td></tr>
    <tr><td class="num">21</td><td class="name"><a href="/platforms/rip-station/">Rip Station</a></td><td>Publishes an EV page; every figure on it read &ldquo;Data unavailable&rdquo; the day we checked</td><td>Not calculable</td><td>83% &mdash; the lowest advertised, and the most plainly stated</td></tr>
    <tr><td class="num">22</td><td class="name"><a href="/platforms/fast-rips/">Fast Rips</a></td><td>No prices or odds published at all</td><td>Not calculable</td><td>100% advertised; terms say credit, non-withdrawable</td></tr>
    <tr><td class="num">23</td><td class="name"><a href="/platforms/mintpull/">MintPull</a></td><td>No prices or odds published; terms warn distribution is likely unequal</td><td>Not calculable</td><td>100% advertised; credited as pack credit, $250/week withdrawal cap</td></tr>
    <tr><td class="num">24</td><td class="name"><a href="/platforms/letsgo/">LETSGO</a></td><td>Nothing published on the web, no operating company named on its own site, and no terms of use we could reach</td><td>Not calculable</td><td>&ldquo;90%&rdquo; on the site, &ldquo;up to 90%&rdquo; on the App Store</td></tr>
  </tbody>
  </table>
  </div>

  <p class="small muted">Clutch Packs leads because observed results cannot be quietly adjusted by revaluing inventory. It is not yet scored, because it discloses no buyback terms and buyback is a quarter of the score.</p>

  <div class="card-grid">
    <article class="card">
      <span class="verdict">Most transparent</span>
      <h3>Clutch Packs</h3>
      <dl>
        <dt>Packs measured</dt><dd>{clutchpacks}</dd>
        <dt>Real pulls</dt><dd>{clutchpulls}</dd>
        <dt>Observed return</dt><dd>{clutch:.2f}&times;</dd>
        <dt>Pulls under 1&times;</dt><dd>{clutchbelow}</dd>
      </dl>
      <p>Records every opening on-chain and publishes the results. The average is near break-even; three quarters of individual pulls are not.</p>
      <p class="more"><a href="/platforms/clutch-packs/">The full pull data &rarr;</a></p>
    </article>

    <article class="card">
      <span class="verdict">Best published EV</span>
      <h3>Courtyard</h3>
      <dl>
        <dt>Packs measured</dt><dd>{cyn}</dd>
        <dt>Price range</dt><dd>{cymin}&ndash;{cymax}</dd>
        <dt>Posted return</dt><dd>95&ndash;96%</dd>
        <dt>Chance of &ge; price</dt><dd>{cyhitlo}&ndash;{cyhithi}</dd>
      </dl>
      <p>Publishes an exact expected value on every pack. Packs differ in shape, not in average return.</p>
      <p class="more"><a href="/platforms/courtyard/">All {cyn} Courtyard packs &rarr;</a></p>
    </article>

    <article class="card">
      <span class="verdict">Best stated return</span>
      <h3>Packz</h3>
      <dl>
        <dt>Packs measured</dt><dd>{pzn}</dd>
        <dt>Price range</dt><dd>$5&ndash;$1,000</dd>
        <dt>Estimated return</dt><dd>~{pzstd} ($25+)</dd>
        <dt>Chance of &ge; price</dt><dd>{pzhit}</dd>
      </dl>
      <p>Every pack uses one odds template. The headline return looks strong, but it rests on Packz's own valuations and the buyback pays in credit you cannot withdraw.</p>
      <p class="more"><a href="/platforms/packz/">All {pzn} Packz packs &rarr;</a></p>
    </article>

    <article class="card">
      <span class="verdict">Best buyback terms</span>
      <h3>Arena Club</h3>
      <dl>
        <dt>Price range</dt><dd>$25&ndash;$5,000</dd>
        <dt>Odds format</dt><dd>Per card</dd>
        <dt>Posted EV</dt><dd>None</dd>
        <dt>Buyback payout</dt><dd>Withdrawable</dd>
      </dl>
      <p>The only platform here whose buyback reaches a real bank account without further conditions, and the only one whose expected value you cannot work out from its own page.</p>
      <p class="more"><a href="/platforms/arena-club/">Arena Club breakdown &rarr;</a></p>
    </article>
  </div>

  <h2>Compare any platforms side by side</h2>
  <p>The <a href="/compare/">comparison tool</a> puts any two to four of the twenty-four platforms next to each other on the things that decide the outcome: whether odds are published, whether buyback money can leave the platform, who sets the card's value, and how long you can hold a card before the platform acts.</p>

  <h2>Work out any pack yourself</h2>
  <p>The <a href="/calculator/">pack EV calculator</a> takes the odds any site publishes and returns the average card value, the expected loss per pack, and the chance of beating the pack price. It is free, needs no account, and runs entirely in your browser.</p>

  <h2>Start here</h2>
  <ul>
    <li><a href="/guides/chase-card-odds/">The real odds of pulling the Cooper Flagg card</a> &mdash; 1 in 5,000, and what that costs.</li>
    <li><a href="/guides/bonus-offers/">Bonus offers ranked by what they're worth</a> &mdash; only one is plausibly positive-EV.</li>
    <li><a href="/guides/buyback-rates/">What a 90% buyback actually pays</a> &mdash; five sites say 90% and mean five different things.</li>
    <li><a href="/platforms/clutch-packs/">What 158,556 real pulls show</a> &mdash; the only observed return data in the category.</li>
    <li><a href="/compare/">Compare any platforms side by side</a> &mdash; pick two to four and see the terms that matter.</li>
    <li><a href="/compare/courtyard-vs-packz/">Courtyard vs Packz</a> &mdash; the two platforms that publish enough to compare directly.</li>
    <li><a href="/methodology/">How we rate platforms</a> &mdash; what goes into a score and what does not.</li>
    <li><a href="/is-card-ripping-gambling/">Is card ripping gambling?</a> &mdash; where the law currently stands.</li>
    <li><a href="/data/">Open data</a> &mdash; every odds table we have collected, as CSV.</li>
  </ul>
</div>
""".format(cyn=CY_N, cy95=CY_AT_95, pzn=PZ_N, collected=COLLECTED,
           collected2=CLUTCH_COLLECTED,
           pzstd=pct(PZ_STD_MID * 100, 0), pzhit=pct(PZ_HIT, 1),
           cymin=money(CY_MIN_PRICE), cymax=money(CY_MAX_PRICE),
           cyhitlo=pct(CY_HIT_LO, 0), cyhithi=pct(CY_HIT_HI, 0),
           clutch=CL["w_avg"], clutchpulls="{:,}".format(CL["pulls"]),
           clutchbelow=pct(CL["below_1x"], 0), clutchpacks=CL["n_packs"],
           totpacks=CY_N + PZ_N + CL["n_packs"] + len(CROWN_RIPS_PACKS))

    ld = [
        jsonld({
            "@context": "https://schema.org", "@type": "WebSite",
            "name": SITE_NAME, "url": BASE_URL,
            "description": "Independent expected-value analysis of online card ripping and digital pack opening platforms.",
        }),
        jsonld({
            "@context": "https://schema.org", "@type": "Organization",
            "name": SITE_NAME, "url": BASE_URL,
            "description": "Independent research on online card ripping platforms, based on each platform's published odds.",
        }),
    ]
    return pages_written("/", page(
        "/",
        "%s — %s" % (SITE_NAME, TAGLINE_FULL),
        "Independent expected-value analysis of online card ripping sites. Courtyard posts 95%% returns on most packs; Packz's published odds work out to about %s. Free pack EV calculator." % pct(PZ_STD_MID * 100, 0),
        body, updated=COLLECTED, structured=ld))


TAGLINE_FULL = "Card ripping sites rated by expected value"


def build_platforms_index():
    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Card ripping platforms</h1>
    <p class="lede">Every platform we cover, with what it discloses and what that works out to. Clutch Packs, Courtyard, Packz and Arena Club we collected first-hand; Crown Rips is in closed beta, so its figures are reported rather than collected. Platforms we have not measured at all are listed at the bottom. To put any of them side by side, use the <a href="/compare/">comparison tool</a>.</p>
  </div>

  <div class="card-grid">
    <article class="card">
      <h3><a href="/platforms/clutch-packs/">Clutch Packs</a></h3>
      {flag_clutch_packs}
      <dl>
        <dt>Packs</dt><dd>{clutchpacks}</dd>
        <dt>Prices</dt><dd>$25&ndash;$2,500</dd>
        <dt>Posted EV</dt><dd>Observed, on-chain</dd>
        <dt>Return</dt><dd>{clutch:.2f}&times; over {clutchpulls} pulls</dd>
        <dt>Buyback</dt><dd>Not disclosed</dd>
      </dl>
      <p>Multisport, Pok&eacute;mon, One Piece and soccer. The only platform publishing what buyers actually pulled rather than what it says its cards are worth.</p>
      <p class="more"><a href="/platforms/clutch-packs/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/courtyard/">Courtyard</a></h3>
      {flag_courtyard}
      <dl>
        <dt>Packs</dt><dd>{cyn}</dd>
        <dt>Prices</dt><dd>{cymin}&ndash;{cymax}</dd>
        <dt>Posted EV</dt><dd>Yes, exact</dd>
        <dt>Return</dt><dd>95&ndash;96%</dd>
        <dt>Buyback</dt><dd>90% advertised</dd>
      </dl>
      <p>Cards, comics, coins, watches and sneakers. Publishes an expected value on every pack, which is the strongest disclosure we have found anywhere.</p>
      <p class="more"><a href="/platforms/courtyard/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/packz/">Packz</a></h3>
      {flag_packz}
      <dl>
        <dt>Packs</dt><dd>{pzn}</dd>
        <dt>Prices</dt><dd>$5&ndash;$1,000</dd>
        <dt>Posted EV</dt><dd>No</dd>
        <dt>Return</dt><dd>~{pzstd} ($25+)</dd>
        <dt>Buyback</dt><dd>90%, credit only</dd>
      </dl>
      <p>Sports and Pok&eacute;mon, US only. Publishes dollar-range odds on every pack, all built from a single odds template.</p>
      <p class="more"><a href="/platforms/packz/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/arena-club/">Arena Club</a></h3>
      {flag_arena_club}
      <dl>
        <dt>Packs</dt><dd>9 tiers &times; 9 categories</dd>
        <dt>Prices</dt><dd>$25&ndash;$5,000</dd>
        <dt>Posted EV</dt><dd>No</dd>
        <dt>Return</dt><dd>Not calculable</dd>
        <dt>Buyback</dt><dd>90% of value, withdrawable</dd>
      </dl>
      <p>Every pull is a graded slab. Odds are listed card by card with no values attached, so the expected value cannot be worked out from the page.</p>
      <p class="more"><a href="/platforms/arena-club/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/crown-rips/">Crown Rips</a></h3>
      {flag_crown_rips}
      <dl>
        <dt>Packs</dt><dd>10 reported</dd>
        <dt>Prices</dt><dd>$1&ndash;$2,500</dd>
        <dt>Posted EV</dt><dd>No</dd>
        <dt>Return</dt><dd>Not calculable</dd>
        <dt>Buyback</dt><dd>100% claimed</dd>
      </dl>
      <p>A card ripping feature inside a sweepstakes casino, in closed beta. Publishes a minimum and maximum pull value per pack but no pull rates, and its disclosed floor is the lowest we have seen.</p>
      <p class="more"><a href="/platforms/crown-rips/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/fanatics-instant-rips/">Fanatics Instant Rips</a></h3>
      {flag_fanatics_instant_rips}
      <dl>
        <dt>Packs</dt><dd>5 categories</dd>
        <dt>Prices</dt><dd>$10&ndash;$2,500</dd>
        <dt>Posted EV</dt><dd>No</dd>
        <dt>Return</dt><dd>Not calculable</dd>
        <dt>Buyback</dt><dd>84.6% effective, credit</dd>
      </dl>
      <p>The largest brand in the category. Publishes a checklist but no pull rates, and the advertised 90% offer nets 84.6% after fees. Uses third-party card valuations, which no competitor does.</p>
      <p class="more"><a href="/platforms/fanatics-instant-rips/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/tilt-rips/">Tilt Rips</a></h3>
      {flag_tilt_rips}
      <dl>
        <dt>Packs</dt><dd>~60</dd>
        <dt>Prices</dt><dd>$0.10&ndash;$3,000</dd>
        <dt>Posted EV</dt><dd>No</dd>
        <dt>Return</dt><dd>Not calculable</dd>
        <dt>Buyback</dt><dd>90%, withdrawable</dd>
      </dl>
      <p>The largest catalogue and the least odds disclosure. Its sell-back is the best cash route we have verified, but the platform sets the valuation and says the price cannot be disputed.</p>
      <p class="more"><a href="/platforms/tilt-rips/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/pickem/">Pickem</a></h3>
      {flag_pickem}
      <dl>
        <dt>Packs</dt><dd>$1 &ndash; $250</dd>
        <dt>Odds shown</dt><dd>In-app, per card</dd>
        <dt>Posted EV</dt><dd>No</dd>
        <dt>Return</dt><dd>Not calculable</dd>
        <dt>Buyback</dt><dd>90%, withdrawable</dd>
      </dl>
      <p>A rip product inside a social casino. Pays 90% to a bank card, and gives you three hours from opening a pack before it sells the card for you.</p>
      <p class="more"><a href="/platforms/pickem/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/packed/">Packed</a></h3>
      {flag_packed}
      <dl>
        <dt>Packs</dt><dd>21, no prices shown</dd>
        <dt>Prices</dt><dd>Not published</dd>
        <dt>Posted EV</dt><dd>No</dd>
        <dt>Return</dt><dd>Not calculable</dd>
        <dt>Buyback</dt><dd>100%, withdrawable</dd>
      </dl>
      <p>The best cash terms we have verified and the shortest clock. Its terms require odds to be published and give you one day to hold a card before it is taken back.</p>
      <p class="more"><a href="/platforms/packed/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/mintpull/">MintPull</a></h3>
      {flag_mintpull}
      <dl>
        <dt>Packs</dt><dd>No prices shown</dd>
        <dt>Odds shown</dt><dd>None published</dd>
        <dt>Posted EV</dt><dd>No</dd>
        <dt>Return</dt><dd>Not calculable</dd>
        <dt>Buyback</dt><dd>100% as pack credit</dd>
      </dl>
      <p>Advertises a 100% FMV guarantee. Its terms credit returns as pack purchase credit, cap withdrawals at $250 per seven days, and are governed by Hong Kong law.</p>
      <p class="more"><a href="/platforms/mintpull/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/fast-rips/">Fast Rips</a></h3>
      {flag_fast_rips}
      <dl>
        <dt>Packs</dt><dd>7, no prices shown</dd>
        <dt>Prices</dt><dd>Not published</dd>
        <dt>Posted EV</dt><dd>No</dd>
        <dt>Return</dt><dd>Not calculable</dd>
        <dt>Buyback</dt><dd>100% advertised</dd>
      </dl>
      <p>Advertises a 100% buyback paid to your bank account. Its own Terms of Use say Platform Credit has no cash value outside the platform and is not withdrawable.</p>
      <p class="more"><a href="/platforms/fast-rips/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/chalkboard/">Chalkboard Pulls</a></h3>
      {flag_chalkboard}
      <dl>
        <dt>Packs</dt><dd>No prices shown</dd>
        <dt>Odds shown</dt><dd>In-app, pre-purchase</dd>
        <dt>Posted EV</dt><dd>No</dd>
        <dt>Return</dt><dd>Not calculable</dd>
        <dt>Buyback</dt><dd>100%, withdrawable</dd>
      </dl>
      <p>A rip product inside a fantasy sports app. The best-documented cash route we have read &mdash; and the only terms that call the platform's own valuation &ldquo;final and non-appealable.&rdquo;</p>
      <p class="more"><a href="/platforms/chalkboard/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/poke-collect/">Poke-Collect</a></h3>
      {flag_poke_collect}
      <dl>
        <dt>Packs</dt><dd>4 digital packs</dd>
        <dt>Prices</dt><dd>$9.99&ndash;$38.99</dd>
        <dt>Odds shown</dt><dd>Per tier, on the web</dd>
        <dt>Return</dt><dd>Not yet calculated</dd>
        <dt>Buyback</dt><dd>None on the pack</dd>
      </dl>
      <p>A real card shop in Alabama selling digital packs. The only platform here whose vault ships you the card for free at the end instead of selling it &mdash; and the only one with no instant buyback.</p>
      <p class="more"><a href="/platforms/poke-collect/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/letsgo/">LETSGO</a></h3>
      {flag_letsgo}
      <dl>
        <dt>Packs</dt><dd>No prices shown</dd>
        <dt>Odds shown</dt><dd>In-app only</dd>
        <dt>Posted EV</dt><dd>No</dd>
        <dt>Return</dt><dd>Not calculable</dd>
        <dt>Buyback</dt><dd>90%, or &ldquo;up to&rdquo; 90%</dd>
      </dl>
      <p>100,000+ installs and real graded slabs, but the buyback is described two different ways, no operating company is named on the site, and the homepage warns it may be illegal where you are.</p>
      <p class="more"><a href="/platforms/letsgo/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/rare-candy/">Rare Candy</a></h3>
      {flag_rare_candy}
      <dl>
        <dt>Packs</dt><dd>8 collected</dd>
        <dt>Prices</dt><dd>$4.99&ndash;$499.99</dd>
        <dt>Posted EV</dt><dd>No, but calculable</dd>
        <dt>Return</dt><dd>~98&ndash;123%, our estimate</dd>
        <dt>Buyback</dt><dd>Up to 90%, Candy only</dd>
      </dl>
      <p>Publishes full value-band odds and a guaranteed 50% floor on every pack &mdash; the best disclosure we have found since Courtyard. Pays in a currency its terms say has no cash value.</p>
      <p class="more"><a href="/platforms/rare-candy/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/swishx/">SwishX</a></h3>
      {flag_swishx}
      <dl>
        <dt>Packs</dt><dd>20 listed, 5 collected</dd>
        <dt>Prices</dt><dd>$25&ndash;$500</dd>
        <dt>Posted EV</dt><dd>Yes, and it checks out</dd>
        <dt>Return</dt><dd>101% posted, ~88% round trip</dd>
        <dt>Buyback</dt><dd>85&ndash;90%, withdrawable</dd>
      </dl>
      <p>The most complete disclosure we have found: posted EV, per-tier odds, target card values and the named pool. Packs carry no markup &mdash; the margin is in the buyback, and they say so.</p>
      <p class="more"><a href="/platforms/swishx/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/triumph/">Rips by Triumph</a></h3>
      {flag_triumph}
      <dl>
        <dt>Packs</dt><dd>No prices shown</dd>
        <dt>Odds shown</dt><dd>None published</dd>
        <dt>Posted EV</dt><dd>No</dd>
        <dt>Return</dt><dd>Not calculable</dd>
        <dt>Buyback</dt><dd>100% claimed, &sect;5.5 differs</dd>
      </dl>
      <p>The largest platform we track at 1M+ installs. Headlines a 100% buyback guarantee its own &sect;5.5 says it is under no obligation to offer &mdash; and its terms are MintPull&rsquo;s, clause for clause.</p>
      <p class="more"><a href="/platforms/triumph/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/gotya/">Gotya</a></h3>
      {flag_gotya}
      <dl>
        <dt>Packs</dt><dd>10 listed, 5 collected</dd>
        <dt>Prices</dt><dd>$15&ndash;$100</dd>
        <dt>Posted EV</dt><dd>Average item value, per pack</dd>
        <dt>Return</dt><dd>~100.5% midpoint</dd>
        <dt>Buyback</dt><dd>90%, withdrawable</dd>
      </dl>
      <p>Says each pack's expected value equals its price. We checked five packs and it holds &mdash; the best round trip we have measured. Governed by English law, with a 180-day dormancy clause.</p>
      <p class="more"><a href="/platforms/gotya/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/holofoil/">Holofoil</a></h3>
      {flag_holofoil}
      <dl>
        <dt>Packs</dt><dd>4 types, dynamic pricing</dd>
        <dt>Prices</dt><dd>$9.20&ndash;$26.26 observed</dd>
        <dt>Odds shown</dt><dd>Per card, required by &sect;5</dd>
        <dt>Return</dt><dd>Not calculable</dd>
        <dt>Buyback</dt><dd>90%, credit only</dd>
      </dl>
      <p>Binds itself to publish pull rates, admits packs usually lose money, and then closes the exit: &sect;4 says credit can never be cashed out, and &sect;10 converts vaulted cards to it after 30 days.</p>
      <p class="more"><a href="/platforms/holofoil/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/catchback/">CatchBack</a></h3>
      {flag_catchback}
      <dl>
        <dt>Packs</dt><dd>10 levels &times; 6 categories</dd>
        <dt>Prices</dt><dd>$5&ndash;$500+</dd>
        <dt>Posted EV</dt><dd>$26.00 on a $25 pack</dd>
        <dt>Return</dt><dd>97.2% from its own bands</dd>
        <dt>Buyback</dt><dd>90%, 110% with Boost</dd>
      </dl>
      <p>Publishes the odds, the EV and the whole card pool &mdash; then sells a Boost and an Insurance at $3.75 each, both expiring in five minutes. We priced both.</p>
      <p class="more"><a href="/platforms/catchback/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/rip-station/">Rip Station</a></h3>
      {flag_rip_station}
      <dl>
        <dt>Packs</dt><dd>10 listed</dd>
        <dt>Prices</dt><dd>$25&ndash;$500</dd>
        <dt>Posted EV</dt><dd>Page exists, fields empty</dd>
        <dt>Return</dt><dd>Not calculable</dd>
        <dt>Buyback</dt><dd>83%, lowest advertised</dd>
      </dl>
      <p>Built an expected-value page and left every field reading &ldquo;Data unavailable.&rdquo; The lowest buyback in the category, attached to the least spin. Operated from Panama under a Delaware parent.</p>
      <p class="more"><a href="/platforms/rip-station/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/underdog/">Underdog Rips</a></h3>
      {flag_underdog}
      <dl>
        <dt>Packs</dt><dd>Prices not published</dd>
        <dt>Odds shown</dt><dd>Claimed, unverified</dd>
        <dt>Posted EV</dt><dd>Claimed by its supplier</dd>
        <dt>Return</dt><dd>Not calculable</dd>
        <dt>Buyback</dt><dd>None stated; 85% per Phygitals</dd>
      </dl>
      <p>A major fantasy operator on Phygitals&rsquo; rails. The supplier documents 85% in USDC, third-party valuations and provable fairness; Underdog&rsquo;s own help pages state no rate at all.</p>
      <p class="more"><a href="/platforms/underdog/">Full breakdown &rarr;</a></p>
    </article>

    <article class="card">
      <h3><a href="/platforms/lastpack/">LastPack</a></h3>
      {flag_lastpack}
      <dl>
        <dt>Packs</dt><dd>5 tiers &times; 4 collections</dd>
        <dt>Prices</dt><dd>$1&ndash;$2,500</dd>
        <dt>Posted EV</dt><dd>95% GROSS EV per pack</dd>
        <dt>Return</dt><dd>95% posted</dd>
        <dt>Buyback</dt><dd>100%, cashable</dd>
      </dl>
      <p>The best pack page in the category &mdash; EV, odds, sell-back and min/max all shown before you buy, with a per-pull fairness check. Built on the same terms template as Triumph and MintPull, and &sect;4.5 still contradicts its own FAQ.</p>
      <p class="more"><a href="/platforms/lastpack/">Full breakdown &rarr;</a></p>
    </article>
  </div>

  <h2>Not yet measured</h2>
  <p>These platforms are on our list. We publish nothing about a platform's returns until we have collected its odds ourselves.</p>
  <div class="table-wrap">
  <table class="plain">
  <thead><tr><th scope="col">Platform</th><th scope="col">Why it matters</th><th scope="col">Status</th></tr></thead>
  <tbody>
    <tr><td class="name">Phygitals</td><td>Powers <a href="/platforms/underdog/">Underdog Rips</a>; its documented terms are covered on that page</td><td>Its own consumer platform not yet measured</td></tr>
    <tr><td class="name">Collector Crypt</td><td>One of the largest platforms by reported sales volume</td><td>Odds not yet collected</td></tr>
    <tr><td class="name">RipRip</td><td>Venture-backed Pok&eacute;mon-only entrant, launched April 2026</td><td>Odds not yet collected</td></tr>
    <tr><td class="name">GameStop Power Packs</td><td>A major retailer's version of digital packs</td><td>Odds not yet collected</td></tr>
  </tbody>
  </table>
  </div>
</div>
""".format(cyn=CY_N, pzn=PZ_N, cymin=money(CY_MIN_PRICE),
           cymax=money(CY_MAX_PRICE), pzstd=pct(PZ_STD_MID * 100, 0),
           clutch=CL["w_avg"], clutchpacks=CL["n_packs"],
           clutchpulls="{:,}".format(CL["pulls"]),
           **{"flag_" + s.replace("-", "_"): flag_row(s)
              for s in PLATFORM_FLAGS})

    return pages_written("/platforms/", page(
        "/platforms/",
        "Card ripping platforms compared — odds, returns and buyback terms",
        "Every online pack ripping platform we have collected odds from: Courtyard, Packz and Arena Club, with published returns, odds formats and buyback terms side by side.",
        body, crumbs=[("/", "Home"), (None, "Platforms")], updated=COLLECTED))


def build_courtyard():
    spicy = [p for p in CY if p["spicy"]]
    best = max((p for p in CY if p["ev_ratio"]), key=lambda p: p["ev_ratio"])
    worst = min((p for p in CY if p["ev_ratio"]), key=lambda p: p["ev_ratio"])

    faq_html, faq_ld = faq_block([
        ("What is the expected value of a Courtyard pack?",
         "<p>Courtyard publishes an expected value on every pack, and on %d of its %d packs that figure is exactly 95%% of the pack price. The $2,500 and $5,000 packs post 96%%, and the $1,500 U.S. Coins Pack posts the lowest figure at 93.3%%. In plain terms, the average card in a Courtyard pack is worth about 95 cents for every dollar spent, using Courtyard's own valuations.</p>" % (CY_AT_95, CY_N)),
        ("Does Courtyard pay out in cash?",
         "<p>Courtyard advertises an instant buyback at 90% of a card's value, and the platform settles in USDC, a dollar-pegged stablecoin. Applying that 90% rate to a 95% pack gives about 85.5% of the pack price back if you sell every card straight back. Independent tracking of recorded pulls has measured Courtyard's actual instant offers nearer 85% of value, which would put the real figure closer to 80%. We have not yet verified the withdrawal path ourselves.</p>"),
        ("Which Courtyard pack has the best odds?",
         "<p>Every Courtyard pack returns almost the same average, so the meaningful difference is shape rather than value. The chance of pulling a card worth at least roughly the pack price ranges from %s to %s across the %d packs. The highest posted return is the %s at %s, and the lowest is the %s at %s.</p>" % (pct(CY_HIT_LO, 0), pct(CY_HIT_HI, 0), CY_N, E(best["name"]), pct(best["ev_ratio"] * 100, 1), E(worst["name"]), pct(worst["ev_ratio"] * 100, 1))),
        ("What are Courtyard's Spicy packs?",
         "<p>Spicy packs lower the floor in exchange for a much larger ceiling. They post the same kind of expected value as the standard packs but start their bottom tier at around half the pack price, and their top prize reaches far higher. The Pok&eacute;mon Legend (Spicy) tops out at $79,900 against $40,000 for the standard Legend pack. Same average, more variance.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Courtyard pack odds and expected value</h1>
    <p class="lede">All {cyn} Courtyard packs, from the {cymin} Basic packs to the {cymax} Sports Cosmic Pack, with the expected value Courtyard publishes on each one.</p>
    {flags_courtyard}
  </div>

  <div class="finding">
    <p class="big">Courtyard publishes an exact expected value on every pack, and on {cy95} of {cyn} packs that figure is exactly 95% of the pack price. The $2,500 and $5,000 packs post 96%. The $1,500 U.S. Coins Pack is the lowest at 93.3%.</p>
    <p class="small muted">Collected {collected} from Courtyard's own pack pages.</p>
  </div>

  <div class="stats">
    <div class="stat"><b>{cyn}</b><span>Packs measured</span></div>
    <div class="stat"><b>95%</b><span>Posted return on {cy95} packs</span></div>
    <div class="stat"><b>85.5%</b><span>Return after 90% buyback</span></div>
    <div class="stat"><b>{hitlo}&ndash;{hithi}</b><span>Chance of beating the price</span></div>
  </div>

  <h2>What the numbers mean</h2>
  <p><strong>The average is fixed; the shape is what changes.</strong> Nearly every pack returns the same 95%, whether you spend $15 or $10,000. What differs between packs is how that value is distributed. The chance of pulling a card worth at least roughly the pack price runs from {hitlo} to {hithi} depending on the pack, so two packs with identical expected value can feel completely different to open.</p>

  <p><strong>Spicy packs trade the floor for the ceiling.</strong> The {nspicy} Spicy packs start their lowest tier at around half the pack price instead of about 70%, and push their top prize far higher in return. If you want the lottery shape, that is where it is; the average return is the same either way.</p>

  <p><strong>Selling back costs you more than the posted EV suggests.</strong> Courtyard advertises a 90% instant buyback. Applied to a 95% pack that is about 85.5% of your money returned if you sell everything straight back. Independent tracking of recorded Courtyard pulls has measured actual instant offers nearer 85% of card value, which would put the real cash return closer to 80%. The posted expected value is the value of the card, not the cash you can get for it.</p>

  <div class="callout">
    <h3>What we have not verified</h3>
    <p>The expected values on this page are Courtyard's own, calculated from Courtyard's own card valuations. We have not yet checked a sample of those valuations against real sold prices. If the valuations run high, the true return is lower than the posted figure. That check is the next thing we are doing, and we will publish it either way.</p>
  </div>

  <h2>All {cyn} Courtyard packs</h2>
  {table}

  <h2>Odds disclosure</h2>
  <p>Courtyard shows each pack's odds as dollar ranges with a percentage against each, plus a single expected value figure. Most packs' odds sum to between 99.6% and 100.5% rather than exactly 100%, which is consistent with rounding the small tiers for display rather than an error in the underlying numbers. One pack in our collection, the Sealed Pok&eacute;mon Booster ($50), appears to be missing a tier between $100 and $200 and needs rechecking.</p>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/compare/courtyard-vs-packz/">Courtyard vs Packz</a> &mdash; how the two disclosures compare.</li>
    <li><a href="/calculator/">Run a Courtyard pack through the calculator</a>.</li>
    <li><a href="/data/">Download the full Courtyard odds dataset</a>.</li>
  </ul>
</div>
""".format(cyn=CY_N, cy95=CY_AT_95, cymin=money(CY_MIN_PRICE),
           cymax=money(CY_MAX_PRICE), collected=COLLECTED,
           hitlo=pct(CY_HIT_LO, 0), hithi=pct(CY_HIT_HI, 0),
           nspicy=len(spicy), table=courtyard_table(), faq=faq_html, **{"flags_courtyard": flag_row("courtyard")})

    ds = jsonld({
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "Courtyard pack odds and expected values",
        "description": "Published odds tiers and expected values for all %d Courtyard mystery packs, collected %s." % (CY_N, COLLECTED),
        "url": BASE_URL + "/platforms/courtyard/",
        "dateModified": COLLECTED,
        "creator": {"@type": "Organization", "name": SITE_NAME},
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv",
                          "contentUrl": BASE_URL + "/data/courtyard_odds_2026-09-21.csv"}],
    })

    return pages_written("/platforms/courtyard/", page(
        "/platforms/courtyard/",
        "Courtyard pack odds and expected value — all %d packs" % CY_N,
        "Courtyard posts an expected value of 95%% of the price on %d of its %d packs. Full odds tables, buyback maths and what the posted EV leaves out." % (CY_AT_95, CY_N),
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "Courtyard")],
        updated=COLLECTED, structured=[faq_ld, ds]))


def build_packz():
    faq_html, faq_ld = faq_block([
        ("What is the expected value of a Packz pack?",
         "<p>Packz does not publish an expected value, but it does publish dollar-range odds on every pack. Working those out at the middle of each range gives about %s of the pack price on every pack of $25 and up. The two cheapest packs are worse: the $10 Pok&eacute;mon Uncommon Pack returns about %s and the $5 Pok&eacute;mon Common Pack about %s. Because Packz shows ranges rather than exact values, every figure is an estimate with a band around it rather than a precise number.</p>" % (pct(PZ_STD_MID * 100, 0), pct(PZ_UNCOMMON["ratio_mid"] * 100, 0), pct(PZ_COMMON["ratio_mid"] * 100, 0))),
        ("Can you cash out a Packz buyback?",
         "<p>No. Packz pays sell-backs as site credit that cannot be withdrawn, so the only way to take value out of the platform is to have the card shipped and sell it yourself. The standard rate is 90% of fair market value, and a new user's first pack qualifies for a 100% buyback capped at $100. Several ranking sites score Packz highly on the strength of that buyback without noting that it pays in credit rather than cash.</p>"),
        ("Do all Packz packs have the same odds?",
         "<p>Yes. All %d packs we collected use the same seven probabilities, 44%%, 25.6%%, 19%%, 9.5%%, 1.5%%, 0.3%% and 0.1%%, with the dollar ranges scaled to the pack price. For every pack of $25 and up the tiers are exactly 0.5 to 0.7, 0.7 to 1, 1 to 1.5, 1.5 to 2.5, 2.5 to 5, 5 to 10 and 10 to 20 times the price. A $25 Starter Pack and a $1,000 Champion Pack therefore have the same expected return.</p>" % PZ_N),
        ("What are the chances of beating the pack price on Packz?",
         "<p>%s, on every pack. That is the sum of the top five tiers, which all start at or above the pack price. Put the other way, %s of pulls are worth less than you paid.</p>" % (pct(PZ_HIT, 1), pct(100 - PZ_HIT, 1))),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Packz pack odds and expected value</h1>
    <p class="lede">All {pzn} Packz packs, from the $5 Pok&eacute;mon Common Pack to the $1,000 Champion and Hall of Fame packs, calculated from the odds Packz publishes on each pack page.</p>
    {flags_packz}
  </div>

  <div class="finding">
    <p class="big">Every Packz pack uses the same odds template. On the $25-and-up packs the published odds work out to about {pzstd} of the pack price at midpoint values. The two cheapest packs are worse: the $10 Uncommon Pack returns about {unc} and the $5 Common Pack about {com}.</p>
    <p class="small muted">Calculated from Packz's published odds, collected {collected}. Packz shows value ranges, not exact card values.</p>
  </div>

  <div class="stats">
    <div class="stat"><b>{pzn}</b><span>Packs measured</span></div>
    <div class="stat"><b>{pzstd}</b><span>Return on $25+ packs</span></div>
    <div class="stat"><b>{pzhit}</b><span>Chance of beating the price</span></div>
    <div class="stat"><b>0%</b><span>Of buyback you can withdraw</span></div>
  </div>

  <h2>One odds template, fourteen packs</h2>
  <p>All {pzn} packs use the same seven probabilities with the dollar ranges scaled to the price. For every pack of $25 and up the tiers are exactly these multiples of the pack price:</p>

  <div class="table-wrap">
  <table class="plain">
  <caption>The Packz odds template, identical across all $25-and-up packs.</caption>
  <thead><tr><th scope="col">Tier</th><th scope="col" class="num">Value, as a multiple of the price</th><th scope="col" class="num">Odds</th><th scope="col">Outcome</th></tr></thead>
  <tbody>
    <tr><td>1</td><td class="num">0.5&ndash;0.7&times;</td><td class="num">44%</td><td>Loss</td></tr>
    <tr><td>2</td><td class="num">0.7&ndash;1&times;</td><td class="num">25.6%</td><td>Loss</td></tr>
    <tr><td>3</td><td class="num">1&ndash;1.5&times;</td><td class="num">19%</td><td>Break even or better</td></tr>
    <tr><td>4</td><td class="num">1.5&ndash;2.5&times;</td><td class="num">9.5%</td><td>Win</td></tr>
    <tr><td>5</td><td class="num">2.5&ndash;5&times;</td><td class="num">1.5%</td><td>Win</td></tr>
    <tr><td>6</td><td class="num">5&ndash;10&times;</td><td class="num">0.3%</td><td>Win</td></tr>
    <tr><td>7</td><td class="num">10&ndash;20&times;</td><td class="num">0.1%</td><td>Win</td></tr>
  </tbody>
  </table>
  </div>

  <p><strong>{loss} of pulls are worth less than you paid.</strong> That is the first two tiers combined. The top tier hits once in a thousand packs. Most of the expected value sits in the common tiers rather than the chase, which is actually a point in the template's favour: the return does not depend on a jackpot you will almost certainly never hit.</p>

  <h2>The cheap packs are the worst deal</h2>
  <p>The $5 Common Pack and $10 Uncommon Pack break the pattern. Their lowest tier starts at 30% and 40% of the pack price respectively, instead of the 50% floor used on every larger pack, which drags their return below the rest. The packs most likely to be bought by a beginner testing the platform are the packs that give back the least.</p>

  <h2>Buyback pays in credit, not cash</h2>
  <p>Packz advertises a 90% buyback, and a new user's first pack qualifies for 100% capped at $100. What the headline does not say is that sell-backs are paid as site credit that cannot be withdrawn. The credit can only buy more packs. Your only routes to actual money are shipping the card and selling it yourself, or keeping it.</p>
  <p>That distinction matters most on cheap pulls. Shipping a $2 card home to resell it will usually cost more than the card is worth, so in practice a low pull on a small pack leaves you choosing between re-ripping and keeping something you did not want.</p>

  <div class="callout">
    <h3>Why this estimate has a band around it</h3>
    <p>Packz publishes value ranges rather than exact card values, so an exact expected value cannot be calculated from its pages. The headline figures here assume cards sit at the middle of their range. Real card values tend to cluster toward the bottom of a range, because cheap cards are more numerous than expensive ones, so the true return is likely at or below our midpoint estimate. The table below shows the full possible span for each pack.</p>
  </div>

  {cta}

  <h2>All {pzn} Packz packs</h2>
  {table}

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Launched</th><td>September 2025</td></tr>
    <tr><th scope="row">Availability</th><td>United States only, 18+</td></tr>
    <tr><th scope="row">Categories</th><td>Sports and Pok&eacute;mon</td></tr>
    <tr><th scope="row">Payment methods</th><td>Visa, Mastercard, American Express, Discover</td></tr>
    <tr><th scope="row">Buyback rate</th><td>90% of fair market value, as non-withdrawable site credit</td></tr>
    <tr><th scope="row">New user offer</th><td>100% buyback on the first pack, capped at $100</td></tr>
    <tr><th scope="row">Odds disclosure</th><td>Dollar-range odds on every pack page; no expected value published</td></tr>
  </tbody>
  </table>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/compare/courtyard-vs-packz/">Courtyard vs Packz</a> &mdash; estimated return against committed return.</li>
    <li><a href="/calculator/">Run a Packz pack through the calculator</a>.</li>
    <li><a href="/data/">Download the full Packz odds dataset</a>.</li>
  </ul>
</div>
""".format(pzn=PZ_N, pzstd=pct(PZ_STD_MID * 100, 0), collected=COLLECTED,
           com=pct(PZ_COMMON["ratio_mid"] * 100, 0),
           unc=pct(PZ_UNCOMMON["ratio_mid"] * 100, 0),
           pzhit=pct(PZ_HIT, 1), loss=pct(100 - PZ_HIT, 1),
           table=packz_table(), faq=faq_html, cta=affiliate_cta("packz"), **{"flags_packz": flag_row("packz")})

    ds = jsonld({
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "Packz pack odds and calculated expected values",
        "description": "Published odds tiers for all %d Packz mystery packs with calculated expected value bands, collected %s." % (PZ_N, COLLECTED),
        "url": BASE_URL + "/platforms/packz/",
        "dateModified": COLLECTED,
        "creator": {"@type": "Organization", "name": SITE_NAME},
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv",
                          "contentUrl": BASE_URL + "/data/packz_odds_2026-09-21.csv"}],
    })

    return pages_written("/platforms/packz/", page(
        "/platforms/packz/",
        "Packz pack odds and expected value — all %d packs" % PZ_N,
        "Packz's published odds work out to about %s of the pack price on $25+ packs, and less on the $5 and $10 packs. Full odds template, EV bands and why the 90%% buyback pays credit, not cash." % pct(PZ_STD_MID * 100, 0),
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "Packz")],
        updated=COLLECTED, structured=[faq_ld, ds]))


def build_arena_club():
    rows = []
    for p in ARENA_CLUB_PACKS:
        for i, (tier, count, rate) in enumerate(p["tiers"]):
            rows.append(
                '<tr><td class="name">%s</td><td>%s</td><td>%s</td><td>%s</td>'
                '<td class="num">%d</td><td class="num">%s</td>'
                '<td class="num"><strong>%s</strong></td></tr>' % (
                    E(p["name"]), p["collected"], money(p["price"]), tier,
                    count, pct(rate, 2),
                    pct(count * rate, 2 if count * rate < 1 else 1)))
        rows.append(
            '<tr><td class="name"></td><td></td><td></td>'
            '<td class="rowspan-label">All tiers</td><td class="num">%d</td>'
            '<td class="num"></td><td class="num"><strong>%s</strong></td></tr>'
            % (sum(c for _, c, _ in p["tiers"]), pct(p["odds_sum"], 2)))

    faq_html, faq_ld = faq_block([
        ("What is the expected value of an Arena Club pack?",
         "<p>It cannot be calculated from Arena Club's own pages. Arena Club lists a hit rate for each individual card but attaches no value to any of them, and publishes no expected value figure anywhere on its pack pages or in its help centre. Of the three platforms we have measured, Arena Club is the hardest for a buyer to evaluate before spending.</p>"),
        ("How do Arena Club pack odds work?",
         "<p>Each pack page lists every card available in that pack with its own hit rate, grouped into three named tiers: Grail, Chase and Lineup. Grail cards are listed at 0.01% to 0.02% each, Chase cards at 0.25% each and Lineup cards at 1.96% each. In the two packs we collected in September there were 3 Grail, 8 Chase and 50 Lineup cards, meaning 98% of pulls came from the Lineup tier. Because the rates are per card rather than per tier, you have to add up dozens of individual numbers to work out your real chance at anything.</p>"),
        ("Does Arena Club grade its own cards?",
         "<p>Some of them, yes. Alongside PSA, BGS and CGC slabs, Arena Club's checklists include cards in its own holders, labelled with an Arena Club grade and a BAC certificate number. In the October checklist we collected for the $25 Pok&eacute;mon Bronze pack, 11 of the 24 Lineup cards were Arena Club-graded rather than third-party graded. That matters for valuation: a PSA 10 has a public sales history you can look up, while an Arena Club 10 of the same card has no established market, so there is no independent way to check what the platform says it is worth.</p>"),
        ("What is Arena Club's Collect Safe option?",
         "<p>Collect Safe is an optional add-on bought at checkout for an extra 10% of the pack price, which guarantees a buyback offer of at least 80% of the pack price. On the $25 Pok&eacute;mon Bronze pack it is offered as &ldquo;Guarantee a $20 Arena Club Offer, for just $2.50 more.&rdquo; You pay $27.50 and cannot get back less than $20, so your worst case is losing $7.50, or 27.3% of what you spent. Without it the floor is only 90% of the revealed card's estimated value, so a low pull returns much less. The add-on pays for itself whenever the card is worth less than about $22.22, which is 89% of the pack price.</p>"),
        ("Can you withdraw money from Arena Club?",
         "<p>Yes. Accepted buyback offers are credited to an in-house Arena Club Wallet rather than refunded directly, and wallet funds can then be withdrawn to a bank account or debit card through a connected Stripe account. That makes it the only platform of the three we have measured whose buyback reaches real money without further conditions, as against Packz's credit-only buyback.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Arena Club pack odds and buyback terms</h1>
    <p class="lede">Arena Club sells graded slabs in nine price tiers from $25 to $5,000 across as many as nine categories. It publishes detailed per-card odds and no card values at all, which makes it the hardest of the three platforms to evaluate before you buy.</p>
    {flags_arena_club}
  </div>

  <div class="finding">
    <p class="big">Arena Club's expected value cannot be calculated from its own disclosures. It lists a hit rate for every individual card in a pack but attaches no value to any of them, and publishes no expected value figure anywhere. Its buyback terms, by contrast, are the best of the three platforms we have measured.</p>
    <p class="small muted">Collected {collected} and re-collected {updated} from Arena Club's pack pages and help centre.</p>
  </div>

  <h2>How the odds are structured</h2>
  <p>Every pack page carries an "Available Slabs" checklist that lists each card with its own hit rate, grouped into three tiers. We collected two complete checklists, and both use the same structure:</p>

  <div class="table-wrap">
  <table>
  <caption>Complete checklists collected for two Arena Club packs on {collected}, plus a second collection of the Pok&eacute;mon Bronze pack on {updated}.</caption>
  <thead><tr><th scope="col">Pack</th><th scope="col">Collected</th><th scope="col">Price</th><th scope="col">Tier</th><th scope="col" class="num">Cards</th><th scope="col" class="num">Odds per card</th><th scope="col" class="num">Tier total</th></tr></thead>
  <tbody>{rows}</tbody>
  </table>
  </div>

  <p><strong>98% of pulls come from the Lineup tier.</strong> On the September checklists that means a pack's expected value is almost exactly the average value of its 50 Lineup cards; the Chase and Grail cards barely move it. Your combined chance at any Chase or Grail card is about 2%, roughly one pack in fifty, and a specific Grail card is about one in five thousand.</p>

  <p><strong>The marquee names are mostly in the Lineup.</strong> A basketball checklist reads like a hall of fame roster, with Jordan, LeBron and Curry cards throughout. But Lineup cards have to be sized to fit the pack price, so at $100 those are common base cards rather than the ones a collector pictures when they see the name. The checklist is accurate and still misleading if you only skim the names.</p>

  <h2>Buyback and Collect Safe</h2>
  <p>Arena Club's standard buyback is 90% of the revealed card's estimated value, credited to an in-house wallet that can be withdrawn to a bank account or debit card through a connected Stripe account. Of the three platforms here, it is the only buyback that reaches real money without further conditions.</p>

  <p>At checkout each pack also offers <strong>Collect Safe</strong>, an opt-in add-on costing an extra 10% of the pack price. With it you are guaranteed an offer of at least 80% of the pack price, or 90% of the card's estimated value, whichever is greater. On the $25 Pok&eacute;mon Bronze pack the toggle reads &ldquo;Guarantee a $20 Arena Club Offer, for just $2.50 more,&rdquo; which confirms the premium is 10% of the pack price and the floor is 80% of the pack price before the premium is added.</p>

  <div class="table-wrap">
  <table class="plain">
  <caption>Collect Safe on the $25 Pok&eacute;mon Bronze pack, using the figures Arena Club displays.</caption>
  <thead><tr><th scope="col"></th><th scope="col">Without Collect Safe</th><th scope="col">With Collect Safe</th></tr></thead>
  <tbody>
    <tr><th scope="row">You pay</th><td>$25</td><td>$27.50</td></tr>
    <tr><th scope="row">Guaranteed floor</th><td>None &mdash; 90% of whatever the card is worth</td><td>$20</td></tr>
    <tr><th scope="row">Worst case</th><td>Whatever a near-worthless pull is worth</td><td>Lose $7.50, or 27.3% of outlay</td></tr>
    <tr><th scope="row">Pays for itself when</th><td>&mdash;</td><td>The card is worth less than $22.22, which is 89% of the pack price</td></tr>
  </tbody>
  </table>
  </div>

  <p>So the add-on is worth buying if a pack produces a card worth under about 89% of its price more often than one time in ten, which is the break-even point for a 10% premium. Given that this is a product where the average card is worth less than the pack, that condition is very likely met. But Arena Club publishes no card values, so neither we nor a buyer at the checkout toggle can calculate it properly.</p>

  <h2>Arena Club grades some of its own cards</h2>
  <p>The checklists mix third-party slabs from PSA, BGS and CGC with cards in Arena Club's own holders, labelled with an Arena Club grade and a BAC certificate number. In the October checklist we collected for the $25 Pok&eacute;mon Bronze pack, 11 of the 24 Lineup cards were Arena Club-graded rather than third-party graded.</p>

  <p>This compounds the valuation problem. A PSA 10 of a given card has a public sales history that anyone can look up, so a platform's stated value for it can be checked. An Arena Club 10 of the same card has no established secondary market, so there is no independent way to verify what the platform says it is worth, or what it will offer you for it at buyback. A platform grading the inventory it sells and then setting the buyback price against its own grade is a structure worth understanding before you spend.</p>

  <div class="callout">
    <h3>The checklist changed completely in a month, and the odds no longer add up</h3>
    <p>We collected the $25 Pok&eacute;mon Bronze checklist twice, on 21 September and 21 October. Not one card appeared in both. The Lineup had also shrunk from 50 cards to 24, and cards disappeared from the list while we were reading it.</p>
    <p>Taken at face value the October figures do not work: 3 Grail cards at 0.01%, 8 Chase at 0.25% and 24 Lineup at 1.96% sum to 49.07%, not 100%. Either the per-card rates are not updated as inventory sells out, or part of the list was not displayed. We are rechecking before drawing a conclusion, because the difference matters: if displayed rates go stale as cards sell, the odds on the page are not the odds you are playing.</p>
  </div>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Pack name</th><td>Slab Packs, one graded card per pack</td></tr>
    <tr><th scope="row">Price tiers</th><td>Bronze $25, Silver $50, Gold $100, Ruby $250, Emerald $500, Diamond $1,000, Legendary $2,500, Crown Jewel $5,000, plus limited Special Series packs</td></tr>
    <tr><th scope="row">Categories</th><td>Baseball, basketball, football, Pok&eacute;mon, soccer, Magic, One Piece, hockey and Super, though not every category is sold at every tier</td></tr>
    <tr><th scope="row">Odds disclosure</th><td>Per-card hit rates in Grail, Chase and Lineup tiers; no card values</td></tr>
    <tr><th scope="row">Expected value</th><td>Not published</td></tr>
    <tr><th scope="row">Buyback rate</th><td>90% of the card's estimated value</td></tr>
    <tr><th scope="row">Buyback payout</th><td>Arena Club Wallet, withdrawable to a bank account or debit card via Stripe</td></tr>
    <tr><th scope="row">Collect Safe</th><td>Optional, 10% of the pack price, guarantees 80% of the pack price or 90% of card value, whichever is greater</td></tr>
  </tbody>
  </table>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/platforms/">Compare all twenty-four platforms</a>.</li>
    <li><a href="/methodology/">How we rate platforms</a>, including how we handle a platform that publishes no values.</li>
  </ul>
</div>
""".format(collected=COLLECTED, updated=UPDATED, rows="".join(rows), faq=faq_html, **{"flags_arena_club": flag_row("arena-club")})

    return pages_written("/platforms/arena-club/", page(
        "/platforms/arena-club/",
        "Arena Club pack odds, Collect Safe and buyback terms explained",
        "Arena Club lists per-card hit rates with no values, so its expected value cannot be calculated. What the Grail, Chase and Lineup tiers really mean, and whether Collect Safe is worth 10%.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "Arena Club")],
        updated=COLLECTED, structured=faq_ld))


def build_tilt():
    tiers = [
        ("Pokémon", "Dime Pack", "$0.10"), ("Pokémon", "Dollar Pack", "$1"),
        ("Pokémon", "Rookie Pack", "$2.50"),
        ("Pokémon", "EX Pack", "$250"), ("Pokémon", "Full Art", "$500"),
        ("Pokémon", "Master Pack", "$1,000"),
        ("Pokémon", "Grandmaster Pack", "$3,000"),
        ("Sports", "Starter / Kickoff / Tip-Off", "$25"),
        ("Sports", "Premium / Blitz / Fast Break", "$50"),
        ("Sports", "Pro / Red Zone / Crossover / Sleeper", "$100"),
        ("Sports", "Ace / Touchdown / Slam Dunk / Steal / Flash / Ink", "$250"),
        ("Sports", "Ultimate / Hail Mary / Dagger / Heist / Supernova", "$500"),
        ("Sports", "Master / Primetime / Showtime / Grand Heist / Case Hit", "$1,000"),
        ("Sports", "Grandmaster", "$3,000"),
        ("One Piece", "Loot Pack", "$25"),
        ("One Piece", "Pro Pack", "$100"),
        ("One Piece", "Heritage Pack", "$500"),
    ]
    rows = "".join(
        '<tr><td>%s</td><td class="name">%s</td><td class="num">%s</td></tr>'
        % (E(c), E(n), p) for c, n, p in tiers)

    faq_html, faq_ld = faq_block([
        ("Does Tilt Rips publish pack odds?",
         "<p>No. Across roughly 60 packs we found no pull rates, drop rates, probabilities, value tiers or expected value figures anywhere on the site. Pack pages show a list of top prizes with their market values, which tells you what the ceiling looks like but nothing about your chance of reaching it. Tilt Rips has the largest pack catalogue of any platform we track and the least odds disclosure.</p>"),
        ("Can you withdraw money from Tilt Rips?",
         "<p>Yes, and this is the platform's strongest feature. Selling a card back pays 90% of market value into a Tilt Rips wallet, and withdrawals are available in US dollars and several cryptocurrencies, with no fees or commissions beyond those shown in the app. That is a better cash route than Fanatics, which pays 84.6% effective in non-withdrawable credit, and Packz, which pays 90% in credit that can only buy more packs.</p>"),
        ("How does Tilt Rips decide what a card is worth?",
         "<p>The site says the price is set by live market data but does not name the data source, and it states that the sell-back price cannot be disputed. Those two facts together are the counterweight to the 90% headline: the party paying you sets the number it is paying 90% of, from a source it does not identify, with no appeal. Compare Fanatics, which names Card Ladder as its valuation source, so the figure can in principle be checked against data a buyer can also see.</p>"),
        ("What is the cheapest Tilt Rips pack?",
         "<p>A $0.10 Dime Pack, followed by a $1 Dollar Pack and a $2.50 Rookie Pack. Those are by a wide margin the cheapest entry points of any platform we track, where the next cheapest anywhere is Crown Rips at $1 and Packz at $5. The catalogue runs up to $3,000 Grandmaster packs.</p>"),
        ("How long does Tilt Rips shipping take?",
         "<p>Up to six weeks, per the site, with shipping fees shown before you confirm and international delivery available for additional fees. That is the slowest fulfilment we have recorded: Fanatics quotes 3 to 15 business days. Vault storage is free with no storage fees, so there is no pressure to ship, but closing an account requires shipping or selling all inventory first.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Tilt Rips: 60 packs, no published odds</h1>
    <p class="lede">Tilt Rips has the largest pack catalogue of any platform we track, prices starting at ten cents, and the best cash-out terms we have verified. It publishes no pull rates for any of it.</p>
    {flags_tilt_rips}
  </div>

  <div class="finding">
    <p class="big">Across roughly 60 packs priced from $0.10 to $3,000, Tilt Rips publishes no pull rates, no value tiers and no expected value. Its sell-back is the strongest we have verified &mdash; 90% of market value, withdrawable in dollars or crypto &mdash; but the platform sets that market value itself, does not name its data source, and states the price cannot be disputed.</p>
    <p class="small muted">Read from the Tilt Rips site on {collected}. Pack pages load their contents dynamically, so a first-hand collection is still needed to confirm no odds appear once a pack page is fully loaded.</p>
  </div>

  <div class="stats">
    <div class="stat"><b>~60</b><span>Packs in the catalogue</span></div>
    <div class="stat"><b>0</b><span>With published pull rates</span></div>
    <div class="stat"><b class="pos">90%</b><span>Sell-back, withdrawable</span></div>
    <div class="stat"><b>$0.10</b><span>Cheapest pack anywhere</span></div>
  </div>

  <h2>The best cash route in the category</h2>
  <p>On every other platform we have examined, the headline buyback rate erodes somewhere: Fanatics deducts a 6% marketplace fee and pays in credit you cannot withdraw, Packz pays credit that can only buy more packs, Courtyard's advertised 90% has been independently measured nearer 85%. Tilt Rips pays 90% of market value into a wallet you can withdraw from in US dollars or several cryptocurrencies, with no fees or commissions beyond those shown in the app.</p>

  <p>Taken at face value that is the strongest sell-back we have been able to verify. Fast Rips advertises 100%, but its own terms describe non-withdrawable credit, so we do not count it. Crown Rips claims 100% but is unverified and in closed beta; Arena Club's 90% to a Stripe-connected bank account is the closest comparison and is equally good. Tilt Rips also vaults cards free with no storage fees and no time limit, so holding a card costs nothing.</p>

  <div class="callout">
    <h3>The catch is who decides what 90% is 90% of</h3>
    <p>Tilt Rips says the price is set by live market data, but it does not name the data source, and it states plainly that the sell-back price cannot be disputed. A rate is only as good as the valuation it is applied to, and here the party paying you also sets that valuation, from a source you cannot inspect, with no appeal.</p>
    <p>Fanatics is the useful contrast: it pays a worse effective rate, 84.6% against 90%, but names Card Ladder as its valuation source, so the number can be checked against data the buyer can also reach. A verifiable 84.6% and an unverifiable 90% are not obviously ranked in the order the percentages suggest.</p>
  </div>

  <h2>The odds gap</h2>
  <p>Pack pages show a list of top prizes with market values attached &mdash; on one $100 pack those run as high as $90,000, which is 900 times the pack price. A ceiling is the easiest thing in this business to advertise and the least useful thing to know. What it does not come with is any probability, so there is no way to turn it into an expected value.</p>

  <p>The site also makes two claims that read as transparency but are not odds disclosure: that every pack contains real physical cards held with security partners, and that pricing comes from live market data. Both speak to inventory and valuation. Neither tells you your chance of pulling anything. We found no provably-fair mechanism, no third-party audit of pull rates, and no published odds of any kind.</p>

  <p>With roughly 60 packs, Tilt Rips has more products with no disclosed odds than any other platform we track has products at all.</p>

  <h2>Pack catalogue and prices</h2>
  <p>Prices are not shown in the page text for most packs, but the pack URLs encode them, and the few prices that do appear confirm the pattern. The table below is our reconstruction and should be treated as provisional until confirmed on the live pack pages.</p>

  <div class="table-wrap">
  <table>
  <caption>Tilt Rips pack tiers, reconstructed from pack URLs and the prices shown on the site, {collected}. Several sports packs share a price point under different names by sport.</caption>
  <thead><tr><th scope="col">Category</th><th scope="col">Packs</th><th scope="col" class="num">Price</th></tr></thead>
  <tbody>{rows}</tbody>
  </table>
  </div>

  <p><strong>The ten-cent pack deserves a mention.</strong> A $0.10 Dime Pack and a $1 Dollar Pack are the cheapest entry points we have found anywhere, well below Packz at $5 and Crown Rips at $1. Cheap packs lower the barrier to trying a platform, and on both Packz and Crown Rips the cheapest packs also carried the worst floors. Whether that holds here cannot be determined, because the floors are not published either. Given that these are Pok&eacute;mon packs, the combination of a ten-cent price point and undisclosed odds is worth noting on its own terms.</p>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Categories</th><td>Pok&eacute;mon, One Piece, football, basketball and general sports</td></tr>
    <tr><th scope="row">Pack prices</th><td>$0.10 to $3,000, roughly 60 packs</td></tr>
    <tr><th scope="row">Odds disclosure</th><td>None. Top prizes listed with values; no pull rates</td></tr>
    <tr><th scope="row">Expected value</th><td>Not published and not calculable</td></tr>
    <tr><th scope="row">Sell-back</th><td>90% of market value, instantly to a wallet</td></tr>
    <tr><th scope="row">Withdrawals</th><td>US dollars and several cryptocurrencies</td></tr>
    <tr><th scope="row">Fees</th><td>None beyond those shown in the app, per the site</td></tr>
    <tr><th scope="row">Valuation source</th><td>&ldquo;Live market data,&rdquo; source not named; price cannot be disputed</td></tr>
    <tr><th scope="row">Vaulting</th><td>Free, no storage fees</td></tr>
    <tr><th scope="row">Shipping</th><td>Up to six weeks; fees shown before confirming; international available</td></tr>
    <tr><th scope="row">Marketplace</th><td>Cards can be listed from inventory or the vault; fees shown before confirming</td></tr>
    <tr><th scope="row">Account closure</th><td>Requires shipping or selling all inventory first</td></tr>
  </tbody>
  </table>
  </div>

  <h2>What we still need</h2>
  <ul>
    <li><strong>Any pull rates at all</strong>, from a fully loaded pack page. Our reading was done without JavaScript, so we cannot yet rule out that odds appear once a pack loads. This is the first thing to check.</li>
    <li><strong>Confirmed prices</strong> for each pack, to replace the reconstruction above.</li>
    <li><strong>The valuation data source</strong>, which decides what the 90% is calculated from.</li>
    <li><strong>Whether a floor exists</strong> on any pack, published or otherwise.</li>
    <li><strong>Withdrawal minimums and processing times</strong>, which are not stated.</li>
  </ul>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/platforms/fanatics-instant-rips/">Fanatics Instant Rips</a>, the useful contrast on valuation sourcing</li>
    <li><a href="/platforms/clutch-packs/">Clutch Packs</a>, the only platform publishing observed results</li>
    <li><a href="/platforms/">Compare all twenty-four platforms</a></li>
  </ul>
</div>
""".format(collected=CLUTCH_COLLECTED, rows=rows, faq=faq_html, **{"flags_tilt_rips": flag_row("tilt-rips")})

    return pages_written("/platforms/tilt-rips/", page(
        "/platforms/tilt-rips/",
        "Tilt Rips review — 60 packs, no published odds, 90% withdrawable sell-back",
        "Tilt Rips publishes no pull rates for any of its ~60 packs, priced from $0.10 to $3,000. Its 90% sell-back is withdrawable in cash or crypto, but the platform sets the valuation and the price cannot be disputed.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "Tilt Rips")],
        updated=CLUTCH_COLLECTED, structured=faq_ld))


def build_fanatics():
    faq_html, faq_ld = faq_block([
        ("Does Fanatics Instant Rips publish pack odds?",
         "<p>No. Fanatics publishes a checklist of the cards available in a series, and has said it intends to move from a static checklist to a dynamic one showing what is still unpulled, but it does not publish pull rates or probabilities against those cards. Knowing what is in a pack without knowing the odds of each card is not enough to work out an expected value. Fanatics is the largest brand in this category and currently discloses the least about odds of the twenty-four platforms we track.</p>"),
        ("What is the real Fanatics instant offer percentage?",
         "<p>Effectively 84.6% of a card's appraised value, not the 90% headline. Fanatics' own worked example takes a $200 card, applies the 90% rate to get $180, then deducts a 6% marketplace fee of $10.80, leaving an offer of $169.20. That is 84.6% of the card's value. The formula is 0.90 multiplied by 0.94. The 90% figure is accurate as far as it goes, but it is not what arrives.</p>"),
        ("Can you withdraw Fanatics Instant Rips credits as cash?",
         "<p>No. Accepting an instant offer pays in Fanatics Live credits, which cannot be withdrawn as cash and can only be spent on Fanatics Live purchases, including more Instant Rips. There is a separate route to real money: decline the offer, take the card, and list it on the Fanatics Collect marketplace, where sales do pay out, with free ACH withdrawal or a $50 fee for a wire. That path costs 1% to 3% of asset value in fulfillment fees and takes time, but it is the only one that ends in cash.</p>"),
        ("How much do Fanatics Instant Rips packs cost?",
         "<p>The category pages list Collector Packs from $10 to $100, Football and Basketball from $100 to $1,000, Baseball from $50 to $1,000, and Pok&eacute;mon from $25 to $2,500. The debut Odyssey series was 1,000 baseball repacks at $250 each, one graded card per pack, with a reported value floor of about $90 and a ceiling of about $3,800.</p>"),
        ("Where do Fanatics card valuations come from?",
         "<p>Card Ladder, a third-party sales-data service. This is the one place where Fanatics has the best practice in the category: Courtyard, Packz and Arena Club all appraise cards using their own valuations, which means the figure a buyback is calculated against is set by the party paying it. Using an outside dataset removes that conflict, and it makes the valuation checkable by anyone with access to the same data.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Fanatics Instant Rips: the 90% offer is really 84.6%</h1>
    <p class="lede">Fanatics is the largest brand in digital pack ripping and discloses the least about odds. It also has the category's best practice on card valuation. Both of those are worth knowing before you buy.</p>
    {flags_fanatics_instant_rips}
  </div>

  <div class="finding">
    <p class="big">Fanatics advertises an instant offer of 90% of a card's appraised value. Its own worked example takes a $200 card, applies the 90%, then deducts a 6% marketplace fee, leaving $169.20 &mdash; which is 84.6% of the card's value. The offer is also paid in Fanatics Live credits that cannot be withdrawn as cash.</p>
    <p class="small muted">Figures from Fanatics' own published example and help documentation, read {collected}. No pull rates are published for any pack, so no expected value can be calculated.</p>
  </div>

  <div class="stats">
    <div class="stat"><b class="neg">84.6%</b><span>Effective instant offer, after fees</span></div>
    <div class="stat"><b>0</b><span>Packs with published pull rates</span></div>
    <div class="stat"><b>36%</b><span>Odyssey series floor, as % of price</span></div>
    <div class="stat"><b>48h</b><span>Window to accept an offer</span></div>
  </div>

  <h2>The buyback maths</h2>
  <p>The 90% figure is accurate as a rate and misleading as an outcome, because the marketplace fee comes off afterwards. Fanatics publishes the arithmetic itself, which is to its credit; it just does not publish the resulting percentage.</p>

  <div class="table-wrap">
  <table class="plain">
  <caption>Fanatics' own worked example of an instant offer.</caption>
  <tbody>
    <tr><th scope="row">Card's appraised value</th><td>$200.00</td></tr>
    <tr><th scope="row">Offer at 90%</th><td>$180.00</td></tr>
    <tr><th scope="row">Marketplace fee, 6%</th><td>&minus;$10.80</td></tr>
    <tr><th scope="row">Offer received</th><td><strong>$169.20</strong></td></tr>
    <tr><th scope="row">Effective rate</th><td><strong>84.6% of card value</strong></td></tr>
    <tr><th scope="row">Paid as</th><td>Fanatics Live credits, not withdrawable as cash</td></tr>
  </tbody>
  </table>
  </div>

  <p><strong>Credit is not cash, but the ecosystem is larger.</strong> Like Packz, Fanatics pays sell-backs in credit that cannot be withdrawn. Unlike Packz, where credit can only buy more packs, Fanatics Live credits work across any Fanatics Live purchase. That is a wider door, still inside the same building.</p>

  <p><strong>There is a real cash route, and it is not the instant offer.</strong> Decline the offer, take the card, and list it on the Fanatics Collect marketplace, where sales pay out in money, with free ACH withdrawal or a $50 wire fee. Fulfillment runs 1% to 3% of asset value and shipping takes 3 to 15 business days. On a card worth more than the instant offer minus that friction, selling it yourself is the better move &mdash; which is to say, the convenient option is the expensive one.</p>

  <h2>The odds problem</h2>
  <p>Fanatics publishes a checklist of what is in a series and has said it will move from a static list to a dynamic one that shows what remains unpulled. That is useful and more than Crown Rips offers. It is still not odds.</p>

  <p>A checklist tells you which cards exist in the pool. Without a probability against each one, you cannot calculate an average, and neither can anyone else. Compare the two ends of this category: Clutch Packs enumerates a 100-card pool at 1% each and publishes 158,556 verified pull outcomes; Courtyard posts an exact expected value on every pack. Against that, the biggest brand in the business asks you to take the pack on trust.</p>

  <p>The company has framed the product as bringing consistency and professionalism to repacks, which is a reasonable ambition. Publishing pull rates is the cheapest available way to demonstrate it.</p>

  <h2>Where Fanatics is genuinely best in class</h2>
  <p>Card valuations come from Card Ladder, a third-party sales-data service, rather than from Fanatics itself.</p>
  <p>This matters more than it sounds. On Courtyard, Packz and Arena Club, the company paying the buyback also decides what the card is worth, and Arena Club additionally grades some of its own inventory. Every expected value on those platforms rests on a number the platform set. Fanatics outsources that number to a dataset anyone can check. Of the twenty-four platforms we track, it is the only one to remove that conflict, and it deserves credit for it even while it publishes no odds at all.</p>

  <h2>Pack prices</h2>
  <div class="table-wrap">
  <table class="plain">
  <caption>Category price ranges as listed on the Instant Rips page, {collected}. Individual packs are not named at the category level.</caption>
  <thead><tr><th scope="col">Category</th><th scope="col" class="num">Price range</th></tr></thead>
  <tbody>
    <tr><th scope="row">Collector Packs</th><td class="num">$10 &ndash; $100</td></tr>
    <tr><th scope="row">Football</th><td class="num">$100 &ndash; $1,000</td></tr>
    <tr><th scope="row">Basketball</th><td class="num">$100 &ndash; $1,000</td></tr>
    <tr><th scope="row">Baseball</th><td class="num">$50 &ndash; $1,000</td></tr>
    <tr><th scope="row">Pok&eacute;mon</th><td class="num">$25 &ndash; $2,500</td></tr>
  </tbody>
  </table>
  </div>

  <p>The debut Odyssey series was 1,000 baseball repacks at $250 each, one graded card per pack, with a reported value floor of about $90 and a ceiling of about $3,800. That floor is 36% of the pack price, which sits between Packz at 50% and Crown Rips at 30%. A worst-case pull taken as an instant offer returns about $76, or 30% of what the pack cost.</p>

  <h2>Fees and logistics</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Instant offer rate</th><td>90% of Card Ladder value, less a 6% marketplace fee, so 84.6% effective</td></tr>
    <tr><th scope="row">Offer window</th><td>48 hours after the pull</td></tr>
    <tr><th scope="row">Offer payout</th><td>Fanatics Live credits, not withdrawable as cash</td></tr>
    <tr><th scope="row">Cash route</th><td>List the card on the Fanatics Collect marketplace</td></tr>
    <tr><th scope="row">Fulfillment or shipping</th><td>1% to 3% of asset value; 3 to 15 business days</td></tr>
    <tr><th scope="row">Vault storage</th><td>Free, no time limit</td></tr>
    <tr><th scope="row">Withdrawal</th><td>ACH free; wire $50</td></tr>
    <tr><th scope="row">Card sourcing</th><td>Card shows, collectors' vaulted cards, and PSA</td></tr>
    <tr><th scope="row">Odds disclosure</th><td>Checklist only; no pull rates published</td></tr>
  </tbody>
  </table>
  </div>

  <p>The free, unlimited vault storage is worth noting against <a href="/platforms/crown-rips/">Crown Rips</a>, where a card left in the vault is reportedly auto-sold after seven days. Holding a card at Fanatics costs nothing and carries no deadline.</p>

  <div class="callout">
    <h3>What we still need</h3>
    <p>Pull rates, for any pack. Until Fanatics publishes probabilities, nobody can state an expected value for an Instant Rips pack, including Fanatics. We would also like to confirm whether the 6% marketplace fee applies uniformly across price points, and whether the dynamic checklist has shipped. If you have screenshots of a live Instant Rips pack page showing anything resembling odds, we would like to see them.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/platforms/clutch-packs/">Clutch Packs</a>, the opposite approach: 158,556 published pull outcomes</li>
    <li><a href="/platforms/">Compare all twenty-four platforms</a></li>
    <li><a href="/calculator/">Pack EV calculator</a></li>
  </ul>
</div>
""".format(collected=CLUTCH_COLLECTED, faq=faq_html, **{"flags_fanatics_instant_rips": flag_row("fanatics-instant-rips")})

    return pages_written("/platforms/fanatics-instant-rips/", page(
        "/platforms/fanatics-instant-rips/",
        "Fanatics Instant Rips review — the 90% offer is really 84.6%",
        "Fanatics advertises a 90% instant offer, but its own example nets 84.6% after a 6% fee, paid in credits you cannot withdraw. No pull rates are published for any pack.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"),
                (None, "Fanatics Instant Rips")],
        updated=CLUTCH_COLLECTED, structured=faq_ld))


def build_clutch():
    s = clutch_stats()
    rows = []
    for cat, name, price, pulls, avg, bands in CLUTCH_PACKS:
        mult = avg / price
        cls = "pos" if mult >= 1 else "neg"
        thin = ' title="Fewer than 500 pulls — the tail is not measurable at this sample size"' if pulls < 500 else ""
        rows.append(
            '<tr><td class="name">%s %s</td><td>%s</td><td class="num">%s</td>'
            '<td class="num"%s>%s</td><td class="num">%s</td>'
            '<td class="num"><strong class="%s">%.2f&times;</strong></td>'
            '<td class="num">%s</td><td class="num">%s</td></tr>' % (
                E(cat), E(name), E(cat), money(price), thin, "{:,}".format(pulls),
                money(avg), cls, mult,
                pct(bands[4] + bands[5], 1), pct(bands[0] + bands[1] + bands[2], 1)))

    band_rows = []
    for cat, name, price, pulls, avg, bands in CLUTCH_PACKS:
        band_rows.append(
            '<tr><td class="name">%s %s</td>' % (E(cat), E(name))
            + "".join('<td class="num">%s</td>' % pct(b, 1) for b in bands)
            + "</tr>")

    faq_html, faq_ld = faq_block([
        ("What is the expected value of a Clutch Packs pack?",
         "<p>Across %s verified pulls on %d packs, the pull-weighted average return is %.2f times the pack price. That is the only observed, as opposed to claimed, average return we have for any platform, because Clutch Packs records every pack opening on the Polygon blockchain and reports real pull values rather than its own valuations. Individual packs range from %.2f to %.2f times, though the packs at the extremes have small samples.</p>" % ("{:,}".format(s["pulls"]), s["n_packs"], s["w_avg"], s["min_mult"], s["max_mult"])),
        ("Do most Clutch Packs pulls make money?",
         "<p>No. Weighted across all recorded pulls, %s return less than the pack price and only %s return double or more. A near-100%% average return and a %s chance of losing money are not contradictory: the average is carried by a thin tail of large pulls, while the typical result is a card worth well under half what the pack cost.</p>" % (pct(s["below_1x"], 0), pct(s["at_2x"], 1), pct(s["below_1x"], 0))),
        ("How do Clutch Packs odds work?",
         "<p>Each pack page lists a pool of 100 cards at 1% each, grouped into four tiers. On the $100 Multisport Ascent pack that is 2 Epics at 2% combined, 6 Chasers at 6%, 15 Hits at 15% and 77 Commons at 77%. It is the clearest odds structure of any platform we track, because every card is equally likely and the tier percentages are simply the card counts.</p>"),
        ("Is the Clutch Packs average inflated by jackpots?",
         "<p>On two packs, yes, and the arithmetic is checkable. A single $130,000 Series Hit appears as the maximum on both the Multisport Ascent and Multisport Moonshot packs. Spread across Ascent's 21,127 recorded pulls that one card adds $6.15 to the average, which is 6.2% of the $100 pack price, so Ascent's stated 1.07 times becomes about 1.00 times without it. On Moonshot, with only 1,102 pulls, it adds $117.97, or 4.7% of the price. Every other pack's average sits close to 1.00 times without needing a jackpot to get there.</p>"),
        ("Does Clutch Packs buy cards back?",
         "<p>Not that it discloses. We found no buyback or sell-back terms on the pack pages or the transparency page, which is the one significant gap in otherwise category-leading disclosure. Since buyback quality is a quarter of our score, and the difference between withdrawable cash and site credit has mattered on every other platform, this needs answering before Clutch Packs can be rated.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Clutch Packs: {pulls} verified pulls, and what they actually show</h1>
    <p class="lede">Clutch Packs records every pack opening on the Polygon blockchain and publishes the results. It is the only platform we track that reports what buyers actually pulled rather than what the platform says its cards are worth.</p>
    {flags_clutch_packs}
  </div>

  <div class="finding">
    <p class="big">Across {pulls} verified pulls on {npacks} packs, the pull-weighted average return is {wavg:.2f} times the pack price &mdash; effectively break-even, against Courtyard's claimed 95%. But {below} of those pulls returned less than the pack price, and only {at2x} returned double or more. The average is real; it is carried by a thin tail.</p>
    <p class="small muted">Figures read from the Clutch Packs transparency page on {collected}. Unlike every other number on this site, these are observed results rather than published odds.</p>
  </div>

  <div class="stats">
    <div class="stat"><b>{pulls}</b><span>Pulls verified on-chain</span></div>
    <div class="stat"><b class="pos">{wavg:.2f}&times;</b><span>Pull-weighted average return</span></div>
    <div class="stat"><b class="neg">{below}</b><span>Of pulls worth less than the pack</span></div>
    <div class="stat"><b>{at2x}</b><span>Of pulls worth double or more</span></div>
  </div>

  <h2>Why this is different from every other platform</h2>
  <p>Courtyard publishes an expected value it calculates from its own card valuations. Packz publishes value ranges that have to be turned into an estimate. Arena Club and Crown Rips publish no values at all. All of those are claims about what a pack should return.</p>

  <p>Clutch Packs publishes an average drawn from recorded pulls, valued at the market price of the card when it was pulled, with a count of openings verified on Polygon against each figure. That is a materially stronger form of disclosure, because it cannot be quietly adjusted by revaluing inventory, and because anyone can in principle audit the chain. It is the single best disclosure practice we have found in this category, and it is worth saying so plainly.</p>

  <p>It is not immune to scrutiny, though, and three things are worth understanding before taking the headline at face value.</p>

  <h3>1. Most pulls still lose money</h3>
  <p>A {wavg:.2f} times average and a {below} chance of losing money are not in conflict. Weighted across all recorded pulls, {below} came back worth less than the pack price and roughly half of all pulls landed in the bottom band at under half the price. Only {at2x} doubled. If you buy one pack, the most likely single outcome by a wide margin is a card worth a fraction of what you paid; the average describes a buyer who opens thousands.</p>

  <h3>2. Two packs are carried by one $130,000 card</h3>
  <p>A single $130,000 Series Hit, a 2000 Bowman Chrome Tom Brady Refractor, appears as the maximum recorded pull on both the Multisport Ascent and Multisport Moonshot packs. On Ascent, spread across 21,127 recorded pulls, that one card contributes $6.15 to the average, which is 6.2% of the $100 pack price. Strip it out and Ascent's stated 1.07 times becomes about 1.00 times. On Moonshot it adds $117.97 across 1,102 pulls.</p>
  <p>Those are the two highest-returning packs on the board, and they are the two that happened to produce the jackpot. Every other pack sits close to 1.00 times without one. This is not a criticism of the disclosure, which is what makes the check possible in the first place, but it does mean the top of the table is luck rather than a better pack.</p>

  <h3>3. The thin samples tell you nothing about the tail</h3>
  <p>Pull counts range from 69,558 on Multisport Liftoff down to 127 on Football Galaxy. With a roughly 0.4% chance of a 10x-or-better pull, a 127-pull sample is expected to contain fewer than one. Basketball Ascent's 1.13 times on 260 pulls and Soccer Orbit's 0.92 times on 164 pulls are both noise, and treating either as a verdict on the pack would be a mistake. We have flagged every pack below 500 pulls in the table.</p>

  <h2>Every pack, by observed return</h2>
  <div class="table-wrap">
  <table>
  <caption>Observed results from the Clutch Packs transparency page, read {collected}. Packs under 500 pulls are too thinly sampled to judge.</caption>
  <thead><tr>
    <th scope="col">Pack</th><th scope="col">Category</th><th scope="col" class="num">Price</th>
    <th scope="col" class="num">Verified pulls</th><th scope="col" class="num">Average pull</th>
    <th scope="col" class="num">Return</th><th scope="col" class="num">Under 1&times;</th>
    <th scope="col" class="num">2&times; or better</th>
  </tr></thead>
  <tbody>{rows}</tbody>
  </table>
  </div>

  <h2>Full value distribution</h2>
  <p>The shape matters more than the average. Note how much of every pack sits in the bottom two bands.</p>
  <div class="table-wrap">
  <table>
  <caption>Share of recorded pulls by value band, as published. The bottom band's label varies between packs, from 0.1x to 0.2x at its lower edge.</caption>
  <thead><tr><th scope="col">Pack</th>{bandhead}</tr></thead>
  <tbody>{bandrows}</tbody>
  </table>
  </div>

  <h2>Pack odds: a flat 100-card pool</h2>
  <p>Alongside the observed results, each pack page lists its card pool with per-tier odds. On the $100 Multisport Ascent pack the pool is 100 cards, each at 1%:</p>
  <div class="table-wrap">
  <table class="plain">
  <caption>Multisport Ascent ($100) card pool, as listed on the pack page.</caption>
  <thead><tr><th scope="col">Tier</th><th scope="col" class="num">Cards</th><th scope="col" class="num">Combined odds</th></tr></thead>
  <tbody>
    <tr><th scope="row">Epics</th><td class="num">2</td><td class="num">2.00%</td></tr>
    <tr><th scope="row">Chasers</th><td class="num">6</td><td class="num">6.00%</td></tr>
    <tr><th scope="row">Hits</th><td class="num">15</td><td class="num">15.00%</td></tr>
    <tr><th scope="row">Commons</th><td class="num">77</td><td class="num">77.00%</td></tr>
  </tbody>
  </table>
  </div>
  <p>This is the cleanest odds structure of any platform we track. Every card is equally likely, the tier percentages are just the card counts, and the pool is enumerated rather than summarised. Compare Arena Club, where you must add up dozens of individual per-card rates to learn your chance at a tier.</p>

  <p>The pack page also states a $20 floor and a $1,000 chaser ceiling on Ascent, which puts its guaranteed minimum at 20% of the pack price. That is low by the standards of Courtyard, whose standard packs floor at around 70%, and Packz at 50%, though it is not as low as Crown Rips.</p>

  <div class="callout">
    <h3>Where the pack page and the transparency page disagree</h3>
    <p>The Ascent pack page gives an average value of $100 and a chaser ceiling of $1,000. The transparency page gives an average of $106.61 and a maximum of $130,000 for the same pack. Both can be true: the Series Hits, which the pack page says can land in any Launch Series pack at any time, appear to sit outside the enumerated 100-card pool. A buyer reading only the pack page would not know the ceiling is 130 times higher than stated, or that the recorded average is above the stated one.</p>
  </div>

  <div class="callout danger">
    <h3>No buyback terms are disclosed</h3>
    <p>We could find no sell-back or buyback terms on the pack pages or the transparency page. On every other platform we track, this is where the headline return gets eroded: Courtyard's 90% advertised rate, Packz's 90% in non-withdrawable credit, Arena Club's 90% to a withdrawable wallet. A near-break-even average return means very different things depending on whether you can convert a card to money at 100%, at 90%, or only into more packs.</p>
    <p>Until that is answered, Clutch Packs cannot be scored, however good its odds disclosure is.</p>
  </div>

  <h2>What we still need</h2>
  <ul>
    <li><strong>Buyback terms</strong>, the rate and whether proceeds are withdrawable.</li>
    <li><strong>Whether Series Hits sit inside or outside the 100-card pool</strong>, and what their odds are. They are the difference between a $1,000 ceiling and a $130,000 one.</li>
    <li><strong>How card values are set</strong> at the moment of a pull, and from which market data.</li>
    <li><strong>Whether the on-chain record is independently auditable</strong> in practice, not just minted. A record anyone can verify is far stronger than one only the platform can read.</li>
    <li><strong>Shipping terms and fees</strong>, which are undisclosed.</li>
  </ul>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/platforms/">Compare all twenty-four platforms</a></li>
    <li><a href="/platforms/courtyard/">Courtyard</a>, the only other platform that publishes a return figure</li>
    <li><a href="/methodology/">How we rate platforms</a></li>
  </ul>
</div>
""".format(pulls="{:,}".format(s["pulls"]), npacks=s["n_packs"],
           wavg=s["w_avg"], below=pct(s["below_1x"], 0),
           at2x=pct(s["at_2x"], 1), collected=CLUTCH_COLLECTED,
           rows="".join(rows), bandrows="".join(band_rows),
           bandhead="".join('<th scope="col" class="num">%s</th>' % b
                            for b in CLUTCH_BAND_LABELS),
           faq=faq_html, **{"flags_clutch_packs": flag_row("clutch-packs")})

    ds = jsonld({
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "Clutch Packs observed pull results",
        "description": "Observed average return, pull counts and value distribution for %d Clutch Packs packs, covering %s pack openings verified on the Polygon blockchain." % (s["n_packs"], "{:,}".format(s["pulls"])),
        "url": BASE_URL + "/platforms/clutch-packs/",
        "dateModified": CLUTCH_COLLECTED,
        "creator": {"@type": "Organization", "name": SITE_NAME},
        "license": "https://creativecommons.org/licenses/by/4.0/",
    })

    return pages_written("/platforms/clutch-packs/", page(
        "/platforms/clutch-packs/",
        "Clutch Packs odds and real returns — %s verified pulls analysed" % "{:,}".format(s["pulls"]),
        "Clutch Packs publishes observed pull results on-chain. Across %s verified pulls the average return is %.2f times the pack price, but %s of pulls return less than the pack cost." % ("{:,}".format(s["pulls"]), s["w_avg"], pct(s["below_1x"], 0)),
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "Clutch Packs")],
        updated=CLUTCH_COLLECTED, structured=[faq_ld, ds]))


def build_crown_rips():
    rows = []
    for name, price, lo, hi in CROWN_RIPS_PACKS:
        rows.append(
            '<tr><td class="name">%s Pack</td><td class="num">%s</td>'
            '<td class="num">%s</td><td class="num"><strong>%s</strong></td>'
            '<td class="num">%s</td><td class="num">%s</td></tr>' % (
                E(name), money(price), money(lo), pct(lo / price * 100, 0),
                money(hi), ("%.1f&times;" % (hi / price)).replace(".0&times;", "&times;")))

    floors = [lo / p for _, p, lo, _ in CROWN_RIPS_PACKS]

    faq_html, faq_ld = faq_block([
        ("What is Crown Rips?",
         "<p>Crown Rips is a digital card ripping feature inside Crown Coins Casino, a sweepstakes casino. It opened as a 500-person beta announced on 27 July 2026, with selected existing customers given early access. Users open mystery packs of sports and Pok&eacute;mon cards and can keep a card in a vault, have the physical card shipped, or sell it back.</p>"),
        ("What is the expected value of a Crown Rips pack?",
         "<p>It cannot be calculated. Crown Rips publishes a minimum and maximum pull value for each pack but no pull rates or probabilities, so there is no way to work out an average. The platform's marketing promises &ldquo;no dead pulls&rdquo; but publishes no numbers behind that. Crown Rips is one of five platforms we track whose expected value a buyer cannot determine before spending.</p>"),
        ("What are the Crown Rips pack prices?",
         "<p>Reporting from the beta lists ten Pok&eacute;mon packs: Starter at $1, Basic at $5, Signature at $10, Bronze at $25, Silver at $50, Gold at $100, Sapphire at $250, Amethyst at $500, Ultimate at $1,000 and Diamond at $2,500. The $1 Starter pack is the cheapest entry point of any platform we track, where the next cheapest is Packz at $5.</p>"),
        ("Does Crown Rips really buy cards back at 100%?",
         "<p>Crown Coins has said users can sell cards back for 100% of fair market value, which would be the best buyback in the category against the 90% offered by Courtyard, Packz and Arena Club. We have not verified it. Two things need checking first: what Crown Rips treats as fair market value, since the platform sets that figure itself, and what form the proceeds take, because the phrasing that proceeds can fund future pack purchases is the same language Packz uses for credit that cannot be withdrawn.</p>"),
        ("What happens to cards left in the Crown Rips vault?",
         "<p>Reporting from the beta says cards sit in the vault for seven days and are then automatically sold back at market value. If accurate, that is the most consequential term on the platform and the one least like its competitors: Courtyard and Arena Club vault cards indefinitely, so holding a card is a decision you make rather than a deadline you have to meet. Confirm it against the current terms before buying a pack you intend to hold.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Crown Rips: pack prices, floors and what is not disclosed</h1>
    <p class="lede">Crown Rips is the card ripping feature inside Crown Coins Casino, launched as a 500-person beta in July 2026. It is the only platform we track that sells rips inside a sweepstakes casino, and the only one with a $1 pack.</p>
    {flags_crown_rips}
  </div>

  <div class="finding">
    <p class="big">Crown Rips publishes a minimum and maximum pull value for every pack but no pull rates at all, so its expected value cannot be calculated. On the figures reported from the beta its disclosed floor is the lowest of any platform we track: most packs guarantee only {modal} of the pack price, against 50% on Packz and roughly 70% on a standard Courtyard pack.</p>
    <p class="small muted">Pack figures reported from the beta, {reported}. Unlike the Courtyard and Packz data on this site, we have not yet collected these from the platform ourselves.</p>
  </div>

  <div class="callout">
    <h3>How this page differs from our others</h3>
    <p>Everything on our <a href="/platforms/courtyard/">Courtyard</a> and <a href="/platforms/packz/">Packz</a> pages was collected directly from those platforms' own pack pages. Crown Rips is in a closed beta, so the pack figures below come from reporting rather than our own collection, and we publish no return figure for it. We will replace this with a first-hand collection when the platform opens up. <a href="/methodology/">Our methodology</a> explains why that distinction matters.</p>
  </div>

  <h2>Pack prices and disclosed range</h2>
  <p>The Pok&eacute;mon store reportedly lists ten packs, each with a fixed price and a stated minimum and maximum pull value. There are no probabilities attached to either end, so the range tells you what is possible rather than what is likely.</p>

  <div class="table-wrap">
  <table>
  <caption>Crown Rips Pok&eacute;mon packs as reported from the beta, {reported}. Floor and ceiling are our arithmetic on the reported minimum and maximum.</caption>
  <thead><tr>
  <th scope="col">Pack</th><th scope="col" class="num">Price</th>
  <th scope="col" class="num">Minimum pull</th><th scope="col" class="num">Floor, as % of price</th>
  <th scope="col" class="num">Maximum pull</th><th scope="col" class="num">Ceiling</th>
  </tr></thead>
  <tbody>{rows}</tbody>
  </table>
  </div>

  <h2>The floor is the story</h2>
  <p><strong>A {modal} floor is low for this category.</strong> It means a worst-case pull on a $100 Gold pack returns a card valued at $30. For comparison, the lowest tier on a standard Courtyard pack starts at about 70% of the price, and Packz guarantees 50% on every pack of $25 and up. Crown Rips is closer to Courtyard's high-variance Spicy packs, which start at around half the price, except that it applies at every price point rather than as an opt-in.</p>

  <p><strong>The cheapest packs are the worst, again.</strong> The $1 Starter pack guarantees only {starter} of its price and the $5 Basic pack {basic}. This is the same pattern we found on Packz, where the $5 and $10 packs have materially worse floors than the rest of the range. On both platforms the pack a newcomer is most likely to try first is the one with the least protection.</p>

  <p><strong>A low floor is not automatically a bad deal.</strong> Floor and average are different things, and a pack can combine a low floor with a reasonable expected value if the middle tiers are generous. That is exactly what the pull rates would tell you, and exactly what Crown Rips does not publish.</p>

  <h2>Volatility settings</h2>
  <p>Crown Rips reportedly offers three volatility settings on each pack, labelled something like Normal, High and Max, where a higher setting raises the chance of rare cards and also the chance of the lowest-value pulls. No platform we track offers anything comparable, and as a feature it is an honest acknowledgment that variance is a separate dial from value.</p>
  <p>It also multiplies the disclosure problem. Ten packs with three settings each is thirty distinct probability distributions, none of which has published rates. A buyer choosing Max over Normal has no way to see what they are trading.</p>

  <div class="callout danger">
    <h3>Cards in the vault may be sold automatically after seven days</h3>
    <p>Reporting from the beta says a card left in the vault is automatically sold back at market value after seven days. If that holds, it is the single most important term on the platform. Courtyard and Arena Club vault cards indefinitely, so keeping a card is a decision; here it would be a deadline, and a card you wanted to keep could be liquidated at a value the platform sets while you were not looking.</p>
    <p>We have not confirmed this against Crown Rips' own terms. If you are in the beta, check it before buying a pack you intend to hold.</p>
  </div>

  <h2>Why a sweepstakes casino is doing this</h2>
  <p>Crown Rips is the only platform we track that sits inside a sweepstakes casino rather than operating as a standalone retail business, and that is worth understanding rather than treating as a detail. Sweepstakes operators are built around a promotional-currency model with a no-purchase-necessary route, which is the structure they rely on to sit outside conventional gambling licensing.</p>

  <p>Dropping a rip product into that framework is a plausible answer to the legal exposure described on our <a href="/is-card-ripping-gambling/">gambling page</a>, where plaintiffs have argued that paying money for a random prize of uncertain value amounts to an unlicensed lottery. Whether it works is untested, and it may cut the other way: a product already operating under a gambling-adjacent licence may find it harder to argue it is simply retail.</p>

  <p>Reporting conflicts on a basic point here. Some coverage describes packs being opened with Sweeps Cash, the promotional virtual currency used for the casino games, while beta coverage describes players loading real cash in dollars specifically for Crown Rips. That distinction decides whether a pack has a dollar price at all, and therefore whether an expected value can ever be stated in dollars. We are not guessing at it.</p>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>Crown Coins Casino, a sweepstakes casino</td></tr>
    <tr><th scope="row">Status</th><td>500-person closed beta, announced 27 July 2026; wider rollout expected but undated</td></tr>
    <tr><th scope="row">Categories</th><td>Pok&eacute;mon and multi-sport cards</td></tr>
    <tr><th scope="row">Pack prices</th><td>Ten Pok&eacute;mon packs reported from $1 to $2,500</td></tr>
    <tr><th scope="row">Odds disclosure</th><td>Minimum and maximum pull value per pack; no pull rates or probabilities</td></tr>
    <tr><th scope="row">Expected value</th><td>Not published and not calculable</td></tr>
    <tr><th scope="row">Volatility settings</th><td>Three per pack, reportedly</td></tr>
    <tr><th scope="row">Buyback</th><td>Claimed at 100% of fair market value; form of proceeds unconfirmed</td></tr>
    <tr><th scope="row">Vault</th><td>Reportedly auto-sells after seven days</td></tr>
    <tr><th scope="row">Shipping</th><td>Physical cards can be shipped; fees and timelines not published</td></tr>
    <tr><th scope="row">Age</th><td>18+ per the site's promotional terms</td></tr>
  </tbody>
  </table>
  </div>

  <h2>What we still need</h2>
  <ul>
    <li><strong>Pull rates, if any exist in the beta.</strong> Without them there is no expected value, and Crown Rips sits with Arena Club as a platform a buyer cannot evaluate.</li>
    <li><strong>What the buyback actually pays, and in what.</strong> A genuine 100% in withdrawable money would be the best terms in the category; 100% in packs-only credit would not.</li>
    <li><strong>Whether the seven-day vault auto-sale is real</strong>, and whether it applies to cards you have paid to vault.</li>
    <li><strong>Whether packs cost dollars or Sweeps Cash</strong>, which the current reporting disagrees on.</li>
  </ul>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/platforms/">Compare all twenty-four platforms</a></li>
    <li><a href="/is-card-ripping-gambling/">Why the sweepstakes framing matters</a></li>
  </ul>
</div>
""".format(rows="".join(rows), reported="27 July 2026",
           modal="30%", starter=pct(floors[0] * 100, 0),
           basic=pct(floors[1] * 100, 0), faq=faq_html, **{"flags_crown_rips": flag_row("crown-rips")})

    return pages_written("/platforms/crown-rips/", page(
        "/platforms/crown-rips/",
        "Crown Rips pack prices and odds — what Crown Coins does not disclose",
        "Crown Rips publishes a minimum and maximum pull value per pack but no pull rates, so its expected value cannot be calculated. Pack prices from $1 to $2,500 and the lowest disclosed floor of any platform we track.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "Crown Rips")],
        updated=COLLECTED, structured=faq_ld))


def build_compare():
    faq_html, faq_ld = faq_block([
        ("Is Courtyard or Packz better value?",
         "<p>On the published numbers Packz looks better, at about %s of the pack price against Courtyard's 95%%, but the comparison is not like for like. Courtyard publishes an exact expected value and commits to it. The Packz figure is our own estimate, calculated from value ranges and resting on Packz's own card valuations, with a span of roughly %s to %s depending on where cards actually sit in each range. Courtyard also lets you withdraw a buyback while Packz pays only in site credit. A committed 95%% that converts to cash is arguably worth more than an estimated 100%% that does not.</p>" % (pct(PZ_STD_MID * 100, 0), pct(pz_std[0]["ratio_low"] * 100, 0), pct(pz_std[0]["ratio_high"] * 100, 0))),
        ("Which platform has better odds of beating the pack price?",
         "<p>Packz, consistently. Every Packz pack gives a %s chance of a card worth at least the pack price, because all its packs use the same odds template. Courtyard's packs range from %s to %s depending on which pack you choose, so the best Courtyard packs beat Packz on this measure and the worst are well behind it.</p>" % (pct(PZ_HIT, 1), pct(CY_HIT_LO, 0), pct(CY_HIT_HI, 0))),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Courtyard vs Packz</h1>
    <p class="lede">The two platforms that publish enough for their packs to be compared directly, and the ways in which that comparison is not as simple as the headline numbers suggest.</p>
  </div>

  <div class="finding">
    <p class="big">Packz's published odds imply a better return than Courtyard's, about {pzstd} of the pack price against 95%. But Courtyard commits to an exact figure while the Packz number is an estimate from value ranges, and Courtyard's buyback can be withdrawn while Packz's pays only in site credit.</p>
    <p class="small muted">Both datasets collected {collected}.</p>
  </div>

  <div class="table-wrap">
  <table class="plain">
  <caption>Courtyard and Packz compared on what each actually publishes, {collected}.</caption>
  <thead><tr><th scope="col"></th><th scope="col">Courtyard</th><th scope="col">Packz</th></tr></thead>
  <tbody>
    <tr><th scope="row">Packs measured</th><td>{cyn}</td><td>{pzn}</td></tr>
    <tr><th scope="row">Price range</th><td>{cymin}&ndash;{cymax}</td><td>$5&ndash;$1,000</td></tr>
    <tr><th scope="row">Stated return, $25+ packs</th><td><strong>95&ndash;96%</strong>, published by Courtyard</td><td><strong>~{pzstd}</strong>, our estimate</td></tr>
    <tr><th scope="row">Cheapest packs</th><td>95% on the $15 packs</td><td>{com} on $5, {unc} on $10</td></tr>
    <tr><th scope="row">How value is disclosed</th><td>Exact expected value on every pack</td><td>Dollar value ranges only</td></tr>
    <tr><th scope="row">Odds structure</th><td>Varies by pack</td><td>One template across all packs</td></tr>
    <tr><th scope="row">Chance of &ge; pack price</th><td>{cyhitlo}&ndash;{cyhithi}, depending on the pack</td><td>{pzhit} on every pack</td></tr>
    <tr><th scope="row">Buyback rate</th><td>90% advertised; independently measured nearer 85%</td><td>90%, or 100% on a first pack up to $100</td></tr>
    <tr><th scope="row">Buyback payout</th><td>Settles in USDC</td><td>Site credit that cannot be withdrawn</td></tr>
    <tr><th scope="row">Categories</th><td>Cards, comics, coins, watches, sneakers</td><td>Sports and Pok&eacute;mon</td></tr>
    <tr><th scope="row">Availability</th><td>Not restricted to the US</td><td>United States only, 18+</td></tr>
  </tbody>
  </table>
  </div>

  <h2>Why the headline comparison is misleading</h2>
  <p><strong>One number is a commitment, the other is an inference.</strong> Courtyard states an expected value on each pack page. If that figure is wrong, it is wrong in public and against a specific claim. Packz publishes only the bands a card might fall into, so its return has to be estimated, and depending on where cards actually sit within those ranges the true figure could be anywhere from {pzlo} to {pzhi} of the price.</p>

  <p><strong>Both figures rest on the platforms' own valuations.</strong> Neither number has been checked against what the cards actually sell for. This is the single biggest open question on this site, and it is the next thing we are testing.</p>

  <p><strong>Credit is not cash.</strong> A 90% buyback paid in withdrawable funds and a 90% buyback paid in packs-only credit are different products. On Packz the credit can only be spent on more packs, so a sell-back is really a re-roll rather than a refund.</p>

  <h2>Which to pick, on the evidence so far</h2>
  <p>If you want the most checkable information before you spend, Courtyard is the only one of the two that commits to a number. If you want the best chance of a pull that beats the pack price, Packz's {pzhit} is better than most Courtyard packs, though the best Courtyard packs beat it. If you expect to sell cards back for money rather than more packs, Packz's credit-only buyback is a significant disadvantage.</p>

  <p>Avoid the $5 and $10 Packz packs specifically. They are the only packs on either platform with a materially worse return than their stablemates, and they are the ones a newcomer is most likely to try first.</p>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Go deeper</h2>
  <ul>
    <li><a href="/platforms/courtyard/">All {cyn} Courtyard packs</a></li>
    <li><a href="/platforms/packz/">All {pzn} Packz packs</a></li>
    <li><a href="/calculator/">Compare any two packs yourself</a></li>
  </ul>
</div>
""".format(cyn=CY_N, pzn=PZ_N, pzstd=pct(PZ_STD_MID * 100, 0),
           cymin=money(CY_MIN_PRICE), cymax=money(CY_MAX_PRICE),
           com=pct(PZ_COMMON["ratio_mid"] * 100, 0),
           unc=pct(PZ_UNCOMMON["ratio_mid"] * 100, 0),
           cyhitlo=pct(CY_HIT_LO, 0), cyhithi=pct(CY_HIT_HI, 0),
           pzhit=pct(PZ_HIT, 1), collected=COLLECTED,
           pzlo=pct(pz_std[0]["ratio_low"] * 100, 0),
           pzhi=pct(pz_std[0]["ratio_high"] * 100, 0), faq=faq_html)

    return pages_written("/compare/courtyard-vs-packz/", page(
        "/compare/courtyard-vs-packz/",
        "Courtyard vs Packz — odds, expected value and buyback compared",
        "Packz's odds imply about %s back against Courtyard's posted 95%%, but one figure is a published commitment and the other an estimate, and only one buyback pays withdrawable money." % pct(PZ_STD_MID * 100, 0),
        body,
        crumbs=[("/", "Home"), (None, "Courtyard vs Packz")],
        updated=COLLECTED, structured=faq_ld))


def build_calculator():
    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Pack EV calculator</h1>
    <p class="lede">Enter the odds any ripping site publishes and see what a pack is actually worth: the average card value, the expected loss per pack, and your chance of beating the price. Runs entirely in your browser, no account needed.</p>
  </div>

  <div class="calc">
    <div class="calc-grid">
      <label class="field">Pack price ($)
        <input type="number" id="price" min="0" step="0.01" value="50">
      </label>
      <label class="field">Buyback rate (%)
        <input type="number" id="buyback" min="0" max="100" step="0.5" value="90">
      </label>
    </div>

    <table class="tier-table">
      <thead><tr><th scope="col">Card value ($)</th><th scope="col">Odds (%)</th><th><span style="position:absolute;left:-9999px">Remove</span></th></tr></thead>
      <tbody id="tierBody"></tbody>
    </table>
    <p class="odds-note" id="oddsNote" aria-live="polite"></p>

    <div class="btn-row">
      <button class="btn" type="button" id="addTier">Add tier</button>
      <button class="btn" type="button" id="loadPackz">Packz $25 Starter</button>
      <button class="btn" type="button" id="loadCourtyard">Courtyard $50 Pok&eacute;mon Pro</button>
      <button class="btn" type="button" id="clearTiers">Clear</button>
    </div>

    <div class="result" aria-live="polite">
      <div class="result-inner">
        <div class="metric wide"><b id="evOut">$0</b><span>Average card value per pack</span></div>
        <div class="metric"><b id="retOut">0%</b><span>Return on the pack price</span></div>
        <div class="metric"><b id="bbOut">$0</b><span>Average cash back if you sell every card back</span></div>
        <div class="metric"><b id="lossOut">$0</b><span>Average gain or loss per pack, selling back</span></div>
        <div class="metric"><b id="tenOut">$0</b><span>Over ten packs, selling back</span></div>
        <div class="metric"><b id="hitOut">0%</b><span>Chance of a card worth more than the pack price</span></div>
        <p class="verdict-line" id="verdict">Add value tiers to see the maths.</p>
      </div>
    </div>
  </div>

  <h2>How to use it</h2>
  <p>Most ripping sites publish odds as dollar ranges rather than exact values, for example a 44% chance of a card worth $12.50 to $17.50. To use a range, enter its midpoint. Bear in mind that real card values tend to cluster toward the bottom of a range, because cheap cards are more numerous than expensive ones, so a midpoint estimate is usually slightly optimistic.</p>

  <p>The calculator checks that your odds add up to 100% and will tell you if they do not. If a site's published odds do not total 100%, that is usually display rounding on the smallest tiers rather than an error.</p>

  <h3>What each number means</h3>
  <ul>
    <li><strong>Average card value</strong> is the expected value: each tier's value multiplied by its probability, summed. It is what you would average per pack over a very large number of packs.</li>
    <li><strong>Return</strong> expresses that as a percentage of the price. Below 100% means the pack loses money on average, which is true of every pack we have measured.</li>
    <li><strong>Average cash back</strong> applies the buyback rate. This is the number that matters if you intend to sell cards back rather than keep them. Check whether a platform's buyback pays withdrawable money or site credit, because they are not equivalent.</li>
    <li><strong>Chance of beating the price</strong> is how often a single pack produces a card worth more than it cost. It has nothing to do with the average, and two packs with the same expected value can differ enormously here.</li>
  </ul>

  <div class="callout">
    <h3>What the calculator cannot tell you</h3>
    <p>It works from the values a platform publishes. If those valuations are higher than what the cards actually sell for, every figure it produces is correspondingly optimistic. Expected value also describes long-run averages, not your next pack: on a pack with a 1-in-1,000 top tier, almost every individual result will look nothing like the average.</p>
  </div>
</div>

<script>
(function(){
  var tierBody=document.getElementById('tierBody');
  var PRESETS={
    packz:{price:25,buyback:90,tiers:[[15,44],[21.25,25.6],[31.25,19],[50,9.5],[93.75,1.5],[187.5,0.3],[375,0.1]]},
    courtyard:{price:50,buyback:90,tiers:[[40,62],[47.5,16],[75,20],[150,2],[500,0.1]]}
  };

  function addTier(v,o){
    var tr=document.createElement('tr');
    tr.innerHTML='<td><input type="number" min="0" step="0.01" aria-label="Card value in dollars" value="'+(v===undefined?'':v)+'"></td>'+
      '<td><input type="number" min="0" max="100" step="0.01" aria-label="Odds in percent" value="'+(o===undefined?'':o)+'"></td>'+
      '<td><button class="icon-btn" type="button" aria-label="Remove tier">&times;</button></td>';
    tr.querySelector('button').addEventListener('click',function(){tr.remove();calc();});
    tr.querySelectorAll('input').forEach(function(i){i.addEventListener('input',calc);});
    tierBody.appendChild(tr);
  }
  function money(n){
    var s=Math.abs(n).toLocaleString(undefined,{style:'currency',currency:'USD'});
    return (n<0?'\\u2212':'')+s;
  }
  function signed(n){return (n>0?'+':'')+money(n);}

  function calc(){
    var price=parseFloat(document.getElementById('price').value)||0;
    var bb=(parseFloat(document.getElementById('buyback').value)||0)/100;
    var ev=0,sum=0,hit=0;
    tierBody.querySelectorAll('tr').forEach(function(tr){
      var ins=tr.querySelectorAll('input');
      var v=parseFloat(ins[0].value), o=parseFloat(ins[1].value);
      if(isNaN(v)||isNaN(o))return;
      ev+=v*(o/100); sum+=o;
      if(v>price)hit+=o;
    });

    var note=document.getElementById('oddsNote');
    if(sum===0){note.textContent='';note.className='odds-note';}
    else if(Math.abs(sum-100)>0.05){
      note.textContent='Your odds add up to '+sum.toFixed(2)+'%. They should total 100%.';
      note.className='odds-note bad';
    } else {note.textContent='Odds total 100%.';note.className='odds-note';}

    var bbVal=ev*bb, per=bbVal-price, ret=price>0?ev/price*100:0;
    document.getElementById('evOut').textContent=money(ev);
    document.getElementById('retOut').textContent=(price>0&&sum>0)?Math.round(ret)+'%':'\\u2014';
    document.getElementById('bbOut').textContent=money(bbVal);
    var l=document.getElementById('lossOut');
    l.textContent=signed(per); l.className=per>=0?'pos':'neg';
    var t=document.getElementById('tenOut');
    t.textContent=signed(per*10); t.className=per>=0?'pos':'neg';
    document.getElementById('hitOut').textContent=hit.toFixed(1)+'%';

    var verdict=document.getElementById('verdict');
    if(sum===0||price===0){verdict.textContent='Add value tiers to see the maths.';return;}
    if(ret>=100){
      verdict.textContent='On average the cards in this pack are worth '+Math.round(ret)+'% of the price. A return at or above 100% is rare, so it is worth checking the listed values against recent sold prices.';
    } else {
      verdict.textContent='On average the cards are worth '+Math.round(ret)+'% of the price. Selling everything back at this buyback rate, you would expect to lose about '+money(Math.abs(per))+' per pack.';
    }
  }

  function load(key){
    var p=PRESETS[key];
    tierBody.innerHTML='';
    p.tiers.forEach(function(t){addTier(t[0],t[1]);});
    document.getElementById('price').value=p.price;
    document.getElementById('buyback').value=p.buyback;
    calc();
  }

  document.getElementById('addTier').addEventListener('click',function(){addTier();});
  document.getElementById('loadPackz').addEventListener('click',function(){load('packz');});
  document.getElementById('loadCourtyard').addEventListener('click',function(){load('courtyard');});
  document.getElementById('clearTiers').addEventListener('click',function(){
    tierBody.innerHTML=''; addTier(); calc();
  });
  ['price','buyback'].forEach(function(id){
    document.getElementById(id).addEventListener('input',calc);
  });

  load('packz');
})();
</script>
"""
    ld = jsonld({
        "@context": "https://schema.org", "@type": "WebApplication",
        "name": "Pack EV calculator",
        "url": BASE_URL + "/calculator/",
        "applicationCategory": "UtilityApplication",
        "operatingSystem": "Any",
        "description": "Calculates the expected value, buyback return and hit rate of a mystery card pack from its published odds.",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
    })
    return pages_written("/calculator/", page(
        "/calculator/",
        "Pack EV calculator — work out what a card pack is really worth",
        "Free calculator for mystery card packs. Enter a site's published odds to get the average card value, expected loss per pack and your chance of beating the pack price.",
        body, crumbs=[("/", "Home"), (None, "Pack EV calculator")],
        structured=ld))


def build_chase():
    grail = 0.0002
    lineup = 0.0196

    def at_least_one(p, n):
        return (1 - (1 - p) ** n) * 100

    prob_rows = "".join(
        '<tr><td class="num">%s</td><td class="num">%s</td>'
        '<td class="num"><strong>%s</strong></td></tr>'
        % ("{:,}".format(n), money(n * 100), pct(at_least_one(grail, n), 2))
        for n in (1, 10, 50, 100, 500, 1000, 3465, 5000)
    )

    top_rows = "".join(
        '<tr><td class="name">%s</td><td>%s</td><td class="num">%s</td>'
        '<td class="num">%s</td><td class="num"><strong>%s</strong></td>'
        '<td class="num">%s</td></tr>' % (p, k, money(pr), t, m, o)
        for p, k, pr, t, m, o in [
            ("Clutch Packs", "Multisport Ascent", 100, "$130,000", "1,300&times;", "Observed once in 21,127 pulls"),
            ("Tilt Rips", "Pro Pack", 100, "$90,000", "900&times;", "Not published"),
            ("Crown Rips", "Diamond", 2500, "$100,000", "40&times;", "Not published"),
            ("Courtyard", "Pokémon Legend (Spicy)", 2499, "$79,900", "32&times;", "0.5% for the top band"),
            ("Courtyard", "Sports Cosmic", 10000, "$160,000", "16&times;", "0.1% for the top band"),
            ("Packz", "Pokémon Starter", 25, "$500", "20&times;", "0.1%"),
            ("Arena Club", "Basketball Gold", 100, "Not published", "&mdash;", "0.02% per Grail card"),
        ])

    faq_html, faq_ld = faq_block([
        ("What are the odds of pulling the Cooper Flagg card?",
         "<p>On Arena Club's $100 Basketball Gold pack, the Cooper Flagg PSA 9 listed in the Grail tier carries a published hit rate of 0.02%, which is 1 in 5,000 packs. At $100 a pack that is $500,000 of packs for one expected hit, and you would need about 3,465 packs, or $346,539, for a coin-flip chance of seeing one. A Cooper Flagg PSA 10 also appears twice in the common Lineup tier at 1.96% each, so the chance of pulling some Cooper Flagg card is 3.94%, or about 1 in 25 packs.</p>"),
        ("How much do you have to spend to hit a grail card?",
         "<p>At a 0.02% hit rate on a $100 pack, the expected spend for one grail is $500,000, and there is no point at which it becomes due. Each pack is independent, so 4,999 misses do not improve the 5,000th. Over 100 packs, which is $10,000 spent, the chance of seeing at least one is 1.98%. Over 1,000 packs, or $100,000, it is 18.13%.</p>"),
        ("Which platform has the biggest top prize?",
         "<p>Relative to the pack price, Clutch Packs: a $130,000 Series Hit on a $100 pack is 1,300 times the price, and it is the only top prize in the category that has been observed to actually land, appearing once in 21,127 recorded pulls. Tilt Rips advertises a $90,000 card on a $100 pack, or 900 times, with no published odds. In absolute terms Courtyard's $10,000 Sports Cosmic Pack tops out at $160,000, but that is only 16 times the price.</p>"),
        ("Do chase cards change a pack's expected value?",
         "<p>Barely, on most platforms, and that is the point most buyers miss. On Courtyard's packs the top two tiers combined add only about 19 cents to the average value of a $5 pack. Packz's top tier, at 0.1%, contributes a comparable fraction. The money in these products sits in the common tiers, which is why a pack can advertise a six-figure ceiling and still return 95 cents on the dollar. The two exceptions we have found are Clutch Packs' Multisport Ascent and Moonshot packs, whose published averages are measurably inflated by a single $130,000 pull.</p>"),
    ])

    body = """
<div class="wrap narrow">
  <div class="page-head">
    <h1>What are the real odds of pulling the Cooper Flagg card?</h1>
    <p class="lede">Every ripping platform leads with its grails. Arena Club puts a Cooper Flagg rookie at the top of a $100 basketball pack; Clutch Packs dangles a $130,000 Tom Brady. Here is what the published numbers actually say about your chances of seeing either.</p>
  </div>

  <div class="finding">
    <p class="big">The Cooper Flagg PSA 9 in Arena Club's Grail tier is listed at 0.02%, or 1 in 5,000 packs. At $100 a pack that is $500,000 of packs for one expected hit, and $346,539 for a coin-flip chance. Meanwhile a Cooper Flagg PSA 10 sits twice in the same pack's common tier at 1.96% each, so "pulling a Cooper Flagg" is about 1 in 25 &mdash; roughly 197 times more likely than pulling the one on the poster.</p>
    <p class="small muted">Calculated from Arena Club's own published per-card hit rates, collected {collected}.</p>
  </div>

  <h2>The grail maths</h2>
  <p>Arena Club publishes a hit rate against every individual card, which makes this one of the few chase cards in the category whose odds can be checked at all. On the $100 Basketball Gold pack the three Grail cards are listed at 0.02% each: a Victor Wembanyama PSA 10, a Jalen Brunson BGS 9.5, and the Cooper Flagg PSA 9.</p>

  <div class="table-wrap">
  <table>
  <caption>Chance of pulling the 0.02% Cooper Flagg Grail at least once, by number of $100 packs opened.</caption>
  <thead><tr><th scope="col" class="num">Packs</th><th scope="col" class="num">Spent</th><th scope="col" class="num">Chance of at least one</th></tr></thead>
  <tbody>{prob_rows}</tbody>
  </table>
  </div>

  <p><strong>There is no point at which it becomes due.</strong> Each pack is independent of the last, so 4,999 misses do not improve the odds on the 5,000th. The 1-in-5,000 figure describes a long-run frequency, not a queue you are advancing through. If you open ten packs you have a 0.2% chance, and opening ten more leaves you with a 0.4% chance in total rather than a better one.</p>

  <p><strong>The whole Grail tier is barely more likely.</strong> Three cards at 0.02% each is 0.06% combined, or 1 in 1,667 packs. The Chase tier, eight cards at 0.25%, comes to 2%, which is roughly one pack in fifty. Everything else &mdash; 98% of pulls &mdash; comes from the Lineup.</p>

  <h2>The same player in two different tiers</h2>
  <p>Here is the part worth understanding before you chase anything. On that Basketball Gold checklist, Cooper Flagg appears three times:</p>

  <div class="table-wrap">
  <table class="plain">
  <thead><tr><th scope="col">Listed as</th><th scope="col">Tier</th><th scope="col" class="num">Hit rate</th></tr></thead>
  <tbody>
    <tr><th scope="row">Cooper Flagg, PSA 9</th><td>Grail</td><td class="num">0.02%</td></tr>
    <tr><th scope="row">Cooper Flagg, PSA 10</th><td>Lineup</td><td class="num">1.96%</td></tr>
    <tr><th scope="row">Cooper Flagg, PSA 10</th><td>Lineup</td><td class="num">1.96%</td></tr>
  </tbody>
  </table>
  </div>

  <p>A lower-graded copy sits in the rarest tier while two higher-graded copies sit in the commonest. That is not a contradiction &mdash; almost certainly these are entirely different cards, a scarce parallel or autograph in the Grail slot and base rookies in the Lineup. But you cannot tell that from the checklist, because <strong>the checklist lists only a player name and a grade</strong>. No set, no year, no card number.</p>

  <p>So a buyer looking at that page sees Cooper Flagg three times and has no way to work out that one of those entries is worth perhaps a hundred times the other two. The same problem blocked us from pricing Arena Club's packs at all: player plus grade is not enough to identify a card, which is why we cannot publish an expected value for any Arena Club pack. For a chase card, it means the name on the marketing is not the thing you are likely to pull.</p>

  <h2>Top prizes across the category</h2>
  <p>Ceilings are the easiest thing in this business to advertise. Measured against the pack price rather than in raw dollars, they look like this:</p>

  <div class="table-wrap">
  <table>
  <caption>Advertised top prizes and their published odds, where any exist.</caption>
  <thead><tr>
    <th scope="col">Platform</th><th scope="col">Pack</th><th scope="col" class="num">Price</th>
    <th scope="col" class="num">Top prize</th><th scope="col" class="num">Multiple</th>
    <th scope="col">Odds</th>
  </tr></thead>
  <tbody>{top_rows}</tbody>
  </table>
  </div>

  <p><strong>Only one of these has been observed to land.</strong> Clutch Packs records every opening on-chain, and the $130,000 Tom Brady Refractor shows up as the maximum recorded pull on its Multisport Ascent pack &mdash; once, across 21,127 pulls. That is the only top prize in the category with any evidence behind it, and at that observed rate it implies roughly $2.1 million of packs per hit. A $35,000 LeBron Exquisite sits in the same series.</p>

  <p><strong>Four of the seven publish no odds on their top prize at all.</strong> Tilt Rips lists a $90,000 card on a $100 pack with no probability attached anywhere. Crown Rips gives a $100,000 maximum with no rates. A ceiling without a rate tells you what is theoretically in the building, not what you are buying.</p>

  <h2>The chase barely moves the expected value</h2>
  <p>This is the counterintuitive part, and it is the single most useful thing to know. A six-figure top prize is nearly irrelevant to what a pack returns on average.</p>

  <p>On Courtyard's $5 Pok&eacute;mon pack, the top two tiers combined contribute about 19 cents to the pack's average value. Packz's 0.1% top tier contributes a similarly small slice. The money in these products sits in the common tiers, which is exactly how a pack can advertise a 1,300x ceiling and still return 95 cents on the dollar. If you are buying for value, the grail is a rounding error.</p>

  <p>The two exceptions prove it. Clutch Packs' Multisport Ascent posts a 1.07 times average return, but that single $130,000 Brady adds $6.15 per pack across 21,127 recorded pulls, which is 6.2% of the pack price. Strip it out and Ascent returns about 1.00 times. Its Moonshot pack is in the same position. When a jackpot does move the average, it moves it because it actually landed, not because it was advertised.</p>

  <h2>So what should you actually do</h2>
  <p><strong>If you want the chase, buy it knowingly.</strong> High-variance packs exist and are honestly labelled on some platforms: Courtyard's Spicy packs drop their floor to around half the pack price in exchange for a much higher ceiling, at the same average return. That is a real, disclosed trade between floor and ceiling. Paying for variance is a legitimate choice; just know that is what you are buying.</p>

  <p><strong>If you want value, ignore the grails entirely</strong> and look at the floor, the buyback and the share of pulls below 1x. On the only platform publishing observed results, 74% of recorded pulls came back worth less than the pack price. That number tells you far more about your next pack than any ceiling does.</p>

  <p><strong>And check whether the card you are chasing is even identifiable.</strong> If a checklist gives you a player and a grade but no set, year or certificate number, you cannot look up what it is worth, and you cannot tell the grail apart from its common namesake in the same pack.</p>

  <div class="callout danger">
    <h3>A note on chasing</h3>
    <p>A 1-in-5,000 card is not a goal, it is a lottery ticket attached to a product that loses money on average. Decide what you are willing to spend before you start, treat it as the cost of the entertainment, and do not buy another pack to recover the last one &mdash; the odds on the next pack are identical regardless of what just happened.</p>
    <p>If it has stopped feeling like fun, free and confidential help is available: call or text <strong>1-800-GAMBLER</strong>.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Go deeper</h2>
  <ul>
    <li><a href="/platforms/arena-club/">Arena Club's full odds structure</a></li>
    <li><a href="/platforms/clutch-packs/">The 158,556 pulls behind the only observed return data</a></li>
    <li><a href="/calculator/">Work out any pack's odds yourself</a></li>
  </ul>
</div>
""".format(collected=COLLECTED, prob_rows=prob_rows, top_rows=top_rows,
           faq=faq_html)

    art = jsonld({
        "@context": "https://schema.org", "@type": "Article",
        "headline": "What are the real odds of pulling the Cooper Flagg card?",
        "description": "Arena Club lists the Cooper Flagg Grail at 0.02%, or 1 in 5,000 packs. What that means in spend, and how every platform's advertised top prize compares.",
        "datePublished": UPDATED, "dateModified": UPDATED,
        "author": {"@type": "Organization", "name": SITE_NAME},
        "publisher": {"@type": "Organization", "name": SITE_NAME},
        "mainEntityOfPage": BASE_URL + "/guides/chase-card-odds/",
    })

    return pages_written("/guides/chase-card-odds/", page(
        "/guides/chase-card-odds/",
        "Cooper Flagg pack odds — the real chance of pulling a grail card",
        "Arena Club lists its Cooper Flagg Grail at 0.02%, or 1 in 5,000 packs, which is $346,539 for a coin-flip chance. Every platform's top prize and published odds, compared.",
        body, crumbs=[("/", "Home"), (None, "Chase card odds")],
        updated=COLLECTED, structured=[faq_ld, art]))


def build_bonuses():
    s = clutch_stats()
    disc = 0.20
    edge = s["w_avg"] / (1 - disc)

    offers = [
        ("Clutch Packs", "20% off your first pack", "Discount",
         "<strong>+26%</strong> expected", "Best offer in the category"),
        ("Tilt Rips", "Buy any pack, get a $10 pack free", "Free pack",
         "Not calculable", "No odds published, so the free pack's value is unknown"),
        ("Packz", "100% buyback on first pack, capped at $100", "Better buyback",
         "~$10 in credit", "Credit only; capped, so pack size matters"),
        ("Packz", "Referral scratch card, $7 or $100 in bonus funds", "Bonus funds",
         "$7 typical", "Bonus funds are site credit"),
        ("Arena Club", "Collect Safe add-on, +10% for an 80% floor", "Paid insurance",
         "Situational", "Not a bonus &mdash; you pay for it"),
        ("Courtyard", "None for new users", "&mdash;",
         "$0", "Referrer gets 1,000 points of undisclosed value"),
        ("Crown Rips", "5 Sweeps Cash in the closed beta", "Beta credit",
         "Not calculable", "Invite only"),
        ("Chalkboard Pulls", "Free Packs in the Promos tab", "Free pack",
         "Below face value",
         "Sell-back credits &ldquo;play-through funds, not&hellip; withdrawable&rdquo;"),
        ("Fanatics", "Not confirmed", "&mdash;", "Unknown", "Terms not verified"),
    ]
    offer_rows = "".join(
        '<tr><td class="name">%s</td><td>%s</td><td>%s</td>'
        '<td class="num">%s</td><td>%s</td></tr>' % r for r in offers)

    best = [p for p in CLUTCH_PACKS if p[3] >= 1000]
    best.sort(key=lambda x: -x[4] / x[2])
    pack_rows = "".join(
        '<tr><td class="name">%s %s</td><td class="num">%s</td>'
        '<td class="num">%s</td><td class="num">%s</td>'
        '<td class="num">%.3f&times;</td>'
        '<td class="num"><strong class="pos">%.2f&times;</strong></td></tr>'
        % (E(c), E(n), "{:,}".format(pulls), money(pr), money(pr * 0.8),
           a / pr, a / pr / 0.8)
        for c, n, pr, pulls, a, _ in best[:6])

    faq_html, faq_ld = faq_block([
        ("Which card ripping site has the best sign-up bonus?",
         "<p>Clutch Packs, on the arithmetic. A 20% discount on your first pack means you pay 80% of face value for a pack whose observed average return across 158,556 recorded pulls is 1.01 times face. That works out to about a 26% expected return on what you actually spend, and it is the only offer in the category we can calculate at all, because Clutch Packs is the only platform publishing observed results. The catch is that the return is in card value, and Clutch Packs discloses no buyback terms, so converting that card into money is an open question.</p>"),
        ("Does Courtyard have a welcome bonus?",
         "<p>No. Courtyard has no welcome offer for new users and no promo code is needed to sign up. Its referral programme pays the referrer up to 1,000 points once the referred user verifies identity and buys packs (sources differ on whether the threshold is $20 or $25), capped at six referrals. Courtyard does not publish what a point is worth in dollars, and the new user appears to get nothing, so there is no calculable value on either side.</p>"),
        ("What is the optimal first pack to buy with a bonus?",
         "<p>It depends on how the offer is capped. Clutch Packs' 20% discount has no stated cap, so the discount scales with the pack price &mdash; but so does the variance, and on its largest packs more than half of recorded pulls come back worth under half the pack price. Packz's 100% first-pack buyback is capped at $100, so a $25 first pack leaves three-quarters of the bonus unused while a $100 pack captures all of it. Tilt Rips' free pack is a fixed $10 regardless of what you buy, so the minimum $10 qualifying purchase extracts it most efficiently.</p>"),
        ("Are card ripping bonuses actually worth taking?",
         "<p>Each one is worth taking once, and none of them is a strategy. Every offer here is new-customer-only and single-use, so whatever edge exists applies to one pack and then disappears. After that you are buying the underlying product, where the average return is below 100% everywhere we have measured and roughly three-quarters of individual pulls come back worth less than the pack price. A bonus that turns one pack positive does not make the next one positive.</p>"),
    ])

    body = """
<div class="wrap narrow">
  <div class="page-head">
    <h1>Pack ripping bonuses, ranked by what they are actually worth</h1>
    <p class="lede">Every sign-up offer we could verify across the platforms we track, with the arithmetic. One of them is plausibly worth more than it costs. Most are worth less than they look, and one platform that everyone lists as having an offer does not have one.</p>
  </div>

  <div class="finding">
    <p class="big">Clutch Packs' 20% first-pack discount is the only offer in the category that produces a calculable positive expected return: you pay 80% of face value for a pack whose observed average across {pulls} recorded pulls is {wavg:.2f} times face, which is about <strong>{edge:+.0%}</strong> on what you spend. It is also the only platform publishing observed results, which is the only reason the sum can be done at all.</p>
    <p class="small muted">All figures below come from published promotional terms and secondary reporting, read {collected}. We have not verified any of them directly with the platforms. Bonus terms change without notice; check before you buy.</p>
  </div>

  <div class="callout">
    <h3>Correction</h3>
    <p>An earlier version of our research described a Courtyard referral offer guaranteeing a $25 buyback on a $25 starter pack for both parties. We could not substantiate that. Current reporting says Courtyard has <strong>no welcome offer at all</strong>, and its referral pays the referrer in points of undisclosed value. We have corrected it here rather than leave it standing.</p>
  </div>

  <h2>Every offer, ranked</h2>
  <div class="table-wrap">
  <table>
  <caption>Sign-up and first-pack offers across the twenty-four platforms we track, {collected}.</caption>
  <thead><tr><th scope="col">Platform</th><th scope="col">Offer</th><th scope="col">Type</th><th scope="col" class="num">What it's worth</th><th scope="col">Catch</th></tr></thead>
  <tbody>{offer_rows}</tbody>
  </table>
  </div>

  <h2>Clutch Packs: the one with real maths behind it</h2>
  <p>A discount is worth more than a credit bonus, because it reduces what you pay rather than adding something you can only spend inside the platform. And because Clutch Packs publishes observed pull results, this is the only offer in the category where a discount can be set against a known return.</p>

  <p>The pull-weighted average across all {npacks} packs is {wavg:.3f} times face value. Paying 80% of face for that gives an expected {edge:.2f} times on outlay. Stripping out the jackpot inflation we identified on two of its packs and using a flat 1.00 times instead still leaves about +25%.</p>

  <div class="table-wrap">
  <table>
  <caption>Clutch Packs packs with at least 1,000 recorded pulls, best observed return first, with the 20% discount applied.</caption>
  <thead><tr>
    <th scope="col">Pack</th><th scope="col" class="num">Pulls</th>
    <th scope="col" class="num">Face price</th><th scope="col" class="num">You pay</th>
    <th scope="col" class="num">Observed return</th><th scope="col" class="num">On outlay</th>
  </tr></thead>
  <tbody>{pack_rows}</tbody>
  </table>
  </div>

  <h3>Three things that cut against it</h3>
  <p><strong>The return is in card value, not money.</strong> This is the big one. Clutch Packs discloses no buyback or sell-back terms anywhere on its pack pages or its transparency page. A 1.01 times average in card value is only a 1.01 times average in cash if you can convert at par, and nothing published says you can. On every other platform this is exactly where the headline erodes: Fanatics pays 84.6% effective, Packz pays credit you cannot withdraw. Until Clutch answers this, treat the +26% as the ceiling rather than the expectation.</p>

  <p><strong>Roughly 63% of single pulls still lose money.</strong> The discount moves your break-even from a card worth 1.0 times face to one worth 0.8 times. On the Multisport Ascent pack, about 26% of recorded pulls cleared 1.0 times and perhaps another 11% of the 0.5-to-1 band clears 0.8. So about 37% of pulls beat the discounted price. A positive average and a likely individual loss coexist comfortably here.</p>

  <p><strong>The edge exists once.</strong> New customers only, one use per account, and it cannot be combined with other Clutch promotions. After that pack you are buying a break-even product with a 74% chance per pull of getting back less than you paid.</p>

  <h3>Conditions worth knowing</h3>
  <ul>
    <li><strong>Card or debit only.</strong> Crypto, Zelle, transferred balances and promotional balances do not qualify.</li>
    <li><strong>No stated cap</strong> on the discount, so it scales with pack price &mdash; and so does variance. On the $2,500 Moonshot pack, 53.4% of recorded pulls came back worth under half the pack price.</li>
    <li>New users only, 18+, eligible locations, one use per account.</li>
  </ul>

  <h2>The rest, briefly</h2>

  <h3>Tilt Rips: a free $10 pack</h3>
  <p>Fund $10, buy a $10 pack, get a second $10 pack free, with phone verification required. Doubling your packs sounds like a 100% bonus, and in face-value terms it is. But Tilt Rips publishes no odds, no floors and no expected value for any of its roughly 60 packs, so the free pack's actual worth cannot be calculated. The efficient play is the minimum $10 qualifying purchase, since the free pack is a fixed $10 regardless of what you spend.</p>

  <h3>Packz: a better buyback on one pack</h3>
  <p>The first pack qualifies for a 100% buyback instead of the standard 90%, capped at $100. Since Packz's own published odds imply roughly 100% of face in card value on its $25-and-up packs, that extra 10 points is worth about $10 on a $100 first pack and about $2.50 on a $25 one.</p>
  <p><strong>The cap is the whole strategy here:</strong> a $25 first pack leaves three-quarters of the bonus on the table. One caveat we could not resolve &mdash; it is unclear whether the $100 cap applies to the pack price or to the payout, which changes the advice if you pull something large. And the payout is site credit that cannot be withdrawn, so the $10 can only buy more packs.</p>

  <h3>Courtyard: nothing</h3>
  <p>No welcome offer, no promo code needed. The referral pays the referrer up to 1,000 points after the referred user verifies identity and buys packs, capped at six referrals. Courtyard does not publish a dollar value for a point, and the new user appears to receive nothing. Several affiliate sites list Courtyard among their promo pages anyway, which tells you something about how those pages are assembled.</p>

  <h3>Arena Club: an add-on, not a bonus</h3>
  <p>Collect Safe costs 10% of the pack price and guarantees a buyback floor of 80% of that price. On the $25 Pok&eacute;mon Bronze pack that is $2.50 for a $20 floor. It pays for itself whenever the revealed card is worth less than about 89% of the pack price &mdash; which, on a product where the average card is worth less than the pack, is often. We cannot put a number on it because Arena Club publishes no card values. <a href="/platforms/arena-club/">Full analysis here.</a></p>

  <h3>Crown Rips and Fanatics</h3>
  <p>Crown Rips gives beta participants 5 Sweeps Cash to start, but the beta is invite-only and limited to 500 users. We could not verify any current Fanatics Instant Rips offer.</p>

  <div class="callout danger">
    <h3>Read this before chasing any of it</h3>
    <p>Every offer here is new-customer-only and single-use. Whatever edge exists applies to one pack and then vanishes, after which you are buying a product whose average return is below 100% on every platform we have measured, and where roughly three-quarters of individual pulls come back worth less than the pack price.</p>
    <p>A bonus that makes one pack positive does not make the next one positive, and "I'm up on the bonus" is the most common reason people keep buying. Decide your budget before you start.</p>
    <p>If this has stopped feeling like fun, free and confidential help is available: call or text <strong>1-800-GAMBLER</strong>.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Go deeper</h2>
  <ul>
    <li><a href="/platforms/clutch-packs/">The 158,556 pulls behind the Clutch Packs figures</a></li>
    <li><a href="/platforms/packz/">Packz's odds template and credit-only buyback</a></li>
    <li><a href="/calculator/">Run a discounted pack through the calculator</a></li>
  </ul>
</div>
""".format(pulls="{:,}".format(s["pulls"]), wavg=s["w_avg"], edge=edge - 1,
           npacks=s["n_packs"], collected=CLUTCH_COLLECTED,
           offer_rows=offer_rows, pack_rows=pack_rows, faq=faq_html)

    # the {edge:.2f} in prose needs the raw multiple, not the delta
    body = body.replace("expected %.2f times on outlay" % (edge - 1),
                        "expected %.2f times on outlay" % edge)

    art = jsonld({
        "@context": "https://schema.org", "@type": "Article",
        "headline": "Pack ripping bonuses, ranked by what they are actually worth",
        "description": "Every card ripping sign-up offer we could verify, with the arithmetic. Clutch Packs' 20% first-pack discount is the only one with a calculable positive expected return.",
        "datePublished": UPDATED, "dateModified": UPDATED,
        "author": {"@type": "Organization", "name": SITE_NAME},
        "publisher": {"@type": "Organization", "name": SITE_NAME},
        "mainEntityOfPage": BASE_URL + "/guides/bonus-offers/",
    })

    return pages_written("/guides/bonus-offers/", page(
        "/guides/bonus-offers/",
        "Card ripping bonuses ranked — which sign-up offers are actually worth it",
        "Every pack ripping sign-up offer, with the maths. Clutch Packs' 20% first-pack discount works out to about +26% on outlay; Courtyard has no welcome offer at all.",
        body, crumbs=[("/", "Home"), (None, "Bonus offers")],
        updated=CLUTCH_COLLECTED, structured=[faq_ld, art]))


def build_mintpull():
    cap = 250
    rows = "".join(
        '<tr><td class="num">%s</td><td class="num"><strong>%d weeks</strong></td>'
        '<td class="num">%.1f months</td></tr>'
        % (money(b), -(-b // cap), (-(-b // cap)) / 4.345)
        for b in (500, 1000, 2500, 5000, 10000))

    faq_html, faq_ld = faq_block([
        ("Can you withdraw money from MintPull?",
         "<p>Only money that came from selling inventory, and only $250 per seven days. Section 5.5 of the terms states &ldquo;The only funds available for withdrawal are those you have received from sales of your Inventory,&rdquo; so deposits cannot be taken back out. The Company &ldquo;may cap eligible funds at $250 per seven days.&rdquo; The minimum withdrawal is $5, processing takes up to a week, and KYC verification is required. At that cap a $2,500 balance takes ten weeks to withdraw and a $10,000 balance takes about nine months.</p>"),
        ("Is the MintPull 100% FMV guarantee paid in cash?",
         "<p>Not according to the terms. The homepage advertises a &ldquo;100% Fair Market Value (FMV) guarantee,&rdquo; but section 5.5 says returns are credited as &ldquo;additional pack purchase credits.&rdquo; Pack credit is not money, and since deposits are separately non-withdrawable, the only balance that can ever leave the platform is proceeds from inventory sales &mdash; subject to the $250 weekly cap.</p>"),
        ("Who operates MintPull?",
         "<p>Arcane Answers Studio Limited, a Hong Kong company based in Kwun Tong, trading as MintPull. Two further entities act as payment administration agents: Starpnet Studio Inc in the United States and YISEN BREEZE LTD in the United Kingdom. Hong Kong law governs the agreement. That is why the website lists three separate support addresses at three unrelated domains.</p>"),
        ("How long can you keep a card on MintPull?",
         "<p>Seven days. Section 5.3 states, in capitals, &ldquo;YOU MAY ONLY STORE A COLLECTIBLE FOR A MAXIMUM OF SEVEN DAYS.&rdquo; After that it becomes a Return at the Company's discretion and you are credited its fair market value as of when you received it. The Company may give 24 hours' notice by push notification and may extend the deadline. That matches Crown Rips and is longer than Packed's one day or Pickem's three hours.</p>"),
        ("Does MintPull publish pack odds?",
         "<p>Not on its website. Section 5.2 says packs may show the producer, series, cost and item count, and that odds details such as value chance, rarity or grade may also be shown. The same section states, in capitals, &ldquo;THE DISTRIBUTION BETWEEN RANGES MAY NOT (AND LIKELY IS NOT) BE EQUAL,&rdquo; and that statistics change in real time with inventory. No figures appear anywhere publicly.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>MintPull: a 100% guarantee you can withdraw at $250 a week</h1>
    <p class="lede">MintPull advertises a 100% fair market value guarantee. Its terms credit returns as pack purchase credit, cap withdrawals at $250 per seven days, and are governed by Hong Kong law.</p>
    {flags_mintpull}
  </div>

  <div class="finding">
    <p class="big">Section 5.5: &ldquo;The only funds available for withdrawal are those you have received from sales of your Inventory,&rdquo; and the Company &ldquo;may cap eligible funds at $250 per seven days.&rdquo; At that rate a $2,500 balance takes ten weeks to withdraw and a $10,000 balance takes about nine months. The same section credits returns as &ldquo;additional pack purchase credits&rdquo; rather than money.</p>
    <p class="small muted">Read from mintpull.net, its Terms of Service and its Responsible Purchasing Policy on {collected}.</p>
  </div>

  <h2>The withdrawal cap</h2>
  <p>Every other platform we track either states no withdrawal cap or sets one high enough not to matter. Pickem allows $2,500 per withdrawal. Arena Club, Tilt Rips, Packed and Fanatics publish no cap at all. MintPull's is $250 per seven days, which is the lowest by an order of magnitude and the term most likely to affect anyone who does well.</p>

  <div class="table-wrap">
  <table>
  <caption>How long it takes to withdraw a balance at $250 per seven days.</caption>
  <thead><tr><th scope="col" class="num">Balance</th><th scope="col" class="num">Weeks to withdraw</th><th scope="col" class="num">Roughly</th></tr></thead>
  <tbody>{rows}</tbody>
  </table>
  </div>

  <p>Note where this bites. It is irrelevant to someone who loses, and severe for someone who pulls well &mdash; which is the opposite of how a cap is usually framed. A single good pull on a mid-priced pack can take months to convert into money, and during that time the balance sits on a platform whose terms let it change fees &ldquo;at any time in the Company's sole discretion.&rdquo;</p>

  <h2>The self-exclusion problem</h2>
  <p>MintPull publishes a Responsible Purchasing Policy, which is more than most of this category does, and it offers temporary suspension or permanent account closure. Section 3.2 then says that on exclusion &ldquo;any remaining funds in your account will be permanently forfeited unless withdrawn prior to the exclusion taking effect.&rdquo;</p>

  <p>Put that beside the $250 weekly cap. <strong>A user with $2,500 in their balance who decides to stop has to keep the account open for ten weeks to get their money out first.</strong> A user with $1,000 needs four weeks. The tool intended to help someone step away requires them to stay for a month or more, or forfeit the balance.</p>

  <p>We do not think that is deliberate. It reads like two policies written separately by people who never put them side by side. But it is the practical effect, and it is the kind of thing a responsible-purchasing policy exists to prevent.</p>

  <div class="callout danger">
    <h3>If you use MintPull, withdraw as you go</h3>
    <p>Do not let a balance accumulate. At $250 per seven days, money you leave on the platform is money you have committed to a months-long exit, and the self-exclusion clause forfeits anything still sitting there. Withdraw to the cap each week rather than waiting until you want to stop.</p>
    <p>If this has stopped feeling like fun, free and confidential help is available: call or text <strong>1-800-GAMBLER</strong>.</p>
  </div>

  <h2>Who you are actually dealing with</h2>
  <p>The site lists three support addresses at three unrelated domains, which is unusual enough to be worth following. The terms explain it:</p>

  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>Arcane Answers Studio Limited, trading as MintPull &mdash; Kwun Tong, Hong Kong (&sect;17)</td></tr>
    <tr><th scope="row">Payment agents</th><td>Starpnet Studio Inc (United States) and YISEN BREEZE LTD (United Kingdom)</td></tr>
    <tr><th scope="row">Governing law</th><td>Hong Kong (&sect;14.1)</td></tr>
    <tr><th scope="row">Funding</th><td>Only after the Company verifies you are in the United States (&sect;6.2)</td></tr>
  </tbody>
  </table>
  </div>

  <p>So the product is sold to US buyers, funded only from the US, administered through US and UK payment agents, and governed by the law of Hong Kong. Every other platform we track is a US company operating under US law. If a dispute arises over a valuation, a withdrawal or a forfeited balance, the contract points to a jurisdiction on the other side of the world.</p>

  <p>That is not an accusation of bad faith &mdash; plenty of legitimate businesses are structured across borders. It is simply a material fact that nothing on the marketing site tells you, and it belongs in any assessment of counterparty risk on a platform that holds your money.</p>

  <h2>Odds, and an unusually frank sentence</h2>
  <p>No odds, prices or pull rates appear anywhere on the public site. Packs are described only as running from &ldquo;Basic Packs to Epic Packs.&rdquo; Section 5.2 says packs may display the producer, series, cost and item count, and that odds details such as value chance, rarity or grade may also be shown.</p>

  <p>The same section then says, in capitals: <strong>&ldquo;THE DISTRIBUTION BETWEEN RANGES MAY NOT (AND LIKELY IS NOT) BE EQUAL.&rdquo;</strong></p>

  <p>That is a more candid statement than most of this category manages, and it is worth reading carefully. It warns that where a pack shows value ranges, you should not assume the outcomes within a range are evenly spread &mdash; which is exactly the assumption our own midpoint estimates make when a platform publishes ranges without rates. It is a fair warning, and it is also an argument for publishing the actual distribution instead.</p>

  <h2>Other terms worth knowing</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Buyback</th><td>Advertised at 100% of FMV; &sect;5.5 credits returns as &ldquo;additional pack purchase credits&rdquo;</td></tr>
    <tr><th scope="row">Storage limit</th><td>&ldquo;YOU MAY ONLY STORE A COLLECTIBLE FOR A MAXIMUM OF SEVEN DAYS&rdquo; (&sect;5.3), then auto-returned at FMV</td></tr>
    <tr><th scope="row">Withdrawals</th><td>Sale proceeds only; $250 per seven days; $5 minimum; up to a week to process; KYC required</td></tr>
    <tr><th scope="row">Deposits</th><td>Not withdrawable</td></tr>
    <tr><th scope="row">FMV</th><td>Proprietary; &ldquo;may not match published market values&rdquo;; &ldquo;subject to change at any time&rdquo; (&sect;&sect;5.4&ndash;5.5)</td></tr>
    <tr><th scope="row">Refunds</th><td>&ldquo;All Purchases are final and binding&rdquo;; requests within 30 days; Company error or legal requirement only</td></tr>
    <tr><th scope="row">Fees</th><td>Shipping, tracking, insurance above $1,000, sales tax, $25 returned-ACH fee; changeable at any time</td></tr>
    <tr><th scope="row">Restricted</th><td>Nevada, and anywhere outside the United States &mdash; though the terms apply this inconsistently</td></tr>
    <tr><th scope="row">Age</th><td>18+, or the local age of majority if higher</td></tr>
    <tr><th scope="row">Responsible purchasing</th><td>Self-exclusion available; <strong>no deposit limits, spending caps or mandatory cooling-off periods</strong> (&sect;4.1)</td></tr>
  </tbody>
  </table>
  </div>

  <h2>Credit where it is due</h2>
  <p>Two things here are better than the category norm. MintPull publishes a Responsible Purchasing Policy at all, naming the National Council on Problem Gambling and Gamblers Anonymous and offering self-exclusion &mdash; most platforms we have read offer nothing. And the all-caps warning about unequal distribution within value ranges is a more honest statement about pack mathematics than several better-funded competitors make.</p>
  <p>Neither offsets the withdrawal cap. But a site that only reported the bad terms would be a worse guide than one that reports both.</p>

  <div class="callout">
    <h3>Why this page has no rating</h3>
    <p>No prices and no odds are published, so no expected value can be calculated. We have also not tested a withdrawal, which is the claim most worth verifying here. If you have used MintPull and have screenshots of in-app odds, or experience of how the $250 cap works in practice, we would like to hear from you.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/guides/buyback-rates/">What a buyback is actually worth, across every platform</a></li>
    <li><a href="/platforms/pickem/">Pickem, where the clock runs for three hours</a></li>
    <li><a href="/platforms/">All twenty-four platforms compared</a></li>
  </ul>
</div>
""".format(collected=UPDATED, rows=rows, faq=faq_html, **{"flags_mintpull": flag_row("mintpull")})

    return pages_written("/platforms/mintpull/", page(
        "/platforms/mintpull/",
        "MintPull review — 100% FMV, capped at $250 a week",
        "MintPull advertises a 100% FMV guarantee. Its terms credit returns as pack purchase credit, cap withdrawals at $250 per seven days, and are governed by Hong Kong law.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "MintPull")],
        updated=UPDATED, structured=faq_ld))


def build_pickem():
    faq_html, faq_ld = faq_block([
        ("How long do you have to decide on a Pickem pull?",
         "<p>Three hours, and the timer starts when you open the pack rather than when you buy it. If it expires, Pickem sells the card automatically at its displayed fair market value. Reporting indicates the window is shorter still in some states. It is by a wide margin the tightest decision window of the twenty-four platforms we track: Packed gives one day, Crown Rips reportedly seven, and Courtyard, Arena Club, Fanatics and Tilt Rips vault cards indefinitely.</p>"),
        ("What is the Pickem buyback rate?",
         "<p>90% of the card's displayed fair market value, rising to 100% on your first pack purchase. Proceeds go to a USD balance which can be withdrawn to a bank card, with a $6 minimum and a $2,500 cap per withdrawal. Only money from selling cards is withdrawable, so deposits and any promotional balance are not.</p>"),
        ("Does Pickem publish pack odds?",
         "<p>Inside the app, yes. Each pack reportedly shows the cards it can produce with a pull percentage against each one, in the same per-card style Arena Club uses. Nothing appears on the public website, so a buyer cannot see a single figure before downloading. Pickem also offers Normal, High and Max probability settings at the same pack price, which means each pack is really three different probability distributions, and we have seen no published figures for any of them.</p>"),
        ("Which states can't use Pickem Ripping Packs?",
         "<p>Michigan, Minnesota, Montana, Nevada and Washington are reported as excluded. The minimum age is 18, or 19 in Nebraska. Pickem Ripping Packs sits inside Pickem, a social gaming platform that also runs slots and table games, which is the likely reason for that particular list of exclusions &mdash; those states are the ones most active against sweepstakes-model operators.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Pickem Ripping Packs: three hours to decide</h1>
    <p class="lede">Pickem pays 90% of fair market value into a balance you can withdraw to a bank card. You get three hours from opening the pack to choose between shipping the card and selling it back, after which it is sold automatically.</p>
    {flags_pickem}
  </div>

  <div class="finding">
    <p class="big">Three hours, and the clock starts when you open the pack rather than when you buy it. If it runs out, Pickem sells the card for you at its own fair market value. That is eight times tighter than Packed's one-day limit and the shortest window of any platform we track.</p>
    <p class="small muted">Confirmed across two independent reviews, read {collected}. We have not verified the window first-hand and reporting indicates it is shorter in some states.</p>
  </div>

  <h2>Why three hours matters</h2>
  <p>On most of this category, deciding what to do with a pull is a decision. Here it is a deadline, and a short one. If you rip a pack in the evening and go to bed, the platform has made the choice for you by morning.</p>

  <p>The detail that sharpens it is where the timer starts. It begins when the pack is opened, not when it is bought, so a pack bought and opened at once gives you three hours from that moment. Shipping also requires an address and, on most platforms in this category, identity verification &mdash; which is time spent inside the window rather than before it.</p>

  <div class="table-wrap">
  <table>
  <caption>How long you can hold a card before the platform acts, across the twenty-four platforms we track.</caption>
  <thead><tr><th scope="col">Platform</th><th scope="col">Window</th><th scope="col">What happens at the end</th></tr></thead>
  <tbody>
    <tr><td class="name">Pickem</td><td><strong class="neg">3 hours</strong></td><td>Card sold automatically at Pickem's FMV</td></tr>
    <tr><td class="name">Packed</td><td><strong class="neg">1 day</strong></td><td>&ldquo;Automatically returned to Packed&rdquo; (&sect;6.1)</td></tr>
    <tr><td class="name">Chalkboard Pulls</td><td><strong class="neg">24 hours</strong></td><td>Time-Based Buyback at 100% of Chalkboard's FMV (&sect;7.3)</td></tr>
    <tr><td class="name">Crown Rips</td><td>7 days, reportedly</td><td>Auto-sold at market value</td></tr>
    <tr><td class="name">Courtyard</td><td>Indefinite</td><td>Vaulted and insured, free</td></tr>
    <tr><td class="name">Arena Club</td><td>Indefinite</td><td>Vaulted</td></tr>
    <tr><td class="name">Fanatics Instant Rips</td><td>Indefinite</td><td>Free vault storage, no time limit</td></tr>
    <tr><td class="name">Tilt Rips</td><td>Indefinite</td><td>Free vaulting, no storage fees</td></tr>
    <tr><td class="name">Poke-Collect</td><td><strong class="pos">1 year</strong></td><td><strong class="pos">Shipped to you automatically, free</strong></td></tr>
  </tbody>
  </table>
  </div>

  <p>Note what the short-window platforms have in common: they are also the ones paying the highest buyback rates. Pickem at 90% withdrawable and Packed at 100% withdrawable are near the top of the category on rate, and at the very bottom on time. That is not a coincidence. A platform that will reliably buy the card back does not want to be holding inventory, and the clock is how it avoids that.</p>

  <h2>What Pickem pays, and how you get it</h2>
  <ul>
    <li><strong>90% of displayed fair market value</strong> on a sell-back, rising to <strong>100% on your first pack purchase</strong>.</li>
    <li><strong>Proceeds land in a USD balance</strong> and can be withdrawn to a bank card, with a $6 minimum and a $2,500 cap per withdrawal.</li>
    <li><strong>Only sale proceeds are withdrawable.</strong> Deposits and promotional balances are not, which is the same structure <a href="/platforms/packed/">Packed</a> uses.</li>
  </ul>
  <p>That places Pickem alongside <a href="/platforms/arena-club/">Arena Club</a> and <a href="/platforms/tilt-rips/">Tilt Rips</a> in the group whose buyback reaches real money, and above <a href="/platforms/packz/">Packz</a> and <a href="/platforms/fanatics-instant-rips/">Fanatics</a>, where it does not. <a href="/guides/buyback-rates/">The full comparison is here.</a></p>

  <h2>Odds are shown, but only once you are inside</h2>
  <p>Each pack reportedly lists the cards it can produce with a pull percentage against each, the same per-card format <a href="/platforms/arena-club/">Arena Club</a> uses. That is real disclosure and better than the several platforms here that publish nothing at all.</p>

  <p>Two things limit it. Nothing appears on the public website, so the figures are invisible until you have downloaded the app and are standing at the checkout. And Pickem offers <strong>Normal, High and Max probability settings at the same pack price</strong>, which means every pack is three distributions rather than one. <a href="/platforms/crown-rips/">Crown Rips</a> has the same feature, and the same gap: no published figures for any setting, so a buyer choosing Max over Normal cannot see what they are trading.</p>

  <p>Pack prices run from $1 starter packs to around $250, with a Pok&eacute;mon Pro Pack and a Football Pro Pack at $100 and a Multi-Sport Elite Pack at $250. Prices do not change when you change the probability setting.</p>

  <h2>A social casino with a card product attached</h2>
  <p>Pickem Ripping Packs is a feature inside Pickem, a social gaming platform that also runs slots, table games and arcade games. <a href="/platforms/crown-rips/">Crown Rips</a> is the same shape: a rip product bolted onto a sweepstakes casino.</p>

  <p>The exclusion list is the tell. Michigan, Minnesota, Montana, Nevada and Washington are reported as blocked, and those are the states most active against sweepstakes-model operators rather than against collectibles sellers. Whatever the packs are, the platform around them is being treated as a gaming product. Our <a href="/is-card-ripping-gambling/">page on the legal position</a> covers why that distinction is unsettled and being tested.</p>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>Pickem, a social gaming platform with slots, table games and arcade games</td></tr>
    <tr><th scope="row">Categories</th><td>Pok&eacute;mon, baseball, football, basketball, multi-sport</td></tr>
    <tr><th scope="row">Pack prices</th><td>$1 starter packs up to about $250</td></tr>
    <tr><th scope="row">Guarantee</th><td>At least one PSA-graded card per pack</td></tr>
    <tr><th scope="row">Probability settings</th><td>Normal, High, Max &mdash; same price, no published figures</td></tr>
    <tr><th scope="row">Odds disclosure</th><td>Per-card pull percentages in-app; nothing on the website</td></tr>
    <tr><th scope="row">Expected value</th><td>Not published and not calculable from public information</td></tr>
    <tr><th scope="row">Buyback</th><td>90% of displayed FMV; 100% on the first pack purchase</td></tr>
    <tr><th scope="row">Decision window</th><td>3 hours from opening the pack, then auto-sold; shorter in some states</td></tr>
    <tr><th scope="row">Withdrawals</th><td>To a bank card; $6 minimum, $2,500 maximum per withdrawal; sale proceeds only</td></tr>
    <tr><th scope="row">Storage</th><td>PSA slabs held in secure vaults until shipped or sold back</td></tr>
    <tr><th scope="row">New user offer</th><td>One free pack on joining</td></tr>
    <tr><th scope="row">Restricted states</th><td>Michigan, Minnesota, Montana, Nevada, Washington</td></tr>
    <tr><th scope="row">Age</th><td>18+, or 19 in Nebraska</td></tr>
  </tbody>
  </table>
  </div>

  <div class="callout">
    <h3>Why this page has no rating, and what we still need</h3>
    <p>Everything here comes from Pickem's public marketing and two independent reviews. We have not collected the in-app odds ourselves, so no expected value can be calculated and no score published. We also want to confirm the exact length of the window in each state, whether it differs by pack, and whether the free first pack counts as the &ldquo;first purchase&rdquo; that triggers the 100% buyback. If you have screenshots of a Pickem pack page showing per-card percentages, we would like to see them.</p>
  </div>

  <div class="callout danger">
    <h3>If you buy, decide before you rip</h3>
    <p>On a three-hour clock, the time to decide what you would keep is before you open the pack, not after. Know in advance what a pull has to be worth for you to ship it, and remember that the alternative is not holding the card &mdash; it is Pickem selling it at a value Pickem sets.</p>
    <p>If this has stopped feeling like fun, free and confidential help is available: call or text <strong>1-800-GAMBLER</strong>.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/guides/buyback-rates/">What a buyback is actually worth, across every platform</a></li>
    <li><a href="/platforms/packed/">Packed, the other short-clock platform</a></li>
    <li><a href="/platforms/">All twenty-four platforms compared</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html, **{"flags_pickem": flag_row("pickem")})

    return pages_written("/platforms/pickem/", page(
        "/platforms/pickem/",
        "Pickem Ripping Packs review — three hours to decide on a pull",
        "Pickem pays 90% of FMV withdrawable to a bank card, but gives you three hours from opening a pack before it sells the card automatically.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "Pickem")],
        updated=UPDATED, structured=faq_ld))


def build_packed():
    faq_html, faq_ld = faq_block([
        ("How long can you keep a card on Packed?",
         "<p>One day. Section 6.3 of the Terms of Use states &ldquo;You may only store a Collectible for a maximum of one (1) day,&rdquo; and adds that Packed may change that period &ldquo;at any time, in its sole discretion and without prior notice to you.&rdquo; Section 6.1 says that once the window closes, inventory &ldquo;will be automatically returned to Packed.&rdquo; To keep a card you have to request shipment inside that window, and shipping requires completed identity verification. It is the shortest holding period of any platform we track, against seven days at Crown Rips and indefinite free vaulting at Courtyard, Arena Club, Fanatics and Tilt Rips.</p>"),
        ("Does Packed really buy back at 100%?",
         "<p>At 100% of its own fair market value, yes, and unlike most of the category you can withdraw the proceeds &mdash; to a debit card, bank account, PayPal or Venmo, with a minimum around $5 to $10. Two conditions matter. The offer only stands for the storage window, which the terms set at one day. And the FMV is Packed's own figure, produced by what the FAQ calls a &ldquo;semi-automated proprietary system&rdquo; which Packed does not claim matches external market calculations.</p>"),
        ("Does Packed publish pack odds?",
         "<p>Its terms require it to. Section 6.2(b) obliges Packed to display each Value Band's probabilities, which may be shown as ranges, and section 6.2(e) states that the likelihood of allocation from each band falls within the published range. That is a stronger commitment than most of this category offers, and it is written into the contract rather than the marketing. The methodology behind the bands is proprietary and not disclosed, and we have not yet confirmed first-hand what the in-app figures look like.</p>"),
        ("Is the minimum item value on a Packed pack guaranteed?",
         "<p>No. Section 6.2(c) says &ldquo;The Minimum Item Value is an estimate only and is not a guaranteed amount,&rdquo; and section 6.2(f) states that the item you receive may have a fair market value below the minimum shown at purchase. Every other platform that advertises a floor presents it as a floor. Here the advertised minimum is explicitly an estimate you can land beneath.</p>"),
        ("Do you lose your deposit bonus if you withdraw from Packed?",
         "<p>Yes. Section 7.5 states that unused Promotional Credit &ldquo;will be forfeited&rdquo; upon a withdrawal, and section 7.3(b) says &ldquo;You may only withdraw Sale Proceeds. You cannot withdraw Purchase Credit or Promotional Credit.&rdquo; So the advertised deposit bonuses &mdash; $50 on $500, $30 on $300, $15 on $150 &mdash; are spendable on eligible packs but cannot be cashed out, and taking money out destroys whatever is left of them.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Packed: a real 100% buyback with a one-day clock on it</h1>
    <p class="lede">Packed pays 100% of fair market value and the money genuinely reaches your bank &mdash; the best cash terms we have verified. Its Terms of Use also give you one day to decide before the card is taken back automatically.</p>
    {flags_packed}
  </div>

  <div class="finding">
    <p class="big">Section 6.3: &ldquo;You may only store a Collectible for a maximum of one (1) day,&rdquo; changeable by Packed &ldquo;at any time, in its sole discretion and without prior notice.&rdquo; After the window, section 6.1 says inventory &ldquo;will be automatically returned to Packed.&rdquo; That is the shortest holding period in the category by a factor of seven, and it is the condition attached to the strongest buyback in the category.</p>
    <p class="small muted">Read from playpacked.com, its FAQ and its Terms of Use on {collected}. We have not yet verified the in-app experience first-hand.</p>
  </div>

  <h2>What Packed does better than anyone else</h2>
  <p>It is worth leading with this, because on two counts Packed sets the standard for the category.</p>

  <p><strong>Odds disclosure is written into the contract.</strong> Section 6.2(b) obliges Packed to display each Value Band's probabilities, and 6.2(e) commits that the real likelihood falls within the published range. Most platforms here either publish nothing (<a href="/platforms/tilt-rips/">Tilt Rips</a>, <a href="/platforms/fast-rips/">Fast Rips</a>) or disclose at their own discretion. Packed is the only one we have found that contractually binds itself to publish.</p>

  <p><strong>The money actually comes out.</strong> Withdrawals go to a debit card, bank account, PayPal or Venmo, with a minimum of about $5 to $10 and instant transfers averaging roughly ten minutes per the FAQ. Set that against <a href="/platforms/packz/">Packz</a> and <a href="/platforms/fanatics-instant-rips/">Fanatics</a>, where the buyback pays credit that cannot be withdrawn at all.</p>

  <p><strong>And the valuation is locked at the pull.</strong> Section 6.4 fixes a collectible's FMV at the moment it comes out of the pack. That protects you from a downward revision between the pull and your decision, which matters more than it sounds on a platform that sets its own values.</p>

  <h2>Four terms that cut the other way</h2>

  <h3>1. One day to decide</h3>
  <p>The storage window is the sharpest term on any platform we have read. <a href="/platforms/crown-rips/">Crown Rips</a> reportedly auto-sells after seven days and we called that the most consequential term on that platform. Packed does it in one, reserves the right to shorten it without notice, and shipping a card out requires completed identity verification &mdash; so if you pull something you want to keep before you have verified, the clock is running while you do the paperwork.</p>

  <h3>2. The minimum is not a minimum</h3>
  <p>Section 6.2(c): &ldquo;The Minimum Item Value is an estimate only and is not a guaranteed amount.&rdquo; Section 6.2(f) goes further and says the item you receive may have an FMV below the minimum shown at purchase. Across this category we have compared floors as a percentage of pack price &mdash; roughly 70% at Courtyard, 50% at Packz, 30% at Crown Rips. Packed's is not a floor at all in the sense those are.</p>

  <h3>3. Withdrawing forfeits your bonus</h3>
  <p>Packed advertises deposit bonuses of $50 on $500, $30 on $300 and $15 on $150. Section 7.3(b) says you may only withdraw Sale Proceeds, not Purchase Credit or Promotional Credit. Section 7.5 says unused Promotional Credit &ldquo;will be forfeited&rdquo; on a withdrawal.</p>
  <p>So the bonus is spendable but not cashable, and the act of taking money out destroys whatever remains of it. That is a familiar structure from online casinos and an unfamiliar one in collectibles; it is also the mechanism that makes a deposit bonus into a reason not to withdraw.</p>

  <h3>4. Ten minutes or two weeks</h3>
  <p>The FAQ says instant withdrawals average about ten minutes. Section 7.3 of the terms says withdrawals are processed &ldquo;within two weeks.&rdquo; Both can be true &mdash; the terms setting an outer bound, the FAQ describing the norm &mdash; but it is the familiar pattern of the marketing figure and the contractual figure being very far apart.</p>

  <h2>Compared with the rest</h2>
  <div class="table-wrap">
  <table>
  <caption>How Packed's terms compare on the two things that decide what a buyback is worth, {collected}.</caption>
  <thead><tr><th scope="col">Platform</th><th scope="col" class="num">Buyback</th><th scope="col">Withdrawable</th><th scope="col">How long you can hold a card</th></tr></thead>
  <tbody>
    <tr><td class="name">Packed</td><td class="num">100%</td><td><strong class="pos">Yes</strong>, card, bank, PayPal, Venmo</td><td><strong class="neg">1 day</strong></td></tr>
    <tr><td class="name">Chalkboard Pulls</td><td class="num">100%</td><td><strong class="pos">Yes</strong>, ACH via Aeropay</td><td><strong class="neg">24 hours</strong></td></tr>
    <tr><td class="name">Arena Club</td><td class="num">90%</td><td><strong class="pos">Yes</strong>, to a bank via Stripe</td><td>Indefinite</td></tr>
    <tr><td class="name">Tilt Rips</td><td class="num">90%</td><td><strong class="pos">Yes</strong>, cash or crypto</td><td>Indefinite, free vaulting</td></tr>
    <tr><td class="name">Courtyard</td><td class="num">90% advertised</td><td>USDC, unconfirmed</td><td>Indefinite, vaulted and insured</td></tr>
    <tr><td class="name">Fanatics</td><td class="num">84.6% effective</td><td><strong class="neg">No</strong>, credit only</td><td>Indefinite, free, no time limit</td></tr>
    <tr><td class="name">Packz</td><td class="num">90%</td><td><strong class="neg">No</strong>, packs only</td><td>Not stated</td></tr>
    <tr><td class="name">Crown Rips</td><td class="num">100% claimed</td><td>Unconfirmed</td><td>7 days, reportedly</td></tr>
    <tr><td class="name">Fast Rips</td><td class="num">100% advertised</td><td><strong class="neg">No</strong> per its terms</td><td>Not stated</td></tr>
  </tbody>
  </table>
  </div>

  <p>Read that table as a single trade. Packed pays the most and lets you take it out, and in exchange gives you the least time to think. Arena Club and Tilt Rips pay ten points less with no clock at all. Which is better depends entirely on whether you intend to keep anything.</p>

  <h2>What we cannot yet tell you</h2>
  <p>No prices or odds appear on the website for any of the 21 packs across Pok&eacute;mon, basketball, baseball and One Piece. The terms require odds to be shown, so they presumably appear in the iOS app at the point of purchase, but a buyer researching beforehand cannot see a single number. Until we collect the in-app Value Bands we cannot calculate an expected value for any Packed pack, and the platform is unrated for that reason.</p>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Categories</th><td>Pok&eacute;mon, basketball, baseball, One Piece &mdash; 21 packs</td></tr>
    <tr><th scope="row">Pack prices</th><td>Not published on the web</td></tr>
    <tr><th scope="row">Odds disclosure</th><td>Required by &sect;6.2(b) to display Value Band probabilities; not shown on the website</td></tr>
    <tr><th scope="row">Expected value</th><td>Not calculable from published information</td></tr>
    <tr><th scope="row">Buyback</th><td>100% of Packed's FMV, locked at the moment of the pull</td></tr>
    <tr><th scope="row">Storage window</th><td>One day (&sect;6.3), changeable without notice</td></tr>
    <tr><th scope="row">Withdrawals</th><td>Debit card, bank, PayPal, Venmo; ~$5&ndash;$10 minimum; instant averages ~10 min per the FAQ, &ldquo;within two weeks&rdquo; per &sect;7.3</td></tr>
    <tr><th scope="row">Tax thresholds</th><td>Forms required above $600 (FAQ) or $2,500 per calendar year (&sect;7.3)</td></tr>
    <tr><th scope="row">Deposit bonuses</th><td>$50 on $500, $30 on $300, $15 on $150 &mdash; not withdrawable, forfeited on withdrawal</td></tr>
    <tr><th scope="row">Refunds</th><td>&ldquo;All purchases, winning Bids, and Tips are final and binding&rdquo; (&sect;7.4.2)</td></tr>
    <tr><th scope="row">Also offers</th><td>Live streamed rips and live auctions</td></tr>
    <tr><th scope="row">Eligibility</th><td>18+, US only, government ID and liveness check via Footprint</td></tr>
  </tbody>
  </table>
  </div>

  <div class="callout">
    <h3>Our relationship with Packed, and why it is worth knowing</h3>
    <p><strong>We hold a Packed referral code and earn from signups made through it.</strong> The link appears below. You should weigh everything on this page knowing that.</p>
    <p>Packed's affiliate terms prohibit affiliates from describing Packed as gambling, from stating odds or pull rates Packed has not published, and from disparaging the company. We have published the one-day storage limit, the non-guaranteed minimum item value and the bonus forfeiture clause anyway, because they are quotations from Packed's own Terms of Use and a reader deciding whether to deposit needs them. If that costs us the code, the findings stay and the code goes.</p>
    <p>Packed also pays the lowest affiliate rate we have seen in this category: a tiered revenue share from 0.50% to 2.50% of referred pack purchases over a 90-day attribution window. <a href="/methodology/">Our policy on commissions is here.</a></p>
  </div>

  {cta}

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/guides/buyback-rates/">What a buyback is actually worth, across every platform</a></li>
    <li><a href="/platforms/fast-rips/">Fast Rips, where the terms contradict the marketing</a></li>
    <li><a href="/platforms/">All twenty-four platforms compared</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html, cta=affiliate_cta("packed"), **{"flags_packed": flag_row("packed")})

    return pages_written("/platforms/packed/", page(
        "/platforms/packed/",
        "Packed review — 100% buyback, but you get one day to decide",
        "Packed pays 100% of FMV withdrawable to a bank, PayPal or Venmo. Section 6.3 of its terms gives you one day to hold a card before it is automatically returned.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "Packed")],
        updated=UPDATED, structured=faq_ld))


def build_fast_rips():
    faq_html, faq_ld = faq_block([
        ("Does Fast Rips really buy cards back at 100%?",
         "<p>Its homepage advertises &ldquo;100% FMV Buyback&rdquo; and &ldquo;Cash Out to Bank.&rdquo; Its Terms of Use set no fixed buyback rate at all, and its Platform Statement says there is no buyback programme as such. What the terms describe is an optional return for certain Mystery Box contents, paid in Platform Credit rather than money, and only &ldquo;where applicable.&rdquo; We could not reconcile the two, and the terms themselves state that they control in the event of a conflict.</p>"),
        ("Can you withdraw money from Fast Rips?",
         "<p>The homepage says &ldquo;Withdraw proceeds to your bank account.&rdquo; Section 6.3 of the Terms of Use says Platform Credit &ldquo;has no cash value outside the Platform&rdquo; and is not withdrawable, and the Platform Statement calls it &ldquo;Non-cash, not legal tender, and for Platform use only.&rdquo; Withdrawals appear only as a discretionary possibility: &ldquo;If and when the Company, in its sole discretion, offers the ability to withdraw certain balances.&rdquo; It is possible that cashing out is a separate flow from the credit return and simply is not documented, but as published the two statements conflict.</p>"),
        ("Does Fast Rips publish pack odds?",
         "<p>Not currently. No odds, pull rates or prices appear on its website for any of its seven packs. The Terms say odds are disclosed &ldquo;where required by law or where the Company, in its sole discretion, chooses to do so,&rdquo; and that odds &ldquo;are subject to change over time.&rdquo; The Platform Statement says that where odds are shown, &ldquo;the applicable Odds are those shown at the time of your transaction.&rdquo; Odds may therefore appear inside the iOS app even though none are published on the web.</p>"),
        ("How does Fast Rips decide what a card is worth?",
         "<p>It decides itself. The Terms describe fair market value as &ldquo;a proprietary, Platform-administered valuation used exclusively for internal Platform purposes,&rdquo; which can change without notice and carries &ldquo;no guarantee&rdquo; that it reflects any resale price. Since the advertised buyback is a percentage of that figure, the company sets both the rate and the number the rate is applied to.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Fast Rips: the homepage and the terms do not agree</h1>
    <p class="lede">Fast Rips advertises a 100% buyback paid out to your bank account, which would be the best terms of any platform we track. Its own Terms of Use say Platform Credit has no cash value outside the platform and is not withdrawable.</p>
    {flags_fast_rips}
  </div>

  <div class="finding">
    <p class="big">The homepage says &ldquo;100% FMV Buyback&rdquo; and &ldquo;Withdraw proceeds to your bank account.&rdquo; Section 6.3 of the Terms of Use says Platform Credit &ldquo;has no cash value outside the Platform&rdquo; and is not withdrawable, and the Platform Statement describes no buyback programme at all &mdash; only an optional return paid in credit, &ldquo;not a cash refund unless we explicitly state otherwise.&rdquo;</p>
    <p class="small muted">Read from fastrips.com, its Terms of Use and its Platform Statement on {collected}. The Terms state that they control in the event of a conflict.</p>
  </div>

  <h2>What each document says</h2>
  <div class="table-wrap">
  <table>
  <caption>Fast Rips' marketing claims against its own published terms, {collected}.</caption>
  <thead><tr><th scope="col">Question</th><th scope="col">Homepage</th><th scope="col">Terms of Use and Platform Statement</th></tr></thead>
  <tbody>
    <tr>
      <th scope="row">Is there a buyback?</th>
      <td>&ldquo;100% FMV Buyback,&rdquo; stated twice</td>
      <td>No fixed rate anywhere in the terms. The Platform Statement says there is no buyback programme as such, only an optional return &ldquo;where applicable&rdquo;</td>
    </tr>
    <tr>
      <th scope="row">What do you get paid in?</th>
      <td>&ldquo;Cash Out to Bank&rdquo;</td>
      <td>&ldquo;Platform Credit equal to the item(s)' calculated FMV&rdquo; &mdash; &ldquo;not a cash refund unless we explicitly state otherwise&rdquo;</td>
    </tr>
    <tr>
      <th scope="row">Can you withdraw it?</th>
      <td>&ldquo;Withdraw proceeds to your bank account&rdquo;</td>
      <td>Platform Credit &ldquo;has no cash value outside the Platform&rdquo; and is not withdrawable (&sect;6.3). Withdrawals exist only &ldquo;if and when the Company, in its sole discretion, offers&rdquo; them</td>
    </tr>
    <tr>
      <th scope="row">Who values the card?</th>
      <td>Not stated</td>
      <td>&ldquo;A proprietary, Platform-administered valuation used exclusively for internal Platform purposes,&rdquo; changeable without notice, with &ldquo;no guarantee&rdquo; it reflects resale price (&sect;4.5)</td>
    </tr>
    <tr>
      <th scope="row">Are there fees?</th>
      <td>Not mentioned</td>
      <td>Users pay &ldquo;payment processing fees, marketplace commissions, withdrawal fees&rdquo; (&sect;6.4)</td>
    </tr>
    <tr>
      <th scope="row">Are odds published?</th>
      <td>No odds or prices shown for any pack</td>
      <td>Disclosed &ldquo;where required by law or where the Company, in its sole discretion, chooses to do so&rdquo; (&sect;3.1)</td>
    </tr>
  </tbody>
  </table>
  </div>

  <h2>The fair reading</h2>
  <p>We are not alleging that Fast Rips will refuse to pay anyone, and there is a plausible innocent explanation. The return option described in the terms covers Mystery Box contents and pays credit; the cash-out advertised on the homepage may be a separate flow for what the Platform Statement calls &ldquo;Eligible Funds,&rdquo; which it says may be withdrawable subject to verification, limits, delays and AML and KYC checks. On that reading both statements can be true at once and the terms simply do not document the cash path.</p>

  <p>But that reading has to be inferred, and a buyer should not have to infer it. As published, the homepage makes an unconditional promise &mdash; 100%, to your bank account &mdash; and the governing document says the credit it pays has no cash value outside the platform and that withdrawals are at the company's sole discretion. The terms state that they control in a conflict, which means the document that wins is the one that promises less.</p>

  <div class="callout danger">
    <h3>What to confirm before you deposit</h3>
    <p>Ask Fast Rips directly, in writing, and keep the answer: is the 100% buyback paid in withdrawable funds or in Platform Credit, what fees are deducted, and what is the minimum and typical processing time for a withdrawal to a bank account? If the answer is credit, the advertised 100% is worth materially less than the 90% that Arena Club and Tilt Rips pay into withdrawable wallets.</p>
    <p>We have contacted Fast Rips for clarification and will update this page with their response.</p>
  </div>

  <h2>Everything else is undisclosed</h2>
  <p>Seven packs are listed &mdash; Fresh, Basic, Pro, Bronze, Silver, Gold and Diamond &mdash; and <strong>not one shows a price</strong>. Every price field on the site renders as a dash. There are no odds, no value tiers, no floor, no ceiling and no expected value for any of them.</p>

  <p>That may simply be because the product lives in the iOS app rather than on the web; the Platform Statement says that where odds are shown, &ldquo;the applicable Odds are those shown at the time of your transaction,&rdquo; which implies they appear somewhere. But a prospective buyer researching the platform before downloading anything can learn neither what a pack costs nor what is in it.</p>

  <h2>The language rule</h2>
  <p>One clause is worth noting on its own. Section 3.4 prohibits users from describing the platform as a gambling product, or from using the words &ldquo;bet,&rdquo; &ldquo;wager,&rdquo; &ldquo;jackpot,&rdquo; &ldquo;stake&rdquo; or &ldquo;payout&rdquo; when promoting it, unless the company approves. The Terms also assert that buying a Mystery Box &ldquo;is not a form of gambling, a wager on a sporting event or contest, a lottery.&rdquo;</p>

  <p>Every platform in this category makes some version of that argument, and as our <a href="/is-card-ripping-gambling/">page on the legal position</a> sets out, the question is genuinely unsettled and being tested in court. What is unusual here is contractually restricting what customers may call it. A company's terms cannot determine how a regulator classifies its product, and a rule of that kind is aimed at affiliates and reviewers rather than at regulators.</p>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Product</th><td>Mystery Boxes, randomised, one physical card per pack, raw or PSA-graded</td></tr>
    <tr><th scope="row">Also offered</th><td>Collectible Packs, with contents disclosed before purchase and not randomised</td></tr>
    <tr><th scope="row">Packs</th><td>Fresh, Basic, Pro, Bronze, Silver, Gold, Diamond &mdash; no prices published</td></tr>
    <tr><th scope="row">Odds disclosure</th><td>None on the web; discretionary under the terms</td></tr>
    <tr><th scope="row">Expected value</th><td>Not published and not calculable</td></tr>
    <tr><th scope="row">Advertised buyback</th><td>100% of FMV</td></tr>
    <tr><th scope="row">Buyback in the terms</th><td>Platform Credit, non-withdrawable; no fixed rate stated</td></tr>
    <tr><th scope="row">Valuation</th><td>Proprietary and internal; no guarantee it matches resale value</td></tr>
    <tr><th scope="row">Refunds</th><td>Purchases &ldquo;generally deemed final and non-refundable&rdquo; (&sect;6.2)</td></tr>
    <tr><th scope="row">Inventory</th><td>Held in a US warehouse; ships within a week, delivered in about two</td></tr>
    <tr><th scope="row">Availability</th><td>iOS app; 18+ or local age of majority; some jurisdictions restricted, VPNs prohibited</td></tr>
    <tr><th scope="row">Third-party coverage</th><td>None found</td></tr>
  </tbody>
  </table>
  </div>

  <div class="callout">
    <h3>Why this page has no rating</h3>
    <p>We score platforms on pack expected value, buyback quality, odds transparency, payouts and trust. Fast Rips publishes no prices and no odds, so three of those cannot be assessed, and its buyback terms contradict its marketing, so the fourth cannot be stated with confidence. A score would imply a precision we do not have. <a href="/methodology/">Our methodology</a> explains why we leave a cell empty rather than guess.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/guides/buyback-rates/">What a 90% buyback actually pays, across every platform</a></li>
    <li><a href="/platforms/">All twenty-four platforms compared</a></li>
    <li><a href="/is-card-ripping-gambling/">Where the law currently stands</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html, **{"flags_fast_rips": flag_row("fast-rips")})

    return pages_written("/platforms/fast-rips/", page(
        "/platforms/fast-rips/",
        "Fast Rips review — the 100% buyback its own terms do not describe",
        "Fast Rips advertises a 100% buyback paid to your bank account. Its Terms of Use say Platform Credit has no cash value outside the platform and is not withdrawable.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "Fast Rips")],
        updated=UPDATED, structured=faq_ld))


def build_chalkboard():
    faq_html, faq_ld = faq_block([
        ("Does Chalkboard Pulls really pay 100% of a card's value?",
         "<p>Yes, as written, and the money can leave the platform. Section 7.1 of the Chalkboard Pulls Terms of Use provides &ldquo;a credit of one hundred percent (100%) of that Collectible's FMV to Your Account,&rdquo; and section 9.2 lets you &ldquo;request withdrawal of available Buyback Credit to an eligible external payment method.&rdquo; ACH withdrawals are processed through Aeropay, typically within ten business days. That is the clearest cash route we have read in this category. The catch is not the rate &mdash; it is who decides the number the rate is applied to.</p>"),
        ("Who decides what a Chalkboard card is worth?",
         "<p>Chalkboard does, and the decision cannot be appealed. Section 7.5 says &ldquo;FMV is determined by Chalkboard in its sole discretion utilizing proprietary methodologies and market data&rdquo; and that it is &ldquo;final and non-appealable.&rdquo; The help centre adds that Chalkboard's figure &ldquo;may differ from third-party marketplaces or pricing services.&rdquo; Section 7.6 states plainly that the buyback credit may be lower than what you paid for the pack. 100% of a number one party sets alone is not the same guarantee as 100% of a published market price.</p>"),
        ("How long do you have to decide on a Chalkboard pull?",
         "<p>One 24-hour period from the pack purchase (&sect;7.3). If you do nothing, Chalkboard processes a Time-Based Buyback at 100% of FMV automatically and the card leaves your Binder. The clock can pause for pending identity verification, delayed shipping, or a lost, damaged or unavailable card. That matches Packed's one day and is far shorter than the indefinite vaulting Courtyard, Arena Club, Fanatics and Tilt Rips offer.</p>"),
        ("Does Chalkboard publish pack odds?",
         "<p>Not on the web. Section 5.1 says the Collectible categories and associated statistics are disclosed before purchase, and the help centre says a pack page &ldquo;may include&rdquo; its price, value range, featured pulls and odds. So the numbers exist inside the app. Nothing appears on any public page, so a buyer researching beforehand cannot see a single figure, and we cannot calculate an expected value. Section 5.1 also warns that &ldquo;the distribution among possible outcomes may not be, and is likely not to be, equal.&rdquo;</p>"),
        ("Are free packs on Chalkboard worth anything?",
         "<p>Less than they look. The help centre states that value sold back from a Free Pack is credited as &ldquo;play-through funds, not as withdrawable funds,&rdquo; and becomes withdrawable only after you use it &mdash; for example by buying and opening another pack. The same article confirms that for a paid pack, &ldquo;100% of the FMV is credited straight to your withdrawable Wallet balance.&rdquo; No multiplier or dollar threshold is published for the play-through, so the real cost of converting it cannot be calculated.</p>"),
        ("Who operates Chalkboard Pulls?",
         "<p>Taild Sports, Inc., trading as Chalkboard. Pulls sits inside the Chalkboard daily fantasy sports app rather than being a standalone rip site &mdash; the same structure as Pickem inside a social casino and Crown Rips inside a sweepstakes casino. Disputes go to individual arbitration under the JAMS rules with a class-action waiver (&sect;18), after a required informal conference and 30 days of negotiation (&sect;17.9), and there is a 30-day opt-out from arbitration.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Chalkboard Pulls: the best cash terms we have read, on a price you cannot appeal</h1>
    <p class="lede">Chalkboard pays 100% of fair market value into a wallet you can withdraw from &mdash; the clearest cash route in the category. The same terms make Chalkboard the sole and &ldquo;final and non-appealable&rdquo; judge of that value.</p>
    {flags_chalkboard}
  </div>

  <div class="finding">
    <p class="big">&sect;7.1 credits &ldquo;one hundred percent (100%) of that Collectible's FMV,&rdquo; and &sect;9.2 lets that credit be withdrawn to an external payment method. &sect;7.5 then says &ldquo;FMV is determined by Chalkboard in its sole discretion utilizing proprietary methodologies and market data&rdquo; and is &ldquo;final and non-appealable.&rdquo; &sect;7.6 adds that the credit may be lower than the price you paid.</p>
    <p class="small muted">Read from the Chalkboard Pulls Terms of Use and the Chalkboard help centre on {collected}. No odds or pack prices are published on the web.</p>
  </div>

  <h2>Why a 100% buyback is not the whole story</h2>
  <p>Twelve of the twenty-four platforms we track advertise a buyback rate. The rate is the number in the marketing; the two things that decide what it is worth are whether the money can leave the platform, and who sets the value it is a percentage of. Chalkboard is the only platform we have read that is unambiguously best-in-class on the first and explicitly worst-case on the second.</p>

  <div class="table-wrap">
  <table>
  <caption>The two questions that decide what a buyback is worth, across the platforms whose terms we have read, {collected}.</caption>
  <thead><tr><th scope="col">Platform</th><th scope="col" class="num">Rate</th><th scope="col">Money can leave</th><th scope="col">Who sets the value</th><th scope="col">Disputable</th></tr></thead>
  <tbody>
    <tr><td class="name">Chalkboard Pulls</td><td class="num">100%</td><td><strong class="pos">Yes</strong>, ACH via Aeropay</td><td>Chalkboard, sole discretion</td><td><strong class="neg">No</strong>, &ldquo;non-appealable&rdquo;</td></tr>
    <tr><td class="name">Packed</td><td class="num">100%</td><td><strong class="pos">Yes</strong>, card, bank, PayPal</td><td>Packed, semi-automated</td><td>Not stated</td></tr>
    <tr><td class="name">Arena Club</td><td class="num">90%</td><td><strong class="pos">Yes</strong>, bank via Stripe</td><td>Arena Club, grades some itself</td><td>Not stated</td></tr>
    <tr><td class="name">Tilt Rips</td><td class="num">90%</td><td><strong class="pos">Yes</strong>, cash or crypto</td><td>&ldquo;Live market data,&rdquo; unnamed</td><td><strong class="neg">No</strong></td></tr>
    <tr><td class="name">Pickem</td><td class="num">90%</td><td><strong class="pos">Yes</strong>, bank card</td><td>Pickem's displayed FMV</td><td>Not stated</td></tr>
    <tr><td class="name">Fanatics Instant Rips</td><td class="num">84.6%</td><td><strong class="neg">No</strong>, credit only</td><td><strong class="pos">Card Ladder</strong>, a third party</td><td><strong class="pos">Yes</strong>, vs the dataset</td></tr>
    <tr><td class="name">MintPull</td><td class="num">100% ad.</td><td><strong class="neg">No</strong>, pack credit</td><td>&ldquo;Proprietary system&rdquo;</td><td>Not stated</td></tr>
    <tr><td class="name">Fast Rips</td><td class="num">100% ad.</td><td><strong class="neg">No</strong> per its terms</td><td>Internal platform valuation</td><td>Not stated</td></tr>
  </tbody>
  </table>
  </div>

  <p>Read the top and bottom rows together. Chalkboard pays more than Fanatics, in money rather than credit, with no fee deducted. Fanatics pays less, in credit you cannot withdraw, against a number from a third-party sales database anyone can look up. Those are opposite trades, and which one is better depends on something neither platform publishes: how close each valuation actually lands to what the card sells for.</p>

  <p>That is the open question on this entire site, and it is why no platform here carries a score yet. A rate is checkable from a document. A valuation is only checkable against real sold prices, and we have not yet verified a single platform's valuations against those.</p>

  <h2>The 24-hour clock</h2>
  <p>Section 7.3 gives you &ldquo;one (1) twenty-four (24) hour period&rdquo; from the pack purchase to request either shipping or a buyback. Do nothing and a Time-Based Buyback is processed at 100% of FMV, and the card is removed from your Binder. The window can pause for pending identity verification, pending or delayed shipping, or resolution of a lost, damaged or unavailable card.</p>

  <p>The pause for identity verification matters more than it reads. Shipping a card requires a verified identity, so a first-time user who pulls something they want to keep is racing a clock while waiting on a verification queue. The terms do allow for that by pausing, which is better than not allowing for it &mdash; Pickem's three-hour timer makes no such provision.</p>

  <div class="table-wrap">
  <table class="plain">
  <caption>Decision windows across the twenty-four platforms we track.</caption>
  <thead><tr><th scope="col">Window</th><th scope="col">Platforms</th></tr></thead>
  <tbody>
    <tr><th scope="row">3 hours</th><td>Pickem</td></tr>
    <tr><th scope="row">1 day</th><td>Packed, <strong>Chalkboard Pulls</strong></td></tr>
    <tr><th scope="row">7 days</th><td>Crown Rips (reported), MintPull</td></tr>
    <tr><th scope="row">Indefinite</th><td>Courtyard, Arena Club, Fanatics Instant Rips, Tilt Rips</td></tr>
    <tr><th scope="row">Not stated</th><td>Packz, Fast Rips, Clutch Packs</td></tr>
  </tbody>
  </table>
  </div>

  <p>The pattern we noted on the <a href="/platforms/pickem/">Pickem page</a> holds again. The platforms paying the highest withdrawable rates &mdash; Packed and Chalkboard at 100%, Pickem at 90% &mdash; are the three with the shortest clocks. A platform that will reliably buy a card back does not want to hold inventory, and the clock is how it avoids that. You are being paid well in exchange for deciding fast.</p>

  <h2>The free pack is not free money</h2>
  <p>Chalkboard sends Free Packs as promotional cards in the Promos tab, with no purchase required and an expiry date on each one. The pack opens like any other and you can keep the card or sell it back. The difference is in what the sell-back pays.</p>

  <div class="callout">
    <h3>Paid pack versus free pack, in Chalkboard's own words</h3>
    <p><strong>Paid pack:</strong> &ldquo;100% of the FMV is credited straight to your withdrawable Wallet balance.&rdquo;</p>
    <p><strong>Free pack:</strong> the sell-back value is credited as &ldquo;play-through funds, not as withdrawable funds,&rdquo; and becomes withdrawable only after you use it &mdash; for example by buying and opening another pack.</p>
  </div>

  <p>This is the standard structure of a casino bonus, and it is the first time we have seen it stated this plainly in a rip product. It is not hidden &mdash; Chalkboard publishes it in a help article specifically about free packs, which is more than most platforms do with their promotional terms. But it means a free pack's value is not its face value. No multiplier or dollar threshold is published, so how much you must cycle through before the money is yours cannot be calculated from anything public.</p>

  <p>We rank bonus offers by what they are actually worth on the <a href="/guides/bonus-offers/">bonus offers page</a>, and a play-through-restricted credit sits well below a straight discount for exactly this reason.</p>

  <h2>Odds exist, but not where you can see them</h2>
  <p>Section 5.1 says the Collectible categories and associated statistics are disclosed before purchase, and the help centre says a pack page &ldquo;may include&rdquo; its price, the range of card values, featured or Signature Pulls, and odds. So the numbers are shown at the point of sale inside the app. None of them appear on any public page.</p>

  <p>Two sentences in those documents deserve attention.</p>

  <p>Section 5.1 warns that &ldquo;the distribution among possible outcomes may not be, and is likely not to be, equal.&rdquo; That is the same candid warning <a href="/platforms/mintpull/">MintPull</a> gives in capitals, and it is a fair one: it says that where a pack shows a value range, the outcomes inside that range are probably not evenly spread. It is also precisely the assumption our own midpoint estimates have to make when a platform publishes ranges without rates.</p>

  <p>The help centre then adds that odds &ldquo;can change as packs are purchased,&rdquo; so the odds shown may differ on a later visit. That is honest, and it is a real problem for anyone trying to hold this category to account. A screenshot of a pack's odds is evidence about one moment, not about the pack. It is the same issue we hit on <a href="/platforms/arena-club/">Arena Club</a>, where not one card from the September checklist survived into October.</p>

  <h2>Terms worth knowing before you deposit</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>Taild Sports, Inc. d/b/a Chalkboard; Pulls sits inside the Chalkboard fantasy sports app</td></tr>
    <tr><th scope="row">Model</th><td>Purchase. You buy an Item and the Reveal allocates a randomised Collectible (&sect;5.1). No free method of entry is described, so this is not a sweepstakes</td></tr>
    <tr><th scope="row">Buyback</th><td>100% of FMV as Buyback Credit (&sect;7.1); final once processed (&sect;7.2); may be lower than the price paid (&sect;7.6)</td></tr>
    <tr><th scope="row">Withdrawals</th><td>Buyback Credit only, to an eligible external payment method; ACH via Aeropay; typically within ten business days; all withdrawals final (&sect;9.6)</td></tr>
    <tr><th scope="row">Deposits</th><td>&ldquo;Non-refundable and non-transferable&rdquo; (&sect;8.2) &mdash; a deposit cannot be withdrawn, only spent</td></tr>
    <tr><th scope="row">Withdrawal limits</th><td>Chalkboard &ldquo;may establish minimum and maximum withdrawal amounts per transaction&rdquo; and limit totals over a rolling period, &ldquo;as disclosed on the Platform&rdquo; (&sect;9.6). No figures are published</td></tr>
    <tr><th scope="row">Inactivity fee</th><td><strong class="neg">$4.00 per month</strong> on inactive accounts (&sect;4.5.2) &mdash; the only such fee we have found in this category</td></tr>
    <tr><th scope="row">Buyback Credit status</th><td>&ldquo;Not a bank deposit, stored-value account, trust account, escrow account, or custodial account&rdquo; (&sect;9.3)</td></tr>
    <tr><th scope="row">Shipping</th><td>To your own address only, not to third-party vaults; one card at a time</td></tr>
    <tr><th scope="row">Cards</th><td>Physical sports cards, graded and encapsulated or raw and ungraded; the status is shown at Reveal</td></tr>
    <tr><th scope="row">Refunds</th><td>Pack purchases &ldquo;final and non-refundable&rdquo; except where required by law</td></tr>
    <tr><th scope="row">Age</th><td>18+, or the local age of majority if higher (&sect;3.1)</td></tr>
    <tr><th scope="row">States</th><td>Not published in the documents we read. &sect;3.4 says eligibility &ldquo;is generally posted at helps.chalkboard.io&rdquo; and &ldquo;may change from time to time&rdquo;; we could not retrieve that page</td></tr>
    <tr><th scope="row">Disputes</th><td>Individual JAMS arbitration with a class-action waiver (&sect;18); informal conference and 30 days' negotiation first (&sect;17.9); 30-day opt-out</td></tr>
    <tr><th scope="row">Liability cap</th><td>The greater of amounts paid in the prior 180 days or $1,000 &mdash; <strong>with carve-outs for valid Buyback Credit withdrawals and Redemptions</strong> (&sect;16.4)</td></tr>
  </tbody>
  </table>
  </div>

  <h2>Credit where it is due</h2>
  <p>Three things here are better than the category norm, and a guide that only reported the unfavourable terms would be the wrong guide.</p>
  <ul>
    <li><strong>The cash path is documented.</strong> Section 9.2 names the mechanism and section 9.3 names the processor. <a href="/platforms/fast-rips/">Fast Rips</a> advertises cash and describes non-withdrawable credit in its terms; Chalkboard's marketing and contract say the same thing.</li>
    <li><strong>The liability cap carves out withdrawals.</strong> Section 16.4 excludes valid Buyback Credit withdrawals and Redemptions from the $1,000 ceiling. A cap that applied to the money you are owed would be the more alarming clause, and it does not.</li>
    <li><strong>The play-through on free packs is published.</strong> Promotional restrictions are usually the least documented part of these platforms. Chalkboard states this one in a help article about free packs, in plain language.</li>
  </ul>
  <p>None of that resolves section 7.5. A 100% rate on a valuation its payer sets alone, finally and without appeal, is a promise whose value depends entirely on the payer's restraint.</p>

  <div class="callout danger">
    <h3>If you use Chalkboard Pulls</h3>
    <p>Screenshot the pack's odds and value range before you buy, since both can change as packs are purchased, and screenshot the FMV at Reveal. Section 7.5 makes the valuation non-appealable, so the record you keep is the only record there is. Verify your identity before you buy anything you might want shipped, not during the 24-hour window. And note the $4 monthly inactivity fee if you are trying one pack and leaving.</p>
    <p>If this has stopped feeling like fun, free and confidential help is available: call or text <strong>1-800-GAMBLER</strong>.</p>
  </div>

  <div class="callout">
    <h3>Why this page has no rating</h3>
    <p>No pack prices and no odds are published on the web, so no expected value can be calculated &mdash; that is three of our five scoring inputs unavailable. The buyback terms are the best documented we have read, but we have not tested a withdrawal and have not compared a single Chalkboard FMV against a real sold price, which is the measurement that would make the 100% meaningful. <a href="/methodology/">Our methodology</a> explains why we leave a cell empty rather than guess.</p>
    <p>If you have used Chalkboard Pulls and have screenshots of in-app pack odds, or a buyback FMV you can compare against a comparable sale, we would like to see them.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/guides/buyback-rates/">What a buyback is actually worth, across every platform</a></li>
    <li><a href="/platforms/packed/">Packed, the other 100% withdrawable buyback with a one-day clock</a></li>
    <li><a href="/guides/withdrawals/">Getting money out: every platform's withdrawal terms</a></li>
    <li><a href="/platforms/">All twenty-four platforms compared</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html,
           **{"flags_chalkboard": flag_row("chalkboard")})

    return pages_written("/platforms/chalkboard/", page(
        "/platforms/chalkboard/",
        "Chalkboard Pulls review — 100% buyback, on a value you cannot appeal",
        "Chalkboard Pulls pays 100% of fair market value as withdrawable credit — the clearest cash route in the category. Its terms also make Chalkboard the sole, final and non-appealable judge of that value.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"),
                (None, "Chalkboard Pulls")],
        updated=UPDATED, structured=faq_ld))


def build_poke_collect():
    faq_html, faq_ld = faq_block([
        ("What happens to a Poke-Collect card if you do nothing?",
         "<p>You get it. The digital mystery packs page states that cards stay in your vault &ldquo;up to one year&rdquo; and that &ldquo;any cards still in your vault after one year are shipped to you automatically for free.&rdquo; That is the opposite of every other platform we track. Pickem sells the card after three hours, Packed reclaims it after one day, Chalkboard processes an automatic buyback after 24 hours, and MintPull returns it after seven days. On Poke-Collect, inaction ends with the card in your hands.</p>"),
        ("Does Poke-Collect buy cards back?",
         "<p>Not as part of the pack. There is no instant sell-back offer on the pack itself, which is the feature every other platform in this category is built around. Poke-Collect instead runs a separate retail buylist &mdash; &ldquo;Scan &amp; Sell (Beta)&rdquo; with &ldquo;Instant Offers&rdquo; &mdash; paying in &ldquo;Store Credit or PayPal,&rdquo; with cards &ldquo;Reviewed Within 24 Hours.&rdquo; No percentage of value is published. So there is no one-tap liquidity, and no published rate to compare against the 90% and 100% offers elsewhere.</p>"),
        ("How much do Poke-Collect digital packs cost?",
         "<p>Four packs are listed. The Mystery Pack is $9.99 for one card from the Poke, Great, Ultra or Master tiers. The Japanese Edition is $9.99 for one card from the Japanese pool. The Booster Edition is $12.99 for five cards revealed one at a time with the best card last. The Gold Edition is $38.99 for one high-end Near Mint English or Japanese single. That is the lowest ceiling of any platform we track &mdash; most run to $2,500 or $5,000.</p>"),
        ("Does Poke-Collect publish pack odds?",
         "<p>Yes, on the web, which puts it ahead of six of the platforms we track. The pack pages link to a pool page that shows the card list and, in the site's own words, &ldquo;each tier's chance per pack.&rdquo; The catch for us is that the pool renders in the browser rather than in the page source, so we have not been able to collect the figures yet and cannot publish an expected value. That is a limitation on our side, not a disclosure failure on theirs.</p>"),
        ("Who operates Poke-Collect?",
         "<p>A Pok&eacute;mon card shop with a physical storefront at 181 Hughes Road, Suite 5, Madison, Alabama, which also sells sealed product and singles online, runs live breaks on Whatnot, and operates a buylist. The digital packs are one line of an existing retail business rather than the whole company. It is the only operator we track with a street address you can walk into.</p>"),
        ("What does shipping cost on Poke-Collect?",
         "<p>$5 flat for your entire vault, free if you ship 25 or more cards at once, and free for local pickup at the Madison store. Shipping is US addresses only. Cards ship sleeved and top-loaded. Because shipping is charged per vault rather than per card, the cost of taking delivery falls the longer you accumulate &mdash; the reverse of platforms that ship one card at a time.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Poke-Collect: the only platform whose clock ends with you keeping the card</h1>
    <p class="lede">Every other platform we track runs a timer that ends in a forced sale. Poke-Collect's vault runs for a year and then ships the card to you, free. It also has no instant buyback at all, which is the trade.</p>
    {flags_poke_collect}
  </div>

  <div class="finding">
    <p class="big">&ldquo;Any cards still in your vault after one year are shipped to you automatically for free.&rdquo; That one sentence inverts the structure of this entire category. Pickem sells your card after three hours, Packed reclaims it after one day, Chalkboard buys it back automatically after 24 hours, MintPull returns it after seven days. Here, doing nothing ends with a card in the post.</p>
    <p class="small muted">Read from poke-collect.com and its digital mystery packs pages on {collected}. Tier odds are published on the pool page but render in-browser; we have not collected them yet.</p>
  </div>

  <h2>The clock, inverted</h2>
  <p>We have written about decision windows on nearly every platform page here, always as a risk. The window is short, the default is a forced sale at a price the platform sets, and the user who goes to bed loses the choice. Poke-Collect is the first exception we have found, and it is worth being precise about why it matters.</p>

  <div class="table-wrap">
  <table>
  <caption>What happens when the window closes, across the twenty-four platforms we track.</caption>
  <thead><tr><th scope="col">Platform</th><th scope="col">Window</th><th scope="col">What happens at the end</th></tr></thead>
  <tbody>
    <tr><td class="name">Pickem</td><td><strong class="neg">3 hours</strong></td><td>Card sold at Pickem's FMV</td></tr>
    <tr><td class="name">Packed</td><td><strong class="neg">1 day</strong></td><td>&ldquo;Automatically returned to Packed&rdquo;</td></tr>
    <tr><td class="name">Chalkboard Pulls</td><td><strong class="neg">24 hours</strong></td><td>Automatic buyback at Chalkboard's FMV</td></tr>
    <tr><td class="name">MintPull</td><td>7 days</td><td>Auto-returned at the Company's discretion</td></tr>
    <tr><td class="name">Crown Rips</td><td>7 days, reportedly</td><td>Auto-sold at market value</td></tr>
    <tr><td class="name">Courtyard, Arena Club, Fanatics, Tilt Rips</td><td>Indefinite</td><td>Vaulted, nothing happens</td></tr>
    <tr><td class="name"><strong>Poke-Collect</strong></td><td><strong class="pos">1 year</strong></td><td><strong class="pos">Card shipped to you automatically, free</strong></td></tr>
  </tbody>
  </table>
  </div>

  <p>Read the last row against the first three. On Pickem, Packed and Chalkboard, the platform ends the year owning the card and you holding a balance. On Poke-Collect, you end the year holding the card. Those are opposite businesses wearing similar interfaces.</p>

  <p>The reason is structural rather than generous. Poke-Collect is a card shop that sells digital packs. The others are platforms built around buying cards back, and a platform that reliably buys cards back cannot afford to hold inventory indefinitely &mdash; which is exactly the point we made on the <a href="/platforms/pickem/">Pickem</a> and <a href="/platforms/chalkboard/">Chalkboard</a> pages. The clock is how a buyback business manages its float. Poke-Collect has no buyback business to manage.</p>

  <h2>What you give up: there is no instant sell-back</h2>
  <p>This is the other half of the trade, and it is a real cost. On every other platform here, a card you do not want converts to a balance in one tap. On Poke-Collect there is no such button on the pack.</p>

  <p>What exists instead is a conventional retail buylist &mdash; &ldquo;Scan &amp; Sell (Beta),&rdquo; offering &ldquo;Instant Offers,&rdquo; paid in &ldquo;Store Credit or PayPal,&rdquo; with cards &ldquo;Reviewed Within 24 Hours.&rdquo; That is a human-reviewed purchase of a physical card, not an algorithmic instant offer against a vault position. No percentage of value is published anywhere.</p>

  <div class="table-wrap">
  <table class="plain">
  <caption>Liquidity, compared.</caption>
  <tbody>
    <tr><th scope="row">Chalkboard Pulls</th><td>100% of FMV, instant, withdrawable &mdash; on a value the terms call non-appealable</td></tr>
    <tr><th scope="row">Packed</th><td>100% of FMV, instant, withdrawable &mdash; within a one-day window</td></tr>
    <tr><th scope="row">Arena Club, Tilt Rips, Pickem</th><td>90%, instant, withdrawable</td></tr>
    <tr><th scope="row">Packz, Fanatics, Fast Rips, MintPull</th><td>Instant, but the proceeds cannot leave the platform</td></tr>
    <tr><th scope="row"><strong>Poke-Collect</strong></th><td><strong>No instant offer. A separate buylist, reviewed within 24 hours, paying store credit or PayPal, at an unpublished rate</strong></td></tr>
  </tbody>
  </table>
  </div>

  <p>Which of those is better depends entirely on what you are doing. If you are ripping to flip &mdash; buying packs intending to sell every card straight back &mdash; Poke-Collect is the worst platform here, because the thing you need does not exist as a product. If you are ripping to collect, it is the only one that does not quietly push you toward selling.</p>

  <p>That distinction runs through this whole site. A 100% buyback is a feature for a flipper and an irrelevance for a collector, and the platforms with the most generous buybacks are also the ones with the least patience for anyone who wants to keep what they pulled.</p>

  <h2>Odds: published, but we have not collected them</h2>
  <p>The pack pages link to a pool page that lists the cards and, in the site's own words, shows &ldquo;each tier's chance per pack&rdquo; across four tiers &mdash; Poke, Great, Ultra and Master. The product pages describe these as &ldquo;live odds.&rdquo;</p>

  <p>That is a real disclosure and it puts Poke-Collect ahead of <a href="/platforms/tilt-rips/">Tilt Rips</a>, <a href="/platforms/fast-rips/">Fast Rips</a>, <a href="/platforms/mintpull/">MintPull</a>, <a href="/platforms/packed/">Packed</a>, <a href="/platforms/pickem/">Pickem</a> and <a href="/platforms/chalkboard/">Chalkboard</a>, none of which publish a number on the open web. We have not been able to read it: the pool loads in the browser rather than in the page source, so our collection tooling sees only &ldquo;Loading the pool&hellip;&rdquo;</p>

  <p><strong>That is our limitation, not their failure, and we say so rather than writing &ldquo;no odds published.&rdquo;</strong> If the pool also lists the individual cards, this becomes one of the few platforms where a genuine expected value can be calculated from public information &mdash; tier probabilities plus a card list plus market prices. Collecting it is on our list.</p>

  <h2>The packs</h2>
  <div class="table-wrap">
  <table>
  <caption>Poke-Collect digital mystery packs, {collected}.</caption>
  <thead><tr><th scope="col">Pack</th><th scope="col" class="num">Price</th><th scope="col">What you get</th></tr></thead>
  <tbody>
    <tr><td class="name">Mystery Pack</td><td class="num">$9.99</td><td>One card from the Poke, Great, Ultra or Master tiers</td></tr>
    <tr><td class="name">Japanese Edition</td><td class="num">$9.99</td><td>One card from the Japanese pool</td></tr>
    <tr><td class="name">Booster Edition</td><td class="num">$12.99</td><td>Five cards, revealed one at a time, best card last</td></tr>
    <tr><td class="name">Gold Edition</td><td class="num">$38.99</td><td>One high-end Near Mint English or Japanese single</td></tr>
  </tbody>
  </table>
  </div>

  <p>Note the ceiling. The most expensive pack here is $38.99. Tilt Rips runs to $3,000, Arena Club to $5,000, Clutch Packs and Fanatics to $2,500. A platform whose largest pack is under $40 is a materially different risk proposition from one that will sell you a $5,000 pack, and that is worth as much as any clause in the terms.</p>

  <h2>Terms worth knowing</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>Poke-Collect, a retail card shop at 181 Hughes Road, Suite 5, Madison, AL 35758, with posted store hours</td></tr>
    <tr><th scope="row">Other lines</th><td>Sealed product, singles, graded cards, a buylist, a player-to-player Vault Market, and live breaks on Whatnot</td></tr>
    <tr><th scope="row">Draw timing</th><td>The card is &ldquo;picked the moment your payment clears&rdquo;</td></tr>
    <tr><th scope="row">Unopened packs</th><td>Open automatically one day after purchase</td></tr>
    <tr><th scope="row">Vault</th><td>Up to one year, then <strong class="pos">shipped to you automatically, free</strong></td></tr>
    <tr><th scope="row">Shipping</th><td>$5 flat for the whole vault; free on 25+ cards; free local pickup; US addresses only; sleeved and top-loaded</td></tr>
    <tr><th scope="row">Sell-back</th><td>No instant pack buyback. Separate buylist pays store credit or PayPal, reviewed within 24 hours, rate not published</td></tr>
    <tr><th scope="row">Refunds</th><td>&ldquo;All sales final&rdquo; &mdash; packs cannot be cancelled, returned or exchanged</td></tr>
    <tr><th scope="row">Odds</th><td>Per-tier chances published on the pool page; render in-browser, not yet collected by us</td></tr>
    <tr><th scope="row">Age</th><td>None stated</td></tr>
    <tr><th scope="row">States</th><td>None stated, beyond US-only shipping</td></tr>
  </tbody>
  </table>
  </div>

  <h2>Where we would push back</h2>
  <p>Two things are missing that every platform in this category should publish, and the fact that Poke-Collect is a real shop does not excuse them.</p>
  <ul>
    <li><strong>No stated age restriction.</strong> Eleven of the twenty-four platforms we track require 18+ in their terms. A randomised paid pack sold to anyone of any age is the single most common criticism made of this whole category, and it is the easiest to fix.</li>
    <li><strong>No published buylist rate.</strong> &ldquo;Instant Offers&rdquo; with no percentage and a 24-hour review is less transparent than the 90% figures elsewhere, even though those figures turn out to mean <a href="/guides/buyback-rates/">six different things</a>. A number you can check beats a number you cannot see.</li>
  </ul>
  <p>Neither is a term that works against the buyer in the way a $250 weekly withdrawal cap does. They are gaps, and they are worth closing.</p>

  <div class="callout">
    <h3>Why this page has no rating</h3>
    <p>The odds are published but we have not collected them, so no expected value can be calculated yet &mdash; and unlike most platforms here, that is a gap we can actually close. There is also no buyback rate to score, because there is no pack buyback. We will update this page once the pool data is collected.</p>
    <p>If you have opened Poke-Collect packs and can screenshot the pool page with its tier percentages and card list, that is the single most useful thing anyone could send us right now.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/guides/buyback-rates/">What a buyback is actually worth, across every platform</a></li>
    <li><a href="/platforms/chalkboard/">Chalkboard Pulls, the opposite trade: 100% instant, 24-hour clock</a></li>
    <li><a href="/platforms/packz/">Packz, the other Pok&eacute;mon-heavy platform, with full published odds</a></li>
    <li><a href="/platforms/">All twenty-four platforms compared</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html,
           **{"flags_poke_collect": flag_row("poke-collect")})

    return pages_written("/platforms/poke-collect/", page(
        "/platforms/poke-collect/",
        "Poke-Collect review — the one platform that ships you the card by default",
        "Poke-Collect vaults cards for a year then ships them to you free, where every other platform auto-sells. The trade is that it has no instant buyback at all.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"),
                (None, "Poke-Collect")],
        updated=UPDATED, structured=faq_ld))


def build_letsgo():
    faq_html, faq_ld = faq_block([
        ("Does LETSGO buy cards back at 90%?",
         "<p>Its two public descriptions do not agree. The letsgooo.com homepage says &ldquo;Sell at 90% of fair market value.&rdquo; The App Store listing for the same product says LETSGO &ldquo;buys back cards at <strong>up to</strong> 90% of fair market value, paid to PayPal, Venmo, debit card or bank transfer,&rdquo; and repeats &ldquo;up to 90%&rdquo; a second time. Those are materially different promises: a flat 90% is a rate, and &ldquo;up to 90%&rdquo; is a ceiling with no floor. Nothing we could reach states which one governs, or what the floor is.</p>"),
        ("Who operates LETSGO?",
         "<p>The website does not say. There is no company name, no registered address and no country anywhere on letsgooo.com &mdash; only &ldquo;&copy; 2026 LETSGO&rdquo; and an info@ email. The privacy policy names no legal entity either. The operator appears only in the app store records: the seller is <strong>LETSGO INTERACTIVE LTD</strong>, and the Google Play developer record gives the address as &ldquo;5 Hatidhar RAANANA, 4366507 Israel.&rdquo; Every other platform we track names its operating company somewhere on its own site.</p>"),
        ("Is LETSGO legal where I live?",
         "<p>LETSGO does not say it is. Its own homepage carries the sentence &ldquo;The LETSGO platform may be illegal in the jurisdiction in which you are located.&rdquo; No platform we track makes a blunter statement about itself, and none publishes a list of states where it does or does not operate. We have no state-by-state restrictions to report for LETSGO because none are published. Our <a href=\"/legal/\">by-state page</a> covers what the other platforms disclose.</p>"),
        ("Does LETSGO publish pack odds?",
         "<p>In the app only. The homepage says &ldquo;Grails and odds shown before you rip,&rdquo; the Google Play listing claims &ldquo;transparent odds and real pricing,&rdquo; and a version 1.8.2 release note mentions a &ldquo;clearer odds display.&rdquo; No figures appear on any public page, and no pack prices do either, so no expected value can be calculated from outside the app. One App Store reviewer reports opening 100+ packs with pull rates &ldquo;in line with the stated odds,&rdquo; while also saying they could not find an expected value per pack.</p>"),
        ("How long does LETSGO take to ship a card?",
         "<p>A developer reply on the App Store listing says shipping &ldquo;can take up to 21 business days,&rdquo; which is about a month of calendar time and the longest figure we have seen in this category. Version 1.1.4 added an identity verification step before cards ship. Several recent user reviews on both stores report orders stuck in preparation or unfulfilled; those are unverified user claims and we repeat them as claims, not findings.</p>"),
        ("How big is LETSGO?",
         "<p>Larger than most of the platforms on this site. The Google Play listing shows 100,000+ installs and about 1,050 reviews averaging 4.4; the App Store listing shows 4.0 from 8 ratings. Scale is not an endorsement &mdash; it means more people are exposed to the disclosure gaps below, not fewer.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>LETSGO: the same buyback described two different ways</h1>
    <p class="lede">The website says 90% of fair market value. The App Store listing says &ldquo;up to 90%.&rdquo; The site names no operating company at all &mdash; and its own homepage says the platform may be illegal where you are.</p>
    {flags_letsgo}
  </div>

  <div class="finding">
    <p class="big">letsgooo.com: &ldquo;Sell at 90% of fair market value.&rdquo; The App Store listing for the same app: LETSGO &ldquo;buys back cards at <em>up to</em> 90% of fair market value.&rdquo; A rate and a ceiling are not the same promise, and no floor is published anywhere. Separately, the homepage states: &ldquo;The LETSGO platform may be illegal in the jurisdiction in which you are located.&rdquo;</p>
    <p class="small muted">Read from letsgooo.com, its privacy policy, and the App Store and Google Play listings on {collected}. We could not reach a terms of use document at any URL we tried.</p>
  </div>

  <h2>&ldquo;90%&rdquo; against &ldquo;up to 90%&rdquo;</h2>
  <p>We have written this page before, about <a href="/platforms/fast-rips/">Fast Rips</a>, where the homepage advertised cash and the terms described non-withdrawable credit. This is a smaller gap and the same species of problem: two official descriptions of one product that a buyer cannot reconcile.</p>

  <div class="table-wrap">
  <table>
  <caption>LETSGO's buyback, as described in each place it is described, {collected}.</caption>
  <thead><tr><th scope="col">Source</th><th scope="col">Wording</th><th scope="col">What it promises</th></tr></thead>
  <tbody>
    <tr><td class="name">letsgooo.com</td><td>&ldquo;Sell at 90% of fair market value&rdquo;</td><td>A rate. Every card returns 90%</td></tr>
    <tr><td class="name">App Store listing</td><td>&ldquo;buys back cards at <strong>up to</strong> 90% of fair market value&rdquo;</td><td>A ceiling. 90% is the best case; the floor is unstated</td></tr>
    <tr><td class="name">Google Play listing</td><td>&ldquo;instant buyback&rdquo; at &ldquo;fair market value&rdquo;</td><td>No percentage at all</td></tr>
    <tr><td class="name">Terms of use</td><td>&mdash;</td><td>We could not reach one</td></tr>
  </tbody>
  </table>
  </div>

  <p>This matters more than the five-point spreads we normally write about. Across the platforms we track, the difference between the best and worst advertised 90% works out to a few dollars per hundred of card value. The difference between &ldquo;90%&rdquo; and &ldquo;up to 90%&rdquo; is unbounded, because the second phrase sets no floor. A buyback that returns 90% on one card and 40% on the next is fully consistent with &ldquo;up to 90%.&rdquo;</p>

  <p>We are not alleging that LETSGO pays less than 90%. Several app reviews describe buybacks working. We are saying that the company has published two different promises and a buyer has no way to know which is the real one &mdash; and that the one place this would normally be settled, a terms of use document, is the one place we could not find.</p>

  <h2>The operator is not named on its own site</h2>
  <p>This is the part we would want to know before depositing anything.</p>

  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">letsgooo.com</th><td>No company name, no registered address, no country. &ldquo;&copy; 2026 LETSGO&rdquo; and info@letsgooo.com</td></tr>
    <tr><th scope="row">Privacy policy</th><td>Names &ldquo;LETSGO and its affiliated companies&rdquo; as the Company. No legal entity, no address, no country, no governing law. Header dated August 11, 2026; footer says September 2026</td></tr>
    <tr><th scope="row">App Store</th><td>Seller: <strong>LETSGO INTERACTIVE LTD</strong></td></tr>
    <tr><th scope="row">Google Play</th><td>Developer: LETSGO INTERACTIVE LTD &mdash; &ldquo;5 Hatidhar RAANANA, 4366507 Israel&rdquo;</td></tr>
  </tbody>
  </table>
  </div>

  <p>So the operator is identifiable, but only from Apple's and Google's records, which those companies require and LETSGO does not volunteer. That makes it the second non-US operator we have covered, after <a href="/platforms/mintpull/">MintPull</a> in Hong Kong &mdash; and unlike MintPull, which names its entity, its address and its governing law in its own terms, LETSGO discloses none of that itself.</p>

  <p>Being incorporated outside the United States is not wrongdoing, and plenty of good products are built abroad. It is a material fact about who holds your money and which courts would hear a dispute, and a platform selling to US buyers should state it on its own website rather than leaving it to an app store form. We could not find a governing-law clause at all, which means we cannot tell you where a dispute would be heard.</p>

  <h2>The sentence on their own homepage</h2>
  <div class="callout danger">
    <h3>&ldquo;The LETSGO platform may be illegal in the jurisdiction in which you are located.&rdquo;</h3>
    <p>That is quoted from letsgooo.com, not from a critic. No other platform we track says this about itself. <a href="/platforms/pickem/">Pickem</a> publishes a list of five states it excludes; <a href="/platforms/mintpull/">MintPull</a> names Nevada; several others say nothing. LETSGO neither excludes states nor claims legality &mdash; it puts the question back on the buyer and moves on.</p>
    <p>We read it as honest rather than sinister: the legal position of paid randomised packs is genuinely unsettled, which is the subject of our <a href="/is-card-ripping-gambling/">is card ripping gambling</a> page. But a warning with no list attached gives a buyer nothing to act on.</p>
  </div>

  <h2>What it does well</h2>
  <p>Two things here are at the better end of the category, and both are real.</p>
  <ul>
    <li><strong>The cash-out methods are specific.</strong> &ldquo;Paid to PayPal, Venmo, debit card or bank transfer&rdquo; is a concrete list, and only <a href="/platforms/packed/">Packed</a> matches it for breadth. Four of the twenty-four platforms we track pay credit that cannot be withdrawn at all; this is not one of them.</li>
    <li><strong>Cards are real and the grading is named.</strong> The listings describe professionally graded slabs from PSA, BGS or CGC with the grade and certification number shown, and state that nothing is simulated. A certification number is checkable against the grader's own database, which is a verification route most platforms here do not offer.</li>
  </ul>

  <h2>Shipping is slow, and reviews say so</h2>
  <p>A developer reply on the App Store says shipping &ldquo;can take up to 21 business days&rdquo; &mdash; roughly a month. Version 1.1.4 added identity verification before cards ship, which adds time at the front. For comparison, <a href="/platforms/poke-collect/">Poke-Collect</a> ships a whole vault for $5 flat and <a href="/platforms/arena-club/">Arena Club</a> and Fanatics vault indefinitely.</p>

  <p>Recent reviews on both stores report orders stuck in preparation and at least one unfulfilled refund. Those are unverified claims from individual users and we treat them as claims. We mention them because the 21-business-day figure is the company's own, and the complaints are consistent with it rather than contradicting it.</p>

  <p>One reviewer also states the app &ldquo;forces you to auto-sell if you hold it in your collection past 3 days,&rdquo; which would contradict the homepage's &ldquo;free vault storage&rdquo; with no stated limit. We could not confirm it either way, and we are not publishing it as a finding &mdash; it is on our open questions list.</p>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>LETSGO INTERACTIVE LTD, &ldquo;5 Hatidhar RAANANA, 4366507 Israel&rdquo; per Google Play; not named on its own site</td></tr>
    <tr><th scope="row">Categories</th><td>Pok&eacute;mon, NBA, MLB, NFL, One Piece TCG</td></tr>
    <tr><th scope="row">Cards</th><td>Physical cards and graded slabs from PSA, BGS or CGC, with grade and certification number shown</td></tr>
    <tr><th scope="row">Pack prices</th><td>Not published anywhere public</td></tr>
    <tr><th scope="row">Odds</th><td>Shown in-app before a rip; nothing published on the web</td></tr>
    <tr><th scope="row">Buyback</th><td>&ldquo;90%&rdquo; on the website, &ldquo;up to 90%&rdquo; on the App Store; no floor published</td></tr>
    <tr><th scope="row">Payouts</th><td>PayPal, Venmo, debit card or bank transfer</td></tr>
    <tr><th scope="row">Who sets the value</th><td>Not stated on the website, the app listings, or any document we could reach</td></tr>
    <tr><th scope="row">Vault</th><td>&ldquo;Climate-controlled, insured storage,&rdquo; free, no time limit stated</td></tr>
    <tr><th scope="row">Shipping</th><td>&ldquo;Insured, tracked to your door&rdquo;; up to 21 business days per a developer reply; identity verification required</td></tr>
    <tr><th scope="row">Promotions</th><td>A free pack via an invite link; conditions not clearly stated, and whether free-pack proceeds are withdrawable is not confirmed</td></tr>
    <tr><th scope="row">Scale</th><td>100,000+ Google Play installs; ~1,050 Play reviews at 4.4; 8 App Store ratings at 4.0</td></tr>
    <tr><th scope="row">Age</th><td>18+ on the site and both store listings</td></tr>
    <tr><th scope="row">States</th><td>None published. The homepage says the platform &ldquo;may be illegal in the jurisdiction in which you are located&rdquo;</td></tr>
    <tr><th scope="row">Governing law</th><td>Not found</td></tr>
  </tbody>
  </table>
  </div>

  <div class="callout">
    <h3>If you use LETSGO</h3>
    <p>Screenshot the buyback offer before accepting it, and keep the certification number on any graded slab &mdash; it is checkable against PSA, BGS or CGC directly, which is the one claim here you can verify yourself without trusting the platform. Ask support in writing whether the buyback is 90% or &ldquo;up to 90%,&rdquo; and what the floor is. Verify your identity before you want anything shipped, and expect the better part of a month.</p>
    <p>If this has stopped feeling like fun, free and confidential help is available: call or text <strong>1-800-GAMBLER</strong>.</p>
  </div>

  <div class="callout">
    <h3>Why this page has no rating</h3>
    <p>No pack prices and no odds are published outside the app, so no expected value can be calculated. The buyback rate is stated two different ways and we cannot tell which governs. No terms of use document was reachable, so storage limits, withdrawal caps, valuation methodology and governing law are all unknown. Four of our five scoring inputs are unavailable. <a href="/methodology/">Our methodology</a> explains why we leave a cell empty rather than guess.</p>
    <p>We have written to LETSGO asking which buyback figure is correct and where the terms of use can be read, and will update this page with any response. If you have in-app screenshots of pack odds, prices, or the terms, we would like to see them.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/platforms/fast-rips/">Fast Rips, where the marketing and the terms disagree more sharply</a></li>
    <li><a href="/guides/buyback-rates/">What a 90% buyback actually pays, across every platform</a></li>
    <li><a href="/guides/withdrawals/">Who pays real money and who pays credit</a></li>
    <li><a href="/platforms/">All twenty-four platforms compared</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html,
           **{"flags_letsgo": flag_row("letsgo")})

    return pages_written("/platforms/letsgo/", page(
        "/platforms/letsgo/",
        "LETSGO review — is the buyback 90% or “up to 90%”?",
        "LETSGO's website says it buys cards back at 90% of fair market value. Its App Store listing says “up to 90%.” The site names no operating company, and warns the platform may be illegal where you are.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "LETSGO")],
        updated=UPDATED, structured=faq_ld))


def build_lastpack():
    rows = lastpack_rows()
    s = lastpack_stats()

    def band_table(r):
        body = "".join(
            '<tr><td class="name">%s</td><td class="num">%s&ndash;%s</td>'
            '<td class="num">%s</td><td class="num">%s</td></tr>'
            % (lab, money(lo), money(hi), pct(q, 1),
               money((lo + hi) / 2.0 * q / 100.0))
            for lab, lo, hi, q in r["bands"])
        return (
            '<div class="table-wrap"><table>'
            '<caption>%s (%s), %s, %s volatility &mdash; LastPack&rsquo;s '
            'published rarity table, collected %s. The last column is each '
            'band&rsquo;s contribution to the midpoint expected value.</caption>'
            '<thead><tr><th scope="col">Rarity</th>'
            '<th scope="col" class="num">Value range</th>'
            '<th scope="col" class="num">Chance</th>'
            '<th scope="col" class="num">Contributes</th></tr></thead>'
            '<tbody>%s</tbody>'
            '<tfoot><tr><th scope="row">Total</th><td class="num">&mdash;</td>'
            '<td class="num">%s</td><td class="num"><strong>%s</strong></td>'
            '</tr></tfoot></table></div>'
            % (r["name"], r["collection"], money(r["price"]), r["vol"],
               UPDATED, body, pct(r["psum"], 1), money(r["mid"])))

    cmp_rows = "".join(
        '<tr><td class="name">%s</td><td class="num">%s</td>'
        '<td class="num">%s</td><td class="num"><strong>%s</strong></td>'
        '<td class="num">%s</td><td class="num">%s</td>'
        '<td class="num">%s</td></tr>'
        % (r["name"], r["vol"], money(r["price"]),
           pct(r["posted_ratio"] * 100, 0), pct(r["ratio_mid"] * 100, 0),
           pct(r["ratio_topfloor"] * 100, 0), pct(r["psum"], 1))
        for r in rows)

    faq_html, faq_ld = faq_block([
        ("Does LastPack pay cash for a sell-back?",
         "<p>Its FAQ and its terms disagree, and this is the thing to resolve before depositing. The FAQ says &ldquo;current user-initiated sellback is 100% of fair market value, credited to your Lastpack balance,&rdquo; and describes real cash-outs through Coinflow or USDC on Solana. But &sect;4.5 of the Terms says that on selling back, your account is credited &ldquo;in the form of additional pack purchase credits.&rdquo; Pack credit is not money. &sect;5.3 then contradicts &sect;4.5 by making &ldquo;Eligible Sale Proceeds&rdquo; cashable. Two of the three say cash; one says credit.</p>"),
        ("How long can you keep a card on LastPack?",
         "<p>Five days. &sect;4.3 states, in capitals, &ldquo;YOU MAY ONLY STORE A COLLECTIBLE FOR A MAXIMUM OF FIVE (5) DAYS FROM THE DATE OF PURCHASE. THIS IS A STRICT DEADLINE &mdash; PLAN ACCORDINGLY.&rdquo; After that it is automatically sold back and your account credited the FMV <em>as determined at the time of your purchase</em> &mdash; not today's value. LastPack may text you and may extend the deadline at its discretion.</p>"),
        ("What does LastPack show before you buy?",
         "<p>More than most platforms show anywhere. Every pack page carries the sell-back rate, the minimum and maximum value in the pack, a &ldquo;GROSS EV&rdquo; percentage, a full rarity table with value ranges and percentages, the top grails, and a live feed of recent pulls. A volatility selector &mdash; Steady, Balanced or Wild &mdash; changes the distribution. On both packs we collected, the rarity percentages summed to exactly 100.0%.</p>"),
        ("Can you verify a LastPack pull was fair?",
         "<p>LastPack says yes, and describes a commit-reveal scheme in plain language: your fairness page shows an &ldquo;envelope fingerprint&rdquo; and your current pull number before you open, your receipt shows the ones actually used, and after opening you can tap verify to recompute the result step by step. If that works as described it is the most user-checkable fairness claim in this category, alongside <a href=\"/platforms/clutch-packs/\">Clutch Packs</a>. We have not run a verification ourselves.</p>"),
        ("Who operates LastPack?",
         "<p>Lotus Digital Inc., a Delaware corporation, under California law. Disputes go to JAMS arbitration in San Jose with a class-action waiver, a jury waiver and a 30-day opt-out. You must be 18, hold a personal US telephone number and a government ID, and pass KYC including a live selfie before adding funds, purchasing, shipping or cashing out. One account per person.</p>"),
        ("What does LastPack cost to ship?",
         "<p>Per card, and &sect;4.6 is explicit that &ldquo;the Company does not offer combined inventory shipments, and each individual collectible must be shipped separately.&rdquo; On low-value pulls that will often cost more than the card. Insurance may be required above $100 and is offered without markup. Shipments go from California, with tracked international services available and duties payable by the recipient.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>LastPack shows you almost everything &mdash; on a contract that contradicts its own help centre</h1>
    <p class="lede">Sell-back rate, min and max value, a posted EV and a full rarity table on every pack, plus a per-pull fairness check. Then &sect;4.5 says your sell-back is pack credit while the FAQ says it is cash.</p>
    {flags_lastpack}
  </div>

  <div class="finding">
    <p class="big">The FAQ: sell-back is &ldquo;100% of fair market value, credited to your Lastpack balance,&rdquo; cashable through Coinflow or USDC on Solana. &sect;4.5 of the Terms: the credit is &ldquo;in the form of <strong>additional pack purchase credits</strong>.&rdquo; &sect;5.3 then makes sale proceeds cashable after all. Separately, &sect;4.3 caps storage at <strong>five days</strong>, after which the card is auto-sold at the FMV fixed when you bought it.</p>
    <p class="small muted">Collected from the live lastpack.com pack builder, its help centre and its Terms of Service (updated 16 October 2026) on {collected}.</p>
  </div>

  <h2>The pack page is the best in the category</h2>
  <p>Before you spend anything, a LastPack pack page shows the price, the sell-back rate, the minimum and maximum value in the pool, a GROSS EV percentage, every rarity band with its value range and probability, the top grails, and a live feed of what other people just pulled. A volatility selector lets you choose Steady, Balanced or Wild.</p>

  {band_a}

  <p>The percentages sum to exactly 100.0%, as they did on both packs we collected. Compare <a href="/platforms/swishx/">SwishX</a> at 100.04&ndash;100.64% and <a href="/platforms/catchback/">CatchBack</a>, which publishes a comparable table but no sell-back rate alongside it.</p>

  <h2>A volatility dial that does not move the expected value</h2>
  <p>We collected one pack at Balanced and one at Steady, in different collections. Both posted <strong>GROSS EV: 95%</strong>.</p>

  <div class="table-wrap">
  <table>
  <caption>LastPack packs collected {collected}: the posted GROSS EV against what the published bands imply.</caption>
  <thead><tr>
    <th scope="col">Pack</th><th scope="col">Volatility</th>
    <th scope="col" class="num">Price</th>
    <th scope="col" class="num">Posted GROSS EV</th>
    <th scope="col" class="num">Bands at midpoint</th>
    <th scope="col" class="num">Top band at floor</th>
    <th scope="col" class="num">Odds sum</th>
  </tr></thead>
  <tbody>{cmps}</tbody>
  </table>
  </div>

  <p>Two things follow. First, <strong>95% looks like a design target rather than a per-pack measurement</strong> &mdash; the same figure on two different collections at two different volatility settings. That is the same architecture as <a href="/platforms/swishx/">SwishX</a>, which says its packs are built to a 100% value target, and <a href="/platforms/gotya/">Gotya</a>, which says expected value equals price. LastPack just sets the dial five points lower, and a pack built to 95% is an ordinary, honest piece of retail design.</p>

  <p>Second, the posted figure is <em>below</em> what its own bands imply. At midpoints the bands work out to {midavg}; valuing the top band at its floor still gives {floorv}. That is the opposite direction from <a href="/platforms/catchback/">CatchBack</a>, whose posted EV sat above its bands.</p>

  <div class="callout">
    <h3>Why our number is the unreliable one here</h3>
    <p>The Grail band is the problem, as it has been on every platform publishing ranges. On the Pok&eacute;mon Noobie pack it runs $8 to $500 &mdash; <strong>{widest} times wide</strong> &mdash; and fires on 0.1% of pulls. Taking its midpoint assumes the average grail is worth $254, which is almost certainly wrong.</p>
    <p>LastPack's own terms warn about exactly this, in capitals: &ldquo;THE DISTRIBUTION BETWEEN RANGES MAY NOT (AND IS LIKELY NOT TO BE) EQUAL.&rdquo; We think the posted 95% is likelier to be right than our midpoint estimate. We publish both because the gap is the honest description of what can be known from the outside.</p>
  </div>

  {band_b}

  <h2>The clause that contradicts the help centre</h2>
  <p>LastPack's sell-back is 100% of fair market value, displayed on the pack page next to the odds. That is the headline rate in this category, and the FAQ pairs it with a real cash-out: Coinflow for fiat, USDC on Solana through the website, two-factor required, with a cap of &ldquo;no more than $10,000 in Eligible Sale Proceeds during any single period of seven (7) consecutive days&rdquo; (&sect;5.3a).</p>

  <p>Then &sect;4.5:</p>

  <blockquote>
    <p>&ldquo;Upon selling back to lastpack your lastpack Account will be credited the FMV of the collectible such credit to be in the form of <strong>additional pack purchase credits</strong>.&rdquo;</p>
  </blockquote>

  <p>Pack purchase credit is not money, and &sect;5.2 is clear that &ldquo;Purchase Funds are non-transferable and may not be cashed out, withdrawn, or redeemed for cash.&rdquo; If &sect;4.5 governs, the 100% never becomes cash. If &sect;5.3 governs &mdash; it defines &ldquo;Eligible Sale Proceeds&rdquo; as amounts owed after LastPack buys an item from you, and makes those cashable &mdash; it does.</p>

  <p><strong>We think &sect;5.3 and the FAQ describe the live product and &sect;4.5 is stale drafting.</strong> There is a specific reason to think so, and it is the most interesting thing on this page.</p>

  <h2>Where that clause came from</h2>
  <p>We have now read this template three times. LastPack's &sect;4.3, &sect;4.4 and &sect;4.5 are the clauses we published from <a href="/platforms/triumph/">Rips by Triumph</a> and <a href="/platforms/mintpull/">MintPull</a> &mdash; the same sentences, shifted up one section number.</p>

  <div class="table-wrap">
  <table class="clauses">
  <caption>The same clauses, across three platforms in three corporate structures.</caption>
  <thead><tr><th scope="col">&nbsp;</th><th scope="col">LastPack</th><th scope="col">Rips by Triumph</th><th scope="col">MintPull</th></tr></thead>
  <tbody>
    <tr><td class="name">Storage cap</td><td>&sect;4.3 &ldquo;MAXIMUM OF FIVE (5) DAYS&rdquo;</td><td>&sect;5.3 &ldquo;MAXIMUM OF SEVEN DAYS&rdquo;</td><td>&sect;5.3 &ldquo;MAXIMUM OF SEVEN DAYS&rdquo;</td></tr>
    <tr><td class="name">Distribution warning</td><td>&sect;4.2 &ldquo;LIKELY NOT TO BE EQUAL&rdquo;</td><td>&sect;5.2 &ldquo;LIKELY NOT TO BE EQUAL&rdquo;</td><td>&sect;5.2 &ldquo;LIKELY IS NOT BE EQUAL&rdquo;</td></tr>
    <tr><td class="name">FMV disclaimer</td><td>&sect;4.4 &ldquo;may not match published market values&rdquo;</td><td>&sect;5.4 &ldquo;may not match published market values&rdquo;</td><td>&ldquo;may not match published market values&rdquo;</td></tr>
    <tr><td class="name">Sell-back form</td><td>&sect;4.5 &ldquo;additional pack purchase credits&rdquo;</td><td>&sect;5.5 Returns final, no obligation to offer</td><td>&sect;5.5 &ldquo;additional pack purchase credits&rdquo;</td></tr>
    <tr><td class="name">Operator</td><td>Lotus Digital Inc. (Delaware)</td><td>Triumph TCG, LLC (Delaware law)</td><td>Arcane Answers Studio Ltd (Hong Kong)</td></tr>
  </tbody>
  </table>
  </div>

  <p>MintPull pays pack credit and the clause describes it accurately. LastPack appears to have built a genuinely better product &mdash; real cash-out, a 100% rate, provable fairness &mdash; on top of a document that still says pack credit, and added &sect;5.3 to describe what it actually does without deleting the clause it contradicts.</p>

  <p>That is the practical cost of the shared template we first wrote about on the <a href="/platforms/triumph/">Triumph page</a>. It is not only that operator-favourable clauses spread. It is that a platform doing the right thing inherits a contract that says otherwise, and the buyer cannot tell which document governs.</p>

  <h2>Five days, at the price from five days ago</h2>
  <div class="callout danger">
    <h3>&sect;4.3, in capitals</h3>
    <p>&ldquo;YOU MAY ONLY STORE A COLLECTIBLE FOR A MAXIMUM OF FIVE (5) DAYS FROM THE DATE OF PURCHASE. THIS IS A STRICT DEADLINE &mdash; PLAN ACCORDINGLY.&rdquo;</p>
    <p>After five days the card is sold back automatically and you are credited &ldquo;the FMV as determined at the time of your purchase.&rdquo; Not today's value &mdash; the value fixed when you bought. On a card that has appreciated in those five days, the difference is theirs. LastPack may text you first and may extend the deadline at its discretion.</p>
  </div>

  <p>Five days is tighter than Triumph's and MintPull's seven, and the shortest storage cap we have found on this template. It is still far more generous than <a href="/platforms/pickem/">Pickem's three hours</a>.</p>

  <h2>What it does well</h2>
  <ul>
    <li><strong>Provable fairness you can actually check.</strong> An envelope fingerprint and pull number shown before you open, a receipt showing the ones used, and a verify button that recomputes the result step by step. <a href="/platforms/rip-station/">Rip Station</a> explicitly disclaims this; LastPack describes a working commit-reveal scheme in plain English.</li>
    <li><strong>It says packs lose money.</strong> &sect;1: &ldquo;Items may be worth less than the Pack price. Do not treat Packs as an investment.&rdquo; The FAQ repeats it. That is <a href="/platforms/holofoil/">Holofoil</a>-level candour.</li>
    <li><strong>It disowns its own animations.</strong> &sect;4.9 says the spinning wheel and reveal effects are &ldquo;entertainment only&rdquo; and do not affect the outcome, odds, FMV or buyback. No other platform we track bothers to say this, and it is the single most common misconception about these products.</li>
    <li><strong>If an item is missing, you get FMV plus 10%</strong> (&sect;4.7). A platform that over-compensates for its own inventory errors is doing something unusual.</li>
    <li><strong>A responsible purchasing policy and self-exclusion</strong>, referenced in the terms and the FAQ. Only <a href="/platforms/mintpull/">MintPull</a> otherwise has one.</li>
  </ul>

  <h2>And what we would push on</h2>
  <ul>
    <li><strong>Fix &sect;4.5.</strong> One sentence currently tells buyers their 100% sell-back is pack credit. If that is not true, deleting it costs nothing and removes the single biggest ambiguity in the product.</li>
    <li><strong>No combined shipments.</strong> &sect;4.6: &ldquo;each individual collectible must be shipped separately.&rdquo; On $1 packs, shipping a handful of cards will cost multiples of what they are worth. <a href="/platforms/poke-collect/">Poke-Collect</a> ships an entire vault for $5 flat.</li>
    <li><strong>Title does not pass until shipment</strong> (&sect;4.2). Compare <a href="/platforms/rare-candy/">Rare Candy</a> and <a href="/platforms/rip-station/">Rip Station</a>, where you hold title to the card in the vault. Here, until it ships, you hold a claim rather than a card.</li>
    <li><strong>The valuation is still theirs.</strong> &sect;4.4: FMV comes from a &ldquo;proprietary system&rdquo; and &ldquo;may not match published market values.&rdquo; Every number on this page rests on it.</li>
  </ul>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>Lotus Digital Inc., a Delaware corporation, trading as lastpack</td></tr>
    <tr><th scope="row">Governing law</th><td>California (&sect;13.6); JAMS arbitration in San Jose, class and jury waivers, 30-day opt-out (&sect;11)</td></tr>
    <tr><th scope="row">Collections</th><td>Pok&eacute;mon, One Piece, Riftbound, Dragon Ball; basketball, football and baseball listed as coming</td></tr>
    <tr><th scope="row">Packs</th><td>Five price points per collection, $1 to $2,500, with a Steady / Balanced / Wild volatility selector</td></tr>
    <tr><th scope="row">Odds</th><td><strong class="pos">Full rarity table per pack with value ranges and percentages</strong>, summing to exactly 100.0% on both packs we collected; change in real time with inventory</td></tr>
    <tr><th scope="row">Posted EV</th><td><strong class="pos">&ldquo;GROSS EV&rdquo; on every pack</strong> &mdash; 95% on both we checked</td></tr>
    <tr><th scope="row">Sell-back</th><td><strong class="pos">100% of FMV</strong>, displayed on the pack page</td></tr>
    <tr><th scope="row">Cash out</th><td>Coinflow for fiat; USDC on Solana via the website; 2FA required; <strong>$10,000 per 7 days</strong> (&sect;5.3a). Deposits are never withdrawable (&sect;5.2)</td></tr>
    <tr><th scope="row">Storage</th><td><strong class="neg">5 days</strong> (&sect;4.3), then auto-sold at the FMV fixed at purchase</td></tr>
    <tr><th scope="row">Fairness</th><td>Commit-reveal with a per-pull verify step and a published guide</td></tr>
    <tr><th scope="row">Shipping</th><td>Per card; <strong>no combined shipments</strong> (&sect;4.6); insurance may be required above $100, offered without markup; ships from California; international available</td></tr>
    <tr><th scope="row">Title</th><td>Does not pass to you until the card is shipped and accepted by the carrier (&sect;4.2)</td></tr>
    <tr><th scope="row">Funding</th><td>Card, Apple Pay, Google Pay, PayPal, Venmo, Cash App, USDC on Solana</td></tr>
    <tr><th scope="row">Age and identity</th><td>18+, one account per person, US phone number, government ID and live selfie KYC</td></tr>
    <tr><th scope="row">Liability cap</th><td>The greater of fees paid or $100 (&sect;9.1)</td></tr>
  </tbody>
  </table>
  </div>

  <div class="callout">
    <h3>Why this page has no rating</h3>
    <p>LastPack discloses enough to rate on odds, and would score near the top. We are not scoring it because the single most important term &mdash; whether a 100% sell-back becomes money or pack credit &mdash; is stated two different ways in the platform's own documents. That is not a detail we can average out. And as everywhere else on this site, nobody has yet tested whether these fair market values match real sold prices.</p>
    <p>We would publish a correction the day &sect;4.5 is updated. If you have cashed out from LastPack, or have a screenshot of a completed Coinflow payout, that settles it.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/platforms/triumph/">Rips by Triumph, where we first found this template</a></li>
    <li><a href="/compare/?p=lastpack,swishx,gotya">Compare LastPack, SwishX and Gotya side by side</a></li>
    <li><a href="/guides/withdrawals/">Which platforms actually pay out money</a></li>
    <li><a href="/calculator/">Run these bands through the pack EV calculator</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html, cmps=cmp_rows,
           band_a=band_table(rows[0]), band_b=band_table(rows[1]),
           midavg=pct(s["mid_avg"] * 100, 0),
           floorv=pct(s["topfloor_avg"] * 100, 0),
           widest="%.0f" % s["max_grail_width"],
           **{"flags_lastpack": flag_row("lastpack")})

    ld = [faq_ld, jsonld({
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "LastPack published pack odds and posted expected values",
        "description": "Published rarity tables, sell-back rates, min and max values and posted GROSS EV for LastPack packs, collected %s, with independent recomputation." % UPDATED,
        "url": BASE_URL + "/platforms/lastpack/",
        "creator": {"@type": "Organization", "name": SITE_NAME},
        "license": "https://creativecommons.org/licenses/by/4.0/",
    })]

    return pages_written("/platforms/lastpack/", page(
        "/platforms/lastpack/",
        "LastPack review — 100% sell-back, and a clause that says otherwise",
        "LastPack posts an EV, full odds and a 100% sell-back on every pack, with a per-pull fairness check. Its §4.5 says that sell-back is pack credit; its FAQ says it is cash.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "LastPack")],
        updated=UPDATED, structured=ld))


def build_underdog():
    faq_html, faq_ld = faq_block([
        ("How long do you have to decide on an Underdog Rips pull?",
         "<p>Three days, per Underdog's own help centre: you have three days from opening to redeem, hold or sell, and after that the card &ldquo;will automatically be bought back.&rdquo; You can choose only one path per card, and once chosen it &ldquo;cannot be reversed.&rdquo; Holding costs nothing during the window. Note that Phygitals, the third party powering the product, documents three different windows depending on card type &mdash; 30 minutes, 3 days or 7 days &mdash; and Underdog's three days matches its sealed-product tier.</p>"),
        ("What does Underdog Rips pay for a card?",
         "<p>Underdog does not say. Its help centre describes selling back &ldquo;at the price offered&rdquo; and states no percentage and no payout form anywhere we could read. Phygitals' own documentation says &ldquo;the standard buyback rate is 85% of FMV,&rdquo; that some packs carry enhanced rates shown as a badge before purchase, and that &ldquo;all buyback payouts are denominated and paid in USDC&rdquo; to a wallet. Whether that is what reaches an Underdog account, or whether Underdog credits its own balance instead, we could not confirm.</p>"),
        ("Who decides what an Underdog Rips card is worth?",
         "<p>Not Underdog, and this is the most interesting thing about the product. Phygitals says fair market value is &ldquo;sourced from industry-standard pricing providers for graded collectibles&rdquo; and fixed at the time of the pull. That makes this one of only two platforms we track that outsources valuation to a third party &mdash; <a href=\"/platforms/fanatics-instant-rips/\">Fanatics</a>, which uses Card Ladder, is the other. The providers are not named here, which is a step short of Fanatics.</p>"),
        ("Does Underdog Rips publish odds?",
         "<p>It says so. Underdog's own announcement describes packs with &ldquo;odds up front,&rdquo; and Phygitals says it displays &ldquo;the odds of winning specific value groups in each pack&rdquo; along with &ldquo;the average expected value (EV) of your play.&rdquo; We could not reach a page showing actual figures, so everything on this page about odds is a claim we have not verified. An EV shown per pack would put it alongside <a href=\"/platforms/courtyard/\">Courtyard</a> and <a href=\"/platforms/swishx/\">SwishX</a> if confirmed.</p>"),
        ("Is Underdog Rips provably fair?",
         "<p>Phygitals says its rarity distributions form part of each opening's provably fair record and publishes separate verification documentation. If that holds up, it is the second platform we track making a cryptographic fairness claim, after <a href=\"/platforms/clutch-packs/\">Clutch Packs</a>. It is also a direct contrast with <a href=\"/platforms/rip-station/\">Rip Station</a>, which states plainly that its published odds are &ldquo;not a cryptographic proof of fairness.&rdquo; We have not run a verification ourselves.</p>"),
        ("Where is Underdog Rips available?",
         "<p>Not everywhere. The terms say Rips are &ldquo;not available in all states&rdquo; and cards ship only to US addresses, but we could not find a published list of which states are included or excluded. Underdog's main fantasy product has its own state-by-state availability that differs by contest type, so do not assume the Rips footprint matches it. Our <a href=\"/legal/\">by-state page</a> records only restrictions we can source.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Underdog Rips: the disclosure lives at the supplier, not the storefront</h1>
    <p class="lede">Underdog&rsquo;s help centre gives you a three-day window and no buyback rate. Phygitals, the third party that sources, vaults and ships every card, documents 85% of FMV in USDC, third-party valuations, provable fairness &mdash; and a buyback window that can be 30 minutes.</p>
    {flags_underdog}
  </div>

  <div class="finding">
    <p class="big">Underdog states no buyback percentage and no payout form anywhere we could read. Phygitals documents &ldquo;the standard buyback rate is 85% of FMV,&rdquo; paid in USDC, with windows of <strong>30 minutes</strong> for standard cards, <strong>3 days</strong> for sealed product and <strong>7 days</strong> for inventory cards &mdash; and once a window closes &ldquo;the offer is permanently removed.&rdquo;</p>
    <p class="small muted">Read from Underdog&rsquo;s help centre and the Phygitals platform documentation on {collected}. We could not reach a page showing actual pack odds or prices; odds claims on this page are unverified.</p>
  </div>

  <h2>Two documents, one product</h2>
  <p>Most platforms on this site are one company making one set of claims. Underdog Rips is a storefront on somebody else&rsquo;s rails, and the two parties document the product very differently.</p>

  <div class="table-wrap">
  <table class="clauses">
  <caption>What each party publishes about the same product, {collected}.</caption>
  <thead><tr><th scope="col">&nbsp;</th><th scope="col">Underdog&rsquo;s help centre</th><th scope="col">Phygitals&rsquo; documentation</th></tr></thead>
  <tbody>
    <tr><td class="name">Buyback rate</td><td>&ldquo;The price offered&rdquo; &mdash; no figure</td><td>&ldquo;The standard buyback rate is <strong>85% of FMV</strong>&rdquo;; enhanced rates badged before purchase</td></tr>
    <tr><td class="name">Payout form</td><td>Not stated</td><td>&ldquo;All buyback payouts are denominated and paid in <strong>USDC</strong>&rdquo;, direct to a wallet</td></tr>
    <tr><td class="name">Window</td><td>3 days, then auto bought back</td><td><strong>30 minutes</strong> standard, 3 days sealed product, 7 days inventory</td></tr>
    <tr><td class="name">Valuation</td><td>Not stated</td><td>&ldquo;Industry-standard pricing providers for graded collectibles&rdquo;, fixed at the pull</td></tr>
    <tr><td class="name">Odds</td><td>&ldquo;Odds up front&rdquo; in the announcement</td><td>&ldquo;The odds of winning specific value groups&rdquo; plus &ldquo;the average expected value (EV) of your play&rdquo;</td></tr>
    <tr><td class="name">Fairness</td><td>Not addressed</td><td>Distributions form part of a provably fair record, with verification documentation</td></tr>
  </tbody>
  </table>
  </div>

  <p>Underdog&rsquo;s three days matches Phygitals&rsquo; sealed-product tier exactly, which suggests Rips runs on that configuration rather than the 30-minute standard one. That is an inference from two documents, not something either party states, and we flag it as such.</p>

  <p>The practical problem is the same either way: <strong>a buyer reading Underdog&rsquo;s own help pages cannot find out what a sell-back pays or in what form.</strong> They have to know Phygitals exists, find its documentation, and then assume it applies.</p>

  <h2>What the supplier does unusually well</h2>
  <p>Set aside where it is published and the Phygitals disclosure is among the better architecture in this category.</p>

  <ul>
    <li><strong>Valuation is outsourced.</strong> FMV comes from &ldquo;industry-standard pricing providers for graded collectibles&rdquo; rather than an in-house estimate. Only <a href="/platforms/fanatics-instant-rips/">Fanatics</a> otherwise does this, and it is the single most important structural fix available in this category &mdash; it removes the conflict where the party paying the buyback also decides what the card is worth. Phygitals does not name the providers, where Fanatics names Card Ladder, so it is a step short.</li>
    <li><strong>An expected value is shown per pack.</strong> If the figure is really there at the point of sale, that is the <a href="/platforms/courtyard/">Courtyard</a> standard, and only four platforms here meet it.</li>
    <li><strong>A provable fairness claim with documentation.</strong> Rarity distributions are part of each opening&rsquo;s verifiable record. <a href="/platforms/rip-station/">Rip Station</a> explicitly disclaims this; Phygitals leans into it.</li>
    <li><strong>The buyback rate can be better than standard.</strong> Enhanced rates above 85% exist and are badged before purchase rather than discovered after.</li>
  </ul>

  <h2>The 30-minute window is the thing to watch</h2>
  <div class="callout danger">
    <h3>&ldquo;The buyback window begins the moment your pack opening is complete&rdquo;</h3>
    <p>Phygitals documents a <strong>30-minute</strong> buyback window on standard cards. Once it closes, &ldquo;the offer is permanently removed.&rdquo; For comparison, we have called <a href="/platforms/pickem/">Pickem&rsquo;s three hours</a> the tightest decision window in the category across nineteen pages. Thirty minutes would be six times tighter.</p>
    <p>Underdog&rsquo;s own help centre says three days for Rips, and three days is a perfectly reasonable window. But if you use Phygitals directly, or if Underdog ever runs a standard-card pack, the clock is half an hour from the reveal &mdash; and the countdown starts while you are still looking at the card.</p>
  </div>

  <h2>What we could not establish</h2>
  <p>This page is thinner on numbers than it should be, and it is worth being explicit about why.</p>

  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Pack prices</th><td>Not published. The terms say &ldquo;various price points as displayed on the platform&rdquo;</td></tr>
    <tr><th scope="row">Actual odds</th><td>Claimed by both parties; we could not reach a page showing figures, so nothing is verified</td></tr>
    <tr><th scope="row">Which buyback applies</th><td>Underdog states none; Phygitals&rsquo; 85% may or may not be what Underdog pays</td></tr>
    <tr><th scope="row">Payout form on Underdog</th><td>Phygitals pays USDC to a wallet; whether an Underdog user receives USDC or an Underdog account balance is unclear</td></tr>
    <tr><th scope="row">States</th><td>&ldquo;Not available in all states&rdquo; with no list we could find</td></tr>
    <tr><th scope="row">Age</th><td>Not established for Rips specifically</td></tr>
  </tbody>
  </table>
  </div>

  <p>Underdog is a large, well-known operator, and that cuts both ways here. It brings a mainstream audience to randomised card packs, and it is the kind of company that could set a disclosure norm for the category simply by publishing the rate on its own help pages. Right now it publishes less about this product than several platforms a hundredth its size.</p>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>Underdog Sports, the fantasy and pick&rsquo;em operator</td></tr>
    <tr><th scope="row">Infrastructure</th><td>Phygitals, named as the independent third party that sources, vaults and ships the physical cards</td></tr>
    <tr><th scope="row">Product</th><td>Digital packs, each containing one real physical sports card</td></tr>
    <tr><th scope="row">After a pull</th><td>Redeem the physical card, hold it digitally, or sell it back. One path per card, and the choice &ldquo;cannot be reversed&rdquo;</td></tr>
    <tr><th scope="row">Window</th><td>3 days on Underdog, then automatically bought back. Phygitals documents 30 minutes, 3 days or 7 days by card type</td></tr>
    <tr><th scope="row">Holding</th><td>&ldquo;Holding a card costs you nothing&rdquo; during the window</td></tr>
    <tr><th scope="row">Buyback</th><td>Not stated by Underdog. 85% of FMV per Phygitals, with enhanced rates badged before purchase</td></tr>
    <tr><th scope="row">Payout</th><td>USDC to a wallet per Phygitals; unconfirmed for Underdog accounts</td></tr>
    <tr><th scope="row">Valuation</th><td><strong class="pos">Third-party pricing providers</strong> for graded collectibles, fixed at the pull; providers unnamed</td></tr>
    <tr><th scope="row">Fairness</th><td>Provably fair record claimed, with separate verification documentation</td></tr>
    <tr><th scope="row">Shipping</th><td>US addresses only; cost not published</td></tr>
    <tr><th scope="row">States</th><td>&ldquo;Not available in all states&rdquo;; no list located</td></tr>
  </tbody>
  </table>
  </div>

  <div class="callout">
    <h3>Why this page has no rating</h3>
    <p>We have verified no figure on this page from the platform a buyer actually transacts with. No pack prices, no odds tables, no stated buyback rate from Underdog itself. Everything numeric here comes from the supplier&rsquo;s documentation and may or may not describe what an Underdog customer gets. That is not enough to score, and we would rather say so than extend Underdog&rsquo;s reputation to a product we could not read. <a href="/methodology/">Our methodology</a> explains why.</p>
    <p>If you have opened an Underdog Rips pack and can screenshot the odds display, the EV figure, or a buyback offer with its percentage, that is what this page needs.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/platforms/fanatics-instant-rips/">Fanatics, the other platform that outsources card valuation</a></li>
    <li><a href="/compare/?p=underdog,fanatics-instant-rips,courtyard">Compare Underdog, Fanatics and Courtyard side by side</a></li>
    <li><a href="/platforms/pickem/">Pickem, and what a short decision window really costs</a></li>
    <li><a href="/guides/buyback-rates/">What a buyback is actually worth, across every platform</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html,
           **{"flags_underdog": flag_row("underdog")})

    return pages_written("/platforms/underdog/", page(
        "/platforms/underdog/",
        "Underdog Rips review — the buyback rate is in the supplier's docs, not Underdog's",
        "Underdog Rips gives you three days and states no buyback rate. Phygitals, which powers it, documents 85% of FMV in USDC, third-party valuations and a window as short as 30 minutes.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"),
                (None, "Underdog Rips")],
        updated=UPDATED, structured=faq_ld))


def build_ripstation():
    packs = [25, 50, 60, 100, 150, 200, 250, 500]
    pack_rows = "".join(
        '<tr><td class="name">Pok&eacute;mon %s Pack</td><td class="num">%s</td>'
        '<td><strong class="neg">Data unavailable &mdash; inventory not verified</strong></td></tr>'
        % (money(v), money(v)) for v in packs)
    pack_rows += (
        '<tr><td class="name">Pok&eacute;mon $50 Floor Pack</td><td class="num">$50.00</td>'
        '<td><strong class="neg">Data unavailable &mdash; inventory not verified</strong></td></tr>'
        '<tr><td class="name">Pok&eacute;mon $50 Max Buyback Pack</td><td class="num">$50.00</td>'
        '<td><strong class="neg">Data unavailable &mdash; inventory not verified</strong></td></tr>')

    faq_html, faq_ld = faq_block([
        ("Does Rip Station publish expected values?",
         "<p>It publishes a page for them. Rip Station links an &ldquo;EV &amp; Odds&rdquo; page from its navigation, and that page lists all ten packs. When we read it on %s, every single expected value read <strong>&ldquo;Data unavailable &mdash; inventory not verified.&rdquo;</strong> Not one figure was populated. The page says odds are published &ldquo;when available&rdquo; on each pack page. We could not find a populated set.</p>" % UPDATED),
        ("What is the Rip Station buyback rate?",
         "<p>83% of a card's current estimated market value &mdash; not of the pack price &mdash; within seven days of each rip. That is the lowest advertised buyback of the twenty-four platforms we track; every other platform advertises 83% or more, and most say 90% or 100%. Rip Station is also unusually clear that it is not a promise: the FAQ calls it &ldquo;not a guaranteed refund&rdquo; and says &ldquo;Buyback is not guaranteed liquidity,&rdquo; and Rip Station may modify or discontinue it.</p>"),
        ("Can you withdraw money from Rip Station?",
         "<p>We cannot tell you. The FAQ says buyback proceeds land &ldquo;in your wallet,&rdquo; but it describes no withdrawal process, no minimum and no cap anywhere. The only place withdrawal appears at all is in the answer about the service shutting down, which says &ldquo;available wallet balances may be withdrawn during that window.&rdquo; A platform that documents withdrawal only in the context of its own closure has left the most important question about its product unanswered.</p>"),
        ("Who operates Rip Station?",
         "<p>Byzantine Port Technologies Inc., a Panama company, as a subsidiary of Byzantion Inc., a Delaware corporation. That makes it the fourth platform we track whose operating entity sits outside the United States, after <a href=\"/platforms/mintpull/\">MintPull</a> in Hong Kong, <a href=\"/platforms/letsgo/\">LETSGO</a> in Israel and <a href=\"/platforms/gotya/\">Gotya</a> under English law. Sign-in is by Google, email, Telegram or X, and you can connect a crypto wallet.</p>"),
        ("What does Rip Station shipping cost?",
         "<p>The carrier's rate plus a $5 handling fee per card. Optional insurance is 1% of declared value with a $1 minimum, capped at $5,000 per box. The FAQ says &ldquo;most single-card orders in the US come to about $11 in total,&rdquo; and international runs &ldquo;$18 to $36 per box, plus handling,&rdquo; with duties extra. That is the most detailed shipping disclosure of any platform we track &mdash; most publish nothing at all.</p>"),
        ("Is Rip Station provably fair?",
         "<p>It says it is not. The FAQ states plainly that published odds are &ldquo;not a cryptographic proof of fairness.&rdquo; Odds derive from the cards currently loaded in each machine rather than a fixed pull-rate table, and update as cards are pulled and the vault restocked. For a platform with crypto wallet sign-in, declining to claim provable fairness is a notable piece of restraint.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Rip Station built a page for expected values and left every field empty</h1>
    <p class="lede">An &ldquo;EV &amp; Odds&rdquo; page listing ten packs, every figure reading &ldquo;Data unavailable.&rdquo; An 83% buyback, the lowest advertised anywhere. And a FAQ unusually honest about what none of it guarantees.</p>
    {flags_rip_station}
  </div>

  <div class="finding">
    <p class="big">Rip Station links an &ldquo;EV &amp; Odds&rdquo; page from its own navigation. On {collected} it listed all ten packs, from {minp} to {maxp}, and every expected value on it read <strong>&ldquo;Data unavailable &mdash; inventory not verified.&rdquo;</strong> Separately, the buyback is <strong>83%</strong> of estimated market value &mdash; the lowest advertised figure across the twenty-four platforms we track.</p>
    <p class="small muted">Read from ripstation.io and its FAQ on {collected}. Inventory-driven figures can change; this describes what the page showed that day.</p>
  </div>

  <h2>The page, as we found it</h2>
  <div class="table-wrap">
  <table>
  <caption>Rip Station's &ldquo;EV &amp; Odds&rdquo; page, {collected}.</caption>
  <thead><tr><th scope="col">Pack</th><th scope="col" class="num">Price</th><th scope="col">Stated expected value</th></tr></thead>
  <tbody>{packs}</tbody>
  </table>
  </div>

  <p>We want to be fair about what this is. Rip Station's odds are drawn from the cards actually loaded in each machine rather than from a fixed table, and they move as cards are pulled and the vault restocked. &ldquo;Inventory not verified&rdquo; is plausibly a transient state while stock is being reconciled, and the page may well be populated when you read it. We are reporting a day, not a permanent condition.</p>

  <p>But the structural point survives that caveat. <a href="/platforms/courtyard/">Courtyard</a>, <a href="/platforms/swishx/">SwishX</a>, <a href="/platforms/gotya/">Gotya</a> and <a href="/platforms/catchback/">CatchBack</a> all publish an expected value that is there when you look. A disclosure surface that is empty at the moment of purchase is not a disclosure, however good the intention behind building it.</p>

  <h2>83%, and why we are not hammering them for it</h2>
  <p>Rip Station's buyback is the lowest advertised number on this site. Here is the whole field:</p>

  <div class="table-wrap">
  <table>
  <caption>Advertised buyback rates across the platforms that state one, {collected}.</caption>
  <thead><tr><th scope="col" class="num">Rate</th><th scope="col">Platforms</th></tr></thead>
  <tbody>
    <tr><td class="num">100%</td><td>Packed, Chalkboard Pulls, Crown Rips, Fast Rips, MintPull, Rips by Triumph</td></tr>
    <tr><td class="num">90%</td><td>Courtyard, Packz, Arena Club, Tilt Rips, Pickem, Gotya, Holofoil, CatchBack, Rare Candy, LETSGO</td></tr>
    <tr><td class="num">85&ndash;90%</td><td>SwishX</td></tr>
    <tr><td class="num"><strong class="neg">83%</strong></td><td><strong>Rip Station</strong></td></tr>
  </tbody>
  </table>
  </div>

  <p>That looks damning until you read the rest of this site. <a href="/platforms/fanatics-instant-rips/">Fanatics</a> advertises 90% and nets 84.6% after fees. <a href="/platforms/fast-rips/">Fast Rips</a> advertises 100% and its terms describe non-withdrawable credit. <a href="/platforms/mintpull/">MintPull</a> advertises 100% and pays pack credit with a $250 weekly cap. <a href="/platforms/triumph/">Triumph</a> headlines a 100% guarantee its &sect;5.5 says it is under no obligation to honour.</p>

  <p><strong>A plainly stated 83% may be worth more than several of the 100%s above it.</strong> That is the argument of our <a href="/guides/buyback-rates/">buyback comparison</a>, and Rip Station is the clearest illustration of it we have found: the lowest number in the category, attached to the least spin.</p>

  <h2>The candour runs through the FAQ</h2>
  <p>Platforms in this category tend to write FAQs that sell. Rip Station's reads like a risk disclosure, and we think that is to its credit even where the content is unwelcome:</p>

  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">On the buyback</th><td>&ldquo;Not a guaranteed refund.&rdquo; &ldquo;Buyback is not guaranteed liquidity.&rdquo; May be modified or discontinued</td></tr>
    <tr><th scope="row">On fairness</th><td>Published odds are &ldquo;not a cryptographic proof of fairness&rdquo;</td></tr>
    <tr><th scope="row">On insurance</th><td>Vault insurance is subject to policy terms and is &ldquo;not a promise of full recoverability&rdquo;</td></tr>
    <tr><th scope="row">On value</th><td>From a linked post: &ldquo;Estimated card value is not guaranteed cash profit&rdquo;</td></tr>
  </tbody>
  </table>
  </div>

  <p>Declining to claim provable fairness is particularly notable for a platform with Telegram and crypto-wallet sign-in, where that claim is close to standard marketing.</p>

  <h2>The question the FAQ does not answer</h2>
  <div class="callout danger">
    <h3>Withdrawals appear once, in the shutdown answer</h3>
    <p>The FAQ says buyback proceeds land &ldquo;in your wallet.&rdquo; It then describes no withdrawal process, no minimum, no cap, no payout method and no timeframe anywhere. The only mention of withdrawing money in the entire document is in the answer about the service shutting down: &ldquo;available wallet balances may be withdrawn during that window.&rdquo;</p>
    <p>That tells us withdrawal exists. It tells us nothing about how to do it while the service is running, which is the question that decides whether an 83% buyback is worth 83 cents or nothing. Until we can confirm it, the cell on our <a href="/guides/withdrawals/">withdrawals page</a> stays unconfirmed.</p>
  </div>

  <h2>Panama, under Delaware</h2>
  <p>Rip Station is operated by <strong>Byzantine Port Technologies Inc., a Panama company</strong>, as a subsidiary of <strong>Byzantion Inc., a Delaware corporation</strong>. The footer carries the Byzantion name; the Panama entity appears in the FAQ.</p>

  <p>That is the fourth non-US operating structure we have documented, after Hong Kong, Israel and England and Wales. As we have said on each of those pages, incorporating abroad is not wrongdoing. It is a material fact about who holds your balance and which courts would hear a dispute, and Rip Station discloses it in its FAQ rather than burying it &mdash; which is more than <a href="/platforms/letsgo/">LETSGO</a> does.</p>

  <h2>Shipping, which it documents better than anyone</h2>
  <p>One area where Rip Station is simply the best in the category:</p>

  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Handling</th><td>$5 per card, on top of the carrier's rate</td></tr>
    <tr><th scope="row">Insurance</th><td>Optional, 1% of declared value, $1 minimum, capped at $5,000 per box</td></tr>
    <tr><th scope="row">Typical US cost</th><td>&ldquo;Most single-card orders in the US come to about $11 in total&rdquo;</td></tr>
    <tr><th scope="row">International</th><td>&ldquo;$18 to $36 per box, plus handling&rdquo;; duties and taxes extra</td></tr>
    <tr><th scope="row">Title</th><td>You hold title; cards sit in third-party insured vaults</td></tr>
  </tbody>
  </table>
  </div>

  <p>Most platforms on this site publish no shipping figure at all, and several make you reach checkout to find one. A stated typical total is genuinely useful, and we would like to see it copied.</p>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>Byzantine Port Technologies Inc. (Panama), subsidiary of Byzantion Inc. (Delaware)</td></tr>
    <tr><th scope="row">Category</th><td>Pok&eacute;mon; each pack pulls one graded card from an insured vault</td></tr>
    <tr><th scope="row">Packs</th><td>Ten listed, {minp} to {maxp}, including a &ldquo;Floor Pack&rdquo; and a &ldquo;Max Buyback Pack&rdquo; at $50</td></tr>
    <tr><th scope="row">Odds</th><td>Derived from cards loaded in each machine; update as cards are pulled and restocked; &ldquo;not a cryptographic proof of fairness&rdquo;</td></tr>
    <tr><th scope="row">Expected value</th><td><strong class="neg">A page exists; every figure read &ldquo;Data unavailable&rdquo; on {collected}</strong></td></tr>
    <tr><th scope="row">Buyback</th><td><strong class="neg">83%</strong> of estimated market value, within 7 days of each rip; &ldquo;not guaranteed liquidity&rdquo;</td></tr>
    <tr><th scope="row">Proceeds</th><td>&ldquo;Lands in your wallet.&rdquo; No withdrawal process, minimum or cap documented</td></tr>
    <tr><th scope="row">Valuation</th><td>From &ldquo;real recent sales across the trading card market&rdquo;; the same data sets the buyback</td></tr>
    <tr><th scope="row">Vault</th><td>Third-party insured vaults; you hold title; insurance &ldquo;not a promise of full recoverability&rdquo;</td></tr>
    <tr><th scope="row">If it shuts down</th><td>&ldquo;Typically thirty days&rdquo; to start a claim for physical collectibles in vault storage</td></tr>
    <tr><th scope="row">Sign-in</th><td>Google, email, Telegram or X; crypto wallet connection offered</td></tr>
    <tr><th scope="row">Age</th><td>18+, or the local age of majority if greater</td></tr>
    <tr><th scope="row">Where</th><td>No US state list; sanctioned and prohibited jurisdictions excluded; VPN use to evade geography prohibited</td></tr>
  </tbody>
  </table>
  </div>

  <div class="callout">
    <h3>Why this page has no rating</h3>
    <p>The platform's own expected-value page was empty when we read it, and no pull rates were published on any pack we could reach, so three of our five inputs are unavailable. The buyback rate is clearly stated at 83%, but we cannot confirm the payout form or the withdrawal route, so we cannot say what the 83% is worth. <a href="/methodology/">Our methodology</a> explains why we leave a cell empty rather than guess.</p>
    <p>If you have seen the EV page populated, or can confirm how a wallet balance is withdrawn, we will update this page and say so in the <a href="/changelog/">changelog</a>.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/guides/buyback-rates/">Why a stated 83% can beat an advertised 100%</a></li>
    <li><a href="/compare/?p=rip-station,swishx,gotya">Compare Rip Station against two platforms that do publish an EV</a></li>
    <li><a href="/guides/withdrawals/">Which platforms actually pay out money</a></li>
    <li><a href="/platforms/">All twenty-four platforms compared</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html, packs=pack_rows,
           minp=money(25), maxp=money(500),
           **{"flags_rip_station": flag_row("rip-station")})

    return pages_written("/platforms/rip-station/", page(
        "/platforms/rip-station/",
        "Rip Station review — an expected-value page with no expected values",
        "Rip Station publishes an EV & Odds page; every figure on it read “Data unavailable” when we checked. Its 83% buyback is the lowest advertised anywhere, and the most plainly stated.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "Rip Station")],
        updated=UPDATED, structured=faq_ld))


def build_catchback():
    p = CATCHBACK_PACK
    s = catchback_stats()

    band_rows = "".join(
        '<tr><td class="num">%s&ndash;%s</td><td class="num">%s</td>'
        '<td class="num">%s</td></tr>'
        % (money(lo), money(hi), pct(q, 2), money((lo + hi) / 2.0 * q / 100.0))
        for lo, hi, q in p["bands"])

    pool_rows = "".join(
        '<tr><td class="name">%s</td><td class="num">%s&ndash;%s</td></tr>'
        % (t[0], money(t[1]), money(t[2])) for t in p["pool"])

    faq_html, faq_ld = faq_block([
        ("Is the CatchBack Boost add-on worth it?",
         "<p>Only on a card worth more than <strong>%s</strong>. Boost costs $3.75 on a $25 pack and raises the buyback from 90%% to 110%% &mdash; an uplift of 20 points of the card's value. Twenty percent of $18.75 is exactly $3.75, so below that figure the add-on costs more than it returns. CatchBack's own odds put 72%% of pulls in the $5&ndash;$25 band, and the cheapest cards in its published pool are $8. The add-on also applies only &ldquo;on a winning pull,&rdquo; a term the pack page does not define, and expires after five minutes.</p>"
         % money(s["boost_breakeven"])),
        ("What does CatchBack Insurance actually pay?",
         "<p>At most %s, and only on a bad pull. Insurance costs $3.75 and guarantees a minimum buyback of 70%% of the pack price, which is %s on a $25 pack. The standard buyback is 90%% of card value, so the guarantee only bites when 90%% of your card is worth less than %s &mdash; that is, a card under about %s. Against the cheapest card in CatchBack's published pool, $8, the top-up would be %s. It pays nothing at all on the 28%% of pulls that land above $25, and it expires in five minutes.</p>"
         % (money(s["ins_max_payout"]), money(s["ins_floor"]),
            money(s["ins_floor"]), money(s["ins_threshold"]),
            money(s["ins_max_payout"]))),
        ("Does CatchBack publish its odds?",
         "<p>Yes, and more than almost anyone. The pack page shows five value bands with percentages that sum to exactly 100.00%, a posted expected value, a 90% buyback figure, and the complete &ldquo;available hits&rdquo; pool &mdash; every card currently in the pack, with its value, grouped by tier. Being able to see the actual pool rather than a sample is disclosure only <a href=\"/platforms/swishx/\">SwishX</a> matches.</p>"),
        ("Does CatchBack's posted expected value add up?",
         "<p>Not quite. The pack page posts an expected value of %s on a %s pack. Working the same figure out from CatchBack's own published bands at their midpoints gives %s &mdash; about %s lower. The gap is explainable: the bottom band spans $5 to $25 while the cheapest cards in the pool are $8, so the true average inside that band sits above its midpoint. But the published numbers do not reconcile on their face, which is different from <a href=\"/platforms/swishx/\">SwishX</a> and <a href=\"/platforms/gotya/\">Gotya</a>, where they do.</p>"
         % (money(s["posted"]), money(s["price"]), money(s["mid"]),
            pct(s["gap"] * 100, 1))),
        ("What does the CatchBack risk selector do?",
         "<p>It changes the shape of the bet. The pack builder offers Chill, Standard and Hot, which adjust the distribution rather than the price. We collected the Standard setting; the odds on this page describe that one. A volatility selector is a familiar control from casino products and we have not seen it on any other card platform.</p>"),
        ("Who operates CatchBack?",
         "<p>We could not establish it. The site names no legal entity, no address and no governing law anywhere we could reach, and its Terms of Service and Privacy Policy are hosted on a third-party documentation subdomain rather than on its own site. Age and state restrictions are not published either. That is a notable gap on a platform that discloses its odds this thoroughly.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>CatchBack publishes more than almost anyone, then sells you two bets on the result</h1>
    <p class="lede">Full band odds, a posted expected value and the entire card pool with values. Also a risk selector, a paid &ldquo;Boost,&rdquo; a paid &ldquo;Insurance,&rdquo; and a five-minute clock on both.</p>
    {flags_catchback}
  </div>

  <div class="finding">
    <p class="big">On a {price} pack, the two optional add-ons cost {addon} each &mdash; {both} of the pack price if you take both. The Boost pays for itself only on a card worth more than <strong>{beven}</strong>, and CatchBack's own odds put <strong>{bottom}</strong> of pulls in the $5&ndash;$25 band. The Insurance can pay at most <strong>{insmax}</strong>, and nothing at all on the 28% of pulls above $25.</p>
    <p class="small muted">Collected from the live CatchBack pack builder on {collected}: {name}, {cat} category, {risk} risk. We could not reach the Terms of Service, which are hosted on a third-party subdomain.</p>
  </div>

  <h2>First, credit where it is due</h2>
  <p>This page is critical, so the disclosure deserves saying first: CatchBack publishes more about its packs than sixteen of the twenty-four platforms we track.</p>

  <div class="table-wrap">
  <table>
  <caption>{name}, {price} &mdash; CatchBack's published value bands, {collected}. The last column is each band's contribution to the midpoint expected value.</caption>
  <thead><tr><th scope="col" class="num">Pull value</th><th scope="col" class="num">Chance</th><th scope="col" class="num">Contributes</th></tr></thead>
  <tbody>{bands}</tbody>
  <tfoot><tr><th scope="row" class="num">Total</th><td class="num">{psum}</td><td class="num"><strong>{mid}</strong></td></tr></tfoot>
  </table>
  </div>

  <p>The rates sum to exactly 100.00%. On top of that, the pack page lists the <strong>entire available pool</strong> &mdash; every card currently in the pack, with its value, grouped by tier:</p>

  <div class="table-wrap">
  <table class="plain">
  <caption>The tiers in the live pool and the value range we observed in each, {collected}.</caption>
  <thead><tr><th scope="col">Tier</th><th scope="col" class="num">Observed values</th></tr></thead>
  <tbody>{pool}</tbody>
  </table>
  </div>

  <p>Seeing the actual inventory rather than a sample is disclosure only <a href="/platforms/swishx/">SwishX</a> matches. There is also a free demo pack, which almost nobody offers.</p>

  <h2>The posted expected value does not quite reconcile</h2>
  <p>CatchBack posts an expected value of <strong>{posted}</strong> on a {price} pack &mdash; {postedr} of the price. Working the same figure out from its own bands at their midpoints gives <strong>{mid}</strong>, or {midr}. The posted figure is {gap} higher than its own published odds imply.</p>

  <p>There is a fair explanation. The bottom band is quoted as $5&ndash;$25, but the cheapest card in the published pool is $8 and the Starter tier tops out at $21, so the real average inside that band sits above its midpoint. Our midpoint method understates it. That is the same band-width problem we wrote about on <a href="/platforms/rare-candy/">Rare Candy</a>, and it is a limitation of the method rather than evidence of anything.</p>

  <p>It is still worth noting, because <a href="/platforms/swishx/">SwishX</a> and <a href="/platforms/gotya/">Gotya</a> both publish figures that reconcile with their own odds to within a percent. CatchBack's does not, and the fix would be to publish the distribution inside the bottom band.</p>

  <h2>The add-ons, priced</h2>
  <p>This is the part we have not had to write before. Alongside the pack, CatchBack sells two optional products at the moment of purchase. Both cost {addon} on a {price} pack. Both expire five minutes after the pull.</p>

  <div class="callout danger">
    <h3>What the pack builder says</h3>
    <p><strong>Boost, +{addon}:</strong> &ldquo;Get a 110% buyback (instead of 90%) on a winning pull, within 5 min.&rdquo;</p>
    <p><strong>Insurance, +{addon}:</strong> &ldquo;Guaranteed minimum buyback of 70% of pack price ({insfloor}) if you sell back within 5 min.&rdquo;</p>
  </div>

  <h3>Boost</h3>
  <p>Boost raises the buyback from 90% to 110% &mdash; an uplift of 20 points of the card's value. The arithmetic is simple: 20% of a card has to exceed {addon} for the add-on to pay for itself, so the break-even card value is <strong>{beven}</strong>.</p>

  <p>CatchBack's own published odds put <strong>{bottom} of pulls in the $5&ndash;$25 band</strong>, and the cheapest cards in its pool are $8. A substantial share of pulls therefore land below the break-even point, where Boost is a straight loss. It also applies only &ldquo;on a winning pull,&rdquo; which the pack page never defines &mdash; so the condition under which it pays at all is not published.</p>

  <h3>Insurance</h3>
  <p>Insurance guarantees a minimum buyback of {insfloor}. The standard buyback is 90% of card value, so the floor only engages when 90% of your card is worth less than {insfloor} &mdash; a card below about <strong>{insthresh}</strong>.</p>

  <p>The maximum it can ever pay is bounded by the cheapest card in the pool. Pull the $8 floor card and the standard buyback is $7.20; the guarantee tops that to {insfloor}, a payout of <strong>{insmax}</strong>. That is the best case. On the 28% of pulls landing above $25, it pays nothing with certainty.</p>

  <div class="callout">
    <h3>What we are and are not saying</h3>
    <p>We cannot tell you whether either add-on is priced fairly, and neither can you, because the distribution <em>inside</em> the bottom band is not published &mdash; and that distribution is exactly what decides both. What we can say is that these are wagers on the outcome of another wager, sold at the moment of maximum excitement, with a five-minute expiry, for 15% of the pack price each.</p>
    <p>No other platform we track sells anything like this. The closest is <a href="/platforms/arena-club/">Arena Club's</a> Collect Safe, which costs 10% for an 80% floor &mdash; and we called that paid insurance rather than a bonus too.</p>
  </div>

  <h2>Five minutes is the shortest clock on this site</h2>
  <p>Both add-ons expire five minutes after the pull. For context, we have spent nineteen platform pages writing about decision windows:</p>

  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">CatchBack add-ons</th><td><strong class="neg">5 minutes</strong></td></tr>
    <tr><th scope="row">Pickem</th><td>3 hours, then the card is sold for you</td></tr>
    <tr><th scope="row">Packed, Chalkboard Pulls</th><td>1 day</td></tr>
    <tr><th scope="row">Holofoil</th><td>30 days, then converted to credit</td></tr>
    <tr><th scope="row">Poke-Collect</th><td>1 year, then shipped to you free</td></tr>
  </tbody>
  </table>
  </div>

  <p>In fairness, the five minutes applies to the optional add-ons rather than to the card itself &mdash; nothing suggests CatchBack takes your card away. But a five-minute expiry on a paid decision, taken seconds after a pull, is the tightest pressure we have found anywhere in this category.</p>

  <h2>The surrounding product</h2>
  <p>CatchBack runs a live global chat beside the pack builder, with user-funded &ldquo;pack drops&rdquo; that others join, VIP tiers (we saw Bronze, Emerald, Affiliate, Gifter and Moderator badges), a running feed of recent hits with dollar values, and an online-user counter. Pack levels run Base through Black Obsidian across six categories including Watches and Streetwear, with a Custom Pack option like <a href="/platforms/holofoil/">Holofoil's</a>.</p>

  <p>These are social casino mechanics. The gifting loop, the tiering, the public win feed and the volatility selector are all drawn from a different product category than collecting. We note it because a reader deciding how to spend an evening should know which design tradition they are inside.</p>

  <div class="callout danger">
    <h3>If you use CatchBack</h3>
    <p>Work out the break-even before you buy, not after you pull. Boost needs a card over {beven} to pay for itself; Insurance pays at most {insmax} and nothing above a {insthresh} card. Taking both costs {both} of the pack price before you have seen anything. Decide on the add-ons when you are calm, and set what you will spend in advance of the chat and the drops, not during them.</p>
    <p>If this has stopped feeling like fun, free and confidential help is available: call or text <strong>1-800-GAMBLER</strong>.</p>
  </div>

  <h2>What we could not establish</h2>
  <p>The site names no operating company, no registered address and no governing law anywhere we could reach. Its Terms of Service and Privacy Policy are hosted on a third-party documentation subdomain rather than on catchbackcards.com, and our fetch of that document did not complete. No age requirement and no state restrictions are published on the pages we read.</p>

  <p>That is an unusual combination: among the most thorough odds disclosure in the category, paired with among the least disclosure about the company behind it. We will update this page when we can read the terms.</p>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td><strong class="neg">Not established.</strong> No entity, address or governing law found; legal documents hosted on a third-party subdomain</td></tr>
    <tr><th scope="row">Categories</th><td>Pok&eacute;mon, Sports, One Piece, Riftbound, Watches, Streetwear, plus Custom Packs</td></tr>
    <tr><th scope="row">Pack levels</th><td>Base, Mega Base, Bronze, Silver, Gold, Emerald, Diamond, Sapphire, Crimson Ruby, Black Obsidian; Standard, Specialty, Sealed Inventory and Custom types</td></tr>
    <tr><th scope="row">Odds</th><td><strong class="pos">Value bands summing to exactly 100.00%, plus the full available pool with per-card values</strong></td></tr>
    <tr><th scope="row">Posted EV</th><td>{posted} on a {price} pack; {gap} above the midpoint of its own bands</td></tr>
    <tr><th scope="row">Risk selector</th><td>Chill, Standard or Hot &mdash; changes the distribution, not the price</td></tr>
    <tr><th scope="row">Buyback</th><td>90% of value, displayed beside the odds</td></tr>
    <tr><th scope="row">Boost add-on</th><td>{addon}; 110% instead of 90% &ldquo;on a winning pull,&rdquo; within 5 minutes. Break-even at {beven} of card value</td></tr>
    <tr><th scope="row">Insurance add-on</th><td>{addon}; floor of {insfloor}, within 5 minutes. Engages below a {insthresh} card; maximum payout {insmax}</td></tr>
    <tr><th scope="row">Shipping</th><td>Free on orders of $50 or more in the US; flat $8 under $50; select international with customs handled at checkout</td></tr>
    <tr><th scope="row">Demo</th><td>A free demo pack is offered before purchase</td></tr>
    <tr><th scope="row">Community</th><td>Live global chat, user-funded pack drops, VIP tiers, a public hits feed and an online-user counter</td></tr>
    <tr><th scope="row">Age and states</th><td><strong class="neg">Not published</strong> anywhere we could reach</td></tr>
  </tbody>
  </table>
  </div>

  <div class="callout">
    <h3>Why this page has no rating</h3>
    <p>The odds disclosure would score well. But we could not read the terms, so the payout form, the withdrawal route, the age requirement, the state restrictions and the operator are all unknown &mdash; and a platform selling paid side bets is one where those answers matter more, not less. <a href="/methodology/">Our methodology</a> explains why we leave a cell empty rather than guess.</p>
    <p>If you can share CatchBack's Terms of Service, or in-app confirmation of how buyback proceeds are paid, we will update this page.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/compare/?p=catchback,swishx,gotya">Compare CatchBack, SwishX and Gotya side by side</a></li>
    <li><a href="/guides/bonus-offers/">Bonus offers ranked by what they are actually worth</a></li>
    <li><a href="/is-card-ripping-gambling/">Is card ripping gambling? Where the law stands</a></li>
    <li><a href="/calculator/">Run these bands through the pack EV calculator</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html, bands=band_rows, pool=pool_rows,
           name=p["name"], cat=p["category"], risk=p["risk"],
           price=money(s["price"]), posted=money(s["posted"]),
           mid=money(s["mid"]), psum=pct(s["psum"], 2),
           postedr=pct(s["posted_ratio"] * 100, 0),
           midr=pct(s["mid_ratio"] * 100, 1), gap=pct(s["gap"] * 100, 1),
           addon=money(s["addon_cost"]), both=pct(s["both_pct"] * 100, 0),
           beven=money(s["boost_breakeven"]), insfloor=money(s["ins_floor"]),
           insthresh=money(s["ins_threshold"]),
           insmax=money(s["ins_max_payout"]),
           bottom=pct(s["bottom_share"], 0),
           **{"flags_catchback": flag_row("catchback")})

    ld = [faq_ld, jsonld({
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "CatchBack published pack odds and add-on pricing",
        "description": "Published value-band odds, posted expected value, card pool and derived break-even analysis of the Boost and Insurance add-ons for a CatchBack Base Pack, collected %s." % UPDATED,
        "url": BASE_URL + "/platforms/catchback/",
        "creator": {"@type": "Organization", "name": SITE_NAME},
        "license": "https://creativecommons.org/licenses/by/4.0/",
    })]

    return pages_written("/platforms/catchback/", page(
        "/platforms/catchback/",
        "CatchBack review — the odds are published, and so are two side bets",
        "CatchBack publishes full band odds, a posted EV and its whole card pool. It also sells a Boost and an Insurance add-on at $3.75 each. We priced both.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "CatchBack")],
        updated=UPDATED, structured=ld))


def build_holofoil():
    faq_html, faq_ld = faq_block([
        ("Can you withdraw money from Holofoil?",
         "<p>No, and the terms are unusually direct about it. Section 4 says Holofoil Credit &ldquo;cannot be withdrawn, cashed out, sold, or transferred to another account or person&rdquo; and has no cash value except where the law requires otherwise. It adds that Holofoil does not offer cash payouts for sell-backs, vault conversions, promotions or returns. Money goes in through Stripe; the only way value comes back out is as a physical card you pay to ship. No other platform we track closes the exit this completely.</p>"),
        ("How long can you keep a card in the Holofoil vault?",
         "<p>Thirty days. Section 10 states that &ldquo;cards left in your vault for more than 30 days may be automatically converted to Holofoil Credit,&rdquo; counted from the date the card entered the vault, though Holofoil may extend that at its discretion. Read it beside section 4 and the effect is specific: a card you do not ship within a month becomes credit that can never become money again.</p>"),
        ("Does Holofoil publish pack odds?",
         "<p>Yes, and its terms require it to. Section 5 says each product page must show the pack contents, price and current pull rates before purchase &mdash; a contractual commitment only <a href=\"/platforms/packed/\">Packed</a> otherwise makes. The pack builder shows per-card odds as &ldquo;1 in N&rdquo;: we recorded 1 in 1,533 for SIR cards, 1 in 1,022 for Gold, 1 in 292 for IR, 1 in 204 for MAR and 1 in 192 for EX. Section 5 also warns the rates describe the product &ldquo;as currently configured&rdquo; and are &ldquo;not a promise about any single pack.&rdquo;</p>"),
        ("What is a Holofoil Custom Pack?",
         "<p>A pack you build yourself. You pick which cards you want to be available, the platform quotes a price, and you rip: &ldquo;Pay only for the cards you pick &mdash; keep them if they hit.&rdquo; We have not seen this mechanic anywhere else in the category. Standard packs are priced dynamically rather than at round numbers &mdash; we recorded True Ascended at $9.20, Collector's Pack at $10.56 and Heavy Pack at $26.26 &mdash; which is consistent with pricing computed from live inventory.</p>"),
        ("Who operates Holofoil?",
         "<p>First Edition TCG LLC, an Oregon limited liability company trading as Holofoil. Oregon law governs, with AAA individual arbitration, a class-action waiver, a 60-day informal resolution step, a 30-day arbitration opt-out and a one-year limit on claims. Use is limited to the United States and Canada, and shipping to those two countries. You must be 18 or the age of majority where you live, whichever is higher.</p>"),
        ("Does Holofoil admit packs lose money?",
         "<p>More plainly than anyone else here. Section 5 states that values shown are estimates and that receiving cards worth less than the pack price is expected. Most platforms in this category imply the opposite in their marketing. We disagree with several of Holofoil's terms, but that sentence is the most honest single line we have read in nineteen sets of terms.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Holofoil: the only platform where money cannot come back out</h1>
    <p class="lede">Section 4 says Holofoil Credit cannot be withdrawn or cashed out, in any circumstance. Section 10 converts vaulted cards into that same credit after 30 days. Shipping the physical card is the only exit there is.</p>
    {flags_holofoil}
  </div>

  <div class="finding">
    <p class="big">&sect;4: Holofoil Credit &ldquo;cannot be withdrawn, cashed out, sold, or transferred to another account or person,&rdquo; and Holofoil &ldquo;does not offer cash payouts for sell-backs, vault conversions, promotions, or returns.&rdquo; &sect;10: &ldquo;Cards left in your vault for more than 30 days may be automatically converted to Holofoil Credit.&rdquo;</p>
    <p class="small muted">Read from holofoil.com, its pack builder and its Terms of Service on {collected}. Pack prices are dynamic; those quoted here are the figures we observed.</p>
  </div>

  <h2>The two clauses, read together</h2>
  <p>Either clause on its own would be ordinary. Four other platforms we track pay buybacks in credit, and several have vault deadlines. What makes Holofoil distinct is the combination, and the order it puts you in.</p>

  <div class="table-wrap">
  <table class="plain">
  <caption>What happens to a dollar on Holofoil.</caption>
  <tbody>
    <tr><th scope="row">1. In</th><td>You add Holofoil Credit by card through Stripe. It lands instantly</td></tr>
    <tr><th scope="row">2. Rip</th><td>Credit buys packs. &sect;4: credit purchases are &ldquo;final and non-refundable once the credit is delivered&rdquo;; opened packs are final sales</td></tr>
    <tr><th scope="row">3. Pull</th><td>The card goes to your vault. You may sell it back for 90% of Holofoil's estimated value &mdash; <strong>paid in credit</strong> (&sect;11)</td></tr>
    <tr><th scope="row">4. Wait</th><td><strong class="neg">After 30 days the card may be converted to credit automatically</strong> (&sect;10)</td></tr>
    <tr><th scope="row">5. Out</th><td><strong class="neg">There is no cash exit.</strong> &sect;4 forbids withdrawal, cash-out, sale and transfer of credit. The only way value leaves is a physical card, shipped at your cost to a US or Canadian address</td></tr>
  </tbody>
  </table>
  </div>

  <p>So the decision Holofoil actually puts to you is not &ldquo;keep or sell.&rdquo; It is <strong>&ldquo;ship within 30 days, or convert to a balance that can only buy more packs.&rdquo;</strong> Selling a card back does not realise value here in the way it does on <a href="/platforms/gotya/">Gotya</a> or <a href="/platforms/swishx/">SwishX</a>; it moves value sideways into the next rip.</p>

  <h2>How that compares</h2>
  <div class="table-wrap">
  <table>
  <caption>The five platforms whose buybacks pay credit rather than money, and what each lets you do with it.</caption>
  <thead><tr><th scope="col">Platform</th><th scope="col">What the credit can do</th><th scope="col">Any cash route at all?</th></tr></thead>
  <tbody>
    <tr><td class="name">Fanatics Instant Rips</td><td>Spend across Fanatics Live, not only on packs</td><td>No, but the spend is broad</td></tr>
    <tr><td class="name">MintPull</td><td>Buy more packs</td><td>Sale proceeds only, capped at $250 per 7 days</td></tr>
    <tr><td class="name">Packz</td><td>Buy more packs</td><td>No</td></tr>
    <tr><td class="name">Rare Candy</td><td>Buy more packs</td><td>No &mdash; &sect;8.1 gives Candy no cash value</td></tr>
    <tr><td class="name"><strong>Holofoil</strong></td><td>Buy more packs</td><td><strong class="neg">No &mdash; &sect;4 forbids withdrawal, cash-out, sale and transfer</strong></td></tr>
  </tbody>
  </table>
  </div>

  <p>Holofoil and Rare Candy are the two that say it outright in their terms rather than leaving it to be inferred. Of the two, Holofoil is the stricter: Rare Candy has no vault deadline, so a card can simply be kept. Holofoil's 30-day clause means keeping is a decision you have to act on.</p>

  <div class="callout danger">
    <h3>If you use Holofoil, treat deposits as spent</h3>
    <p>Money that goes in cannot come back out as money, under any circumstance the terms describe. Decide what a pack is worth to you as entertainment before you deposit, not after you pull. If you pull something you want, <strong>ship it inside 30 days</strong> &mdash; that is the only form in which value leaves the platform, and the clock starts when the card enters the vault.</p>
    <p>If this has stopped feeling like fun, free and confidential help is available: call or text <strong>1-800-GAMBLER</strong>.</p>
  </div>

  <h2>What it does better than most</h2>
  <p>This page would be unbalanced if it stopped there, because Holofoil's disclosure is genuinely above the category average in three places.</p>

  <ul>
    <li><strong>Odds are a contractual obligation.</strong> Section 5 requires every product page to show pack contents, price and current pull rates before purchase. Only <a href="/platforms/packed/">Packed</a> otherwise binds itself to publish. And unlike Packed, Holofoil actually does it on the open web: the pack builder lists per-card odds as &ldquo;1 in N.&rdquo;</li>
    <li><strong>It says packs lose money.</strong> Section 5 states that values shown are estimates and that receiving cards worth less than the pack price is expected. In nineteen sets of terms, that is the most honest sentence we have read. Most platforms spend their marketing implying the reverse.</li>
    <li><strong>A real company, named, with ordinary consumer terms.</strong> First Edition TCG LLC, an Oregon company, under Oregon law, with a 30-day arbitration opt-out and Holofoil paying AAA fees on non-frivolous claims under $10,000. Set that against <a href="/platforms/letsgo/">LETSGO</a>, which names no entity at all.</li>
  </ul>

  <h2>The odds it publishes</h2>
  <p>The pack builder shows per-card pull rates rather than value-band probabilities, which means an expected value cannot be worked out from them directly &mdash; you would need the full card pool and its values, and the pool changes with inventory.</p>

  <div class="table-wrap">
  <table>
  <caption>Per-card pull rates observed in the Holofoil pack builder, {collected}.</caption>
  <thead><tr><th scope="col">Rarity</th><th scope="col" class="num">Stated odds</th><th scope="col" class="num">As a percentage</th></tr></thead>
  <tbody>
    <tr><td class="name">SIR</td><td class="num">1 in 1,533</td><td class="num">0.065%</td></tr>
    <tr><td class="name">Gold</td><td class="num">1 in 1,022</td><td class="num">0.098%</td></tr>
    <tr><td class="name">IR</td><td class="num">1 in 292</td><td class="num">0.34%</td></tr>
    <tr><td class="name">MAR</td><td class="num">1 in 204</td><td class="num">0.49%</td></tr>
    <tr><td class="name">EX</td><td class="num">1 in 192</td><td class="num">0.52%</td></tr>
  </tbody>
  </table>
  </div>

  <p>Card values are shown alongside, running from $1 to $1,027 raw and $26 to $2,282 in PSA 10. That is the same shape of disclosure <a href="/platforms/arena-club/">Arena Club</a> offers &mdash; rates and values, but not joined up into a figure you can act on.</p>

  <h2>The Custom Pack, which nobody else does</h2>
  <p>Alongside the fixed packs, Holofoil lets you build one: you choose which cards are in play, the platform quotes a price, and you rip. &ldquo;Pay only for the cards you pick &mdash; keep them if they hit.&rdquo;</p>

  <p>It is the most interesting mechanic we have come across in this category, and it cuts both ways. A buyer who knows what they want can construct a pack around it rather than accepting someone else's pool, which is more control than any other platform gives. But the price is quoted by the platform using its own valuations, and section 8 makes Holofoil's determination of value &ldquo;final.&rdquo; You choose the contents; Holofoil still sets the price of the bet.</p>

  <p>Prices generally are dynamic rather than round &mdash; True Ascended at $9.20, Collector's Pack at $10.56, Heavy Pack at $26.26, with Rarity Run and Slab Packs observed between $36 and $47. Our figures describe {collected} and are not a price list.</p>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>First Edition TCG LLC, an Oregon limited liability company, trading as Holofoil</td></tr>
    <tr><th scope="row">Governing law</th><td>Oregon and US federal law (&sect;23); AAA individual arbitration, class waiver, 60-day informal step, 30-day opt-out, one-year claim limit (&sect;22)</td></tr>
    <tr><th scope="row">Category</th><td>Pok&eacute;mon only. Independent of The Pok&eacute;mon Company, Nintendo, Game Freak and Creatures</td></tr>
    <tr><th scope="row">Packs</th><td>True Ascended, Heavy, Collector's, Custom, plus Rarity Run and Slab Packs; prices dynamic</td></tr>
    <tr><th scope="row">Odds</th><td><strong class="pos">Required on every product page by &sect;5</strong>; shown per card as &ldquo;1 in N&rdquo;; &ldquo;not a promise about any single pack&rdquo;</td></tr>
    <tr><th scope="row">Buyback</th><td>90% of Holofoil's estimated market value, <strong class="neg">paid in credit</strong>; rate changeable at any time (&sect;11)</td></tr>
    <tr><th scope="row">Credit</th><td><strong class="neg">&ldquo;Cannot be withdrawn, cashed out, sold, or transferred&rdquo;</strong> (&sect;4); credit purchases final once delivered; opened packs final</td></tr>
    <tr><th scope="row">Vault</th><td><strong class="neg">30 days</strong>, then may be converted to credit automatically; extendable at Holofoil's discretion (&sect;10)</td></tr>
    <tr><th scope="row">Valuation</th><td>Holofoil's own methods; may change without notice; its determination is &ldquo;final&rdquo; subject only to the obvious-error process (&sect;&sect;8&ndash;9)</td></tr>
    <tr><th scope="row">Shipping</th><td>US and Canada only; live carrier rates, one fee per box, optional insurance; title and risk pass at carrier handoff; report problems within 10 days (&sect;12)</td></tr>
    <tr><th scope="row">Promotions</th><td>Extra 20% credit on a first purchase, capped at $20</td></tr>
    <tr><th scope="row">Age</th><td>18+, or the local age of majority if higher (&sect;2)</td></tr>
    <tr><th scope="row">Where</th><td>United States and Canada; Holofoil may &ldquo;limit any product in any state, province, or territory&rdquo;; no specific states listed</td></tr>
  </tbody>
  </table>
  </div>

  <div class="callout">
    <h3>Why this page has no rating</h3>
    <p>The odds Holofoil publishes are per card rather than per value band, and the pool changes with inventory, so no expected value can be calculated from them. Prices are dynamic, which removes the other half of the calculation. The buyback cannot be scored on the same scale as the others because its proceeds are not money. <a href="/methodology/">Our methodology</a> explains why we leave a cell empty rather than guess.</p>
    <p>If you have opened Holofoil packs and can share a full pack's card pool with its rates and values, that would be enough to calculate one.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/guides/withdrawals/">Which platforms actually pay out money, and which pay credit</a></li>
    <li><a href="/compare/?p=holofoil,rare-candy,gotya">Compare Holofoil, Rare Candy and Gotya side by side</a></li>
    <li><a href="/platforms/rare-candy/">Rare Candy, the other platform whose currency has no cash value</a></li>
    <li><a href="/guides/buyback-rates/">What a 90% buyback is actually worth</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html,
           **{"flags_holofoil": flag_row("holofoil")})

    return pages_written("/platforms/holofoil/", page(
        "/platforms/holofoil/",
        "Holofoil review — credit that cannot be cashed out, and a 30-day vault",
        "Holofoil's §4 says its credit cannot be withdrawn or cashed out at all, and §10 converts vaulted cards to that credit after 30 days. Shipping the card is the only exit.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "Holofoil")],
        updated=UPDATED, structured=faq_ld))


def build_gotya():
    rows = gotya_rows()
    s = gotya_stats()

    pack_rows = "".join(
        '<tr><td class="name">%s</td><td class="num">%s</td>'
        '<td class="num">%s</td><td class="num"><strong>%s</strong></td>'
        '<td class="num"><strong class="%s">%s</strong></td>'
        '<td class="num">%s</td><td class="num">%s</td></tr>'
        % (r["name"], money(r["price"]), money(r["stated"]), money(r["mid"]),
           "pos" if r["ratio_mid"] >= 0.98 else "neg",
           pct(r["ratio_mid"] * 100, 1), pct(r["psum"], 1),
           pct(r["round_trip"] * 100, 1))
        for r in rows)

    def band_table(r):
        body = "".join(
            '<tr><td class="num">%s&ndash;%s</td><td class="num">%s</td>'
            '<td class="num">%s</td></tr>'
            % (money(lo), money(hi), pct(p, 2), money((lo + hi) / 2.0 * p / 100.0))
            for lo, hi, p in r["bands"])
        return (
            '<div class="table-wrap"><table>'
            '<caption>%s, %s &mdash; Gotya&rsquo;s published card-value bands, '
            'collected %s. The last column is each band&rsquo;s contribution to '
            'the midpoint expected value.</caption>'
            '<thead><tr><th scope="col" class="num">Card value</th>'
            '<th scope="col" class="num">Chance</th>'
            '<th scope="col" class="num">Contributes</th></tr></thead>'
            '<tbody>%s</tbody>'
            '<tfoot><tr><th scope="row" class="num">Total</th>'
            '<td class="num">%s</td><td class="num"><strong>%s</strong></td>'
            '</tr></tfoot></table></div>'
            % (r["name"], money(r["price"]), UPDATED, body,
               pct(r["psum"], 1), money(r["mid"])))

    faq_html, faq_ld = faq_block([
        ("Does a Gotya pack really contain its price in card value?",
         "<p>On the paid packs we collected, yes, and slightly more. Gotya's homepage says &ldquo;each pack's expected value equals its price.&rdquo; We took the published value bands from five packs and worked out the midpoint expected value: the four paid packs average %s of their price, and across all five it is %s. The odds on every one sum to exactly 100.0%%. That is a claim that survives checking, which is rare in this category.</p>"
         % (pct(s["paid_avg"] * 100, 1), pct(s["mid_avg"] * 100, 1))),
        ("Is the Gotya free pack worth the same as a paid one?",
         "<p>No, and it is the one place the claim does not hold. The free $10 pack's own published bands work out to %s at midpoints &mdash; about %s below the paid packs. Gotya describes it as &ldquo;the same $10 pack everyone pays for&rdquo; with the &ldquo;same card pool, same published odds,&rdquo; but the odds table on that pack is not the same shape as the paid ones. It is still a free pack and still worth claiming; it is just not the equal of the packs you buy.</p>"
         % (pct(s["free_ratio"] * 100, 1), pct((s["paid_avg"] - s["free_ratio"]) * 100, 0))),
        ("Can you withdraw money from Gotya?",
         "<p>Yes. The standing buyback is 90% of fair market value, credited to your Wallet, which section 20 describes as an internal ledger credit. Section 21 allows withdrawal to a verified bank account held in your own legal name, and Gotya's free-pack page puts the cash-out floor at a $25 balance with payouts &ldquo;within a few business days.&rdquo; The terms themselves state no minimum or maximum figures.</p>"),
        ("What happens if you stop using Gotya?",
         "<p>Your cards are converted to credit. Section 30 says that after 180 consecutive days of inactivity an account becomes dormant, and Gotya may convert Vault Assets to Wallet credit at &ldquo;currently 90% of Fair Market Value at the moment of conversion,&rdquo; after at least two email notices with the first at least 14 days beforehand. No other platform we track has a dormancy clause. There is no ordinary storage deadline, so this is the one clock on the platform &mdash; and it is six months long, with notice.</p>"),
        ("Who operates Gotya?",
         "<p>VBR GROUP LLP, a limited liability partnership registered in England and Wales at 32 Kinburn Street, London SE16 6DW, together with Gotya Collect LLC in Cheyenne, Wyoming. Section 36 puts the agreement under the law of England and Wales, with the English courts having exclusive jurisdiction for business users. That makes Gotya the third non-US-governed platform we track, after <a href=\"/platforms/mintpull/\">MintPull</a> in Hong Kong and <a href=\"/platforms/letsgo/\">LETSGO</a> in Israel.</p>"),
        ("Can you dispute Gotya's card valuation?",
         "<p>Not through any published process. Sections 2 and 14 say Gotya determines fair market value as &ldquo;a good-faith internal estimate&rdquo; using its own methodology, and may disregard data it considers stale, manipulated or unrepresentative. Section 24 lists &ldquo;Disagreement with FMV&rdquo; among the reasons a return will not be accepted. The only route the terms describe is emailing Gotya before starting legal proceedings.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Gotya says the pack is worth its price. We checked five packs, and it is.</h1>
    <p class="lede">Every odds table sums to exactly 100%, the midpoint expected value averages {mid} of the pack price, and the 90% buyback reaches a real bank account. The free pack is the one that falls short of the claim.</p>
    {flags_gotya}
  </div>

  <div class="finding">
    <p class="big">Gotya's homepage says &ldquo;each pack's expected value equals its price.&rdquo; We took the published value bands from {n} packs and worked it out: the {npaid} paid packs average <strong>{paid}</strong> of their price at midpoints. The free $10 pack averages <strong>{free}</strong>. The 90% standing buyback makes the round trip about <strong>{trip}</strong>, which is the best we have measured anywhere.</p>
    <p class="small muted">Collected from gotya.com pack pages and terms on {collected}. Odds are Gotya's own and are recalculated from live vault inventory, so they move.</p>
  </div>

  <h2>The claim, tested</h2>
  <p>Platforms in this category make a lot of claims about value. This is the first one we have been able to test directly against the platform's own published odds on multiple packs, and it is the second platform &mdash; after <a href="/platforms/swishx/">SwishX</a> &mdash; to design packs around a 100% value target rather than a markup.</p>

  <div class="table-wrap">
  <table>
  <caption>Gotya packs: the stated average item value, our midpoint calculation from the published bands, and what a 90% buyback returns, {collected}.</caption>
  <thead><tr>
    <th scope="col">Pack</th><th scope="col" class="num">Price</th>
    <th scope="col" class="num">Gotya's stated average</th>
    <th scope="col" class="num">Our midpoint EV</th>
    <th scope="col" class="num">As % of price</th>
    <th scope="col" class="num">Odds sum</th>
    <th scope="col" class="num">Round trip at 90%</th>
  </tr></thead>
  <tbody>{packs}</tbody>
  </table>
  </div>

  <p>Two things stand out. <strong>Every odds table sums to exactly 100.0%</strong> &mdash; not 100.04%, not 100.64%, which is more than we can say for <a href="/platforms/swishx/">SwishX</a>. And on the paid packs the midpoint expected value comes in slightly <em>above</em> the price rather than below it.</p>

  {band_paid}

  <p>That is a checkable disclosure for a $15 purchase, and it reconciles.</p>

  <h2>The free pack is the exception</h2>
  <p>Gotya's free-pack page describes the offer as &ldquo;the same $10 pack everyone pays for,&rdquo; with the &ldquo;same card pool, same published odds.&rdquo; Its published odds are not the same shape as the paid packs.</p>

  {band_free}

  <p>At midpoints that is <strong>{free}</strong> of the nominal $10, against {paid} on the paid packs. The bottom band starts at $3 where the Rookie Pack's starts at 73% of its price, and the top band is a tenth as likely.</p>

  <p>We are not calling this deceptive. A free pack costing the platform real inventory is reasonably a thinner pack, and Gotya publishes the odds that show it &mdash; which is the opposite of hiding it. But &ldquo;the same $10 pack everyone pays for&rdquo; is a sentence the platform's own odds table does not support, and the fix is to delete the sentence rather than change the pack.</p>

  <h2>The round trip is the best we have measured</h2>
  <p>A buyback rate only means something once you know the pack's expected value and whether the money leaves. Gotya is one of the few platforms where all three are known.</p>

  <div class="table-wrap">
  <table>
  <caption>Round trip across the platforms where the pack EV, the buyback rate and the payout form are all published.</caption>
  <thead><tr><th scope="col">Platform</th><th scope="col" class="num">Pack EV</th><th scope="col" class="num">Buyback</th><th scope="col" class="num">Round trip</th><th scope="col">Form</th></tr></thead>
  <tbody>
    <tr><td class="name">Gotya</td><td class="num">~100.5%</td><td class="num">90%</td><td class="num"><strong class="pos">~90%</strong></td><td>Wallet, then bank at a $25 floor</td></tr>
    <tr><td class="name">SwishX, within 24h</td><td class="num">~101%</td><td class="num">85&ndash;90%</td><td class="num">~88%</td><td>Cash via Stripe</td></tr>
    <tr><td class="name">Courtyard</td><td class="num">95%</td><td class="num">90% advertised, ~85% measured</td><td class="num">~81&ndash;85%</td><td>USDC, unverified</td></tr>
    <tr><td class="name">Packz</td><td class="num">~100%</td><td class="num">90%</td><td class="num">~90%</td><td><strong class="neg">Site credit only</strong></td></tr>
    <tr><td class="name">Rare Candy</td><td class="num">~98&ndash;123%</td><td class="num">Up to 90%</td><td class="num">Not comparable</td><td><strong class="neg">Candy, no cash value</strong></td></tr>
  </tbody>
  </table>
  </div>

  <p>Gotya and Packz land in the same place on the arithmetic and in completely different places in practice: Packz pays site credit that can only buy more packs, Gotya pays into a wallet you can move to your own bank. That single difference is worth more than any rate on this table.</p>

  <h2>What to watch: the 180-day clause</h2>
  <div class="callout danger">
    <h3>Section 30: dormancy</h3>
    <p>After <strong>180 consecutive days of inactivity</strong>, your account becomes dormant and Gotya may convert your Vault Assets to Wallet credit at &ldquo;currently 90% of Fair Market Value at the moment of conversion.&rdquo; Gotya must send at least two email notices, the first at least 14 days before conversion.</p>
    <p>No other platform we track has a dormancy clause. Gotya otherwise has no storage deadline at all &mdash; its free-pack page says there is &ldquo;no deadline&rdquo; for keeping a card in the vault &mdash; so this is the only clock on the platform. Six months with two written warnings is far gentler than <a href="/platforms/pickem/">Pickem's three hours</a>. It is still a mechanism that turns your card into credit while you are not looking, and the 90% is applied at conversion rather than at the pull, so a card that has appreciated is converted at the higher figure and one that has fallen at the lower.</p>
  </div>

  <h2>And the parts that are weaker than the odds</h2>
  <ul>
    <li><strong>English law, Wyoming shell.</strong> The operator is VBR GROUP LLP, registered in England and Wales at 32 Kinburn Street, London, alongside Gotya Collect LLC in Cheyenne, Wyoming. Section 36 puts the agreement under English law. That is the third non-US-governed platform we track. The Wyoming address in section 39 carries the postcode &ldquo;8200,&rdquo; which is not a complete US ZIP code.</li>
    <li><strong>No way to dispute a valuation.</strong> Sections 2 and 14 make FMV &ldquo;a good-faith internal estimate&rdquo; by Gotya's own methodology, and section 24 lists &ldquo;Disagreement with FMV&rdquo; as a reason a return will not be accepted. Every figure on this page rests on a number only Gotya sets.</li>
    <li><strong>The terms promise less than the footer.</strong> The site footer says &ldquo;Odds published on every pack page.&rdquo; Section 13 says Gotya &ldquo;may display&rdquo; probability brackets and expected value, and that odds may update, be rounded, be delayed or become unavailable. The practice we observed is better than the contract requires, which is the right way round &mdash; but the contract is what binds.</li>
    <li><strong>The odds move.</strong> Every pack page says the odds are &ldquo;calculated in real-time from the live vault inventory.&rdquo; Our figures describe {collected}; they are not a commitment Gotya has made about tomorrow.</li>
  </ul>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>VBR GROUP LLP, a limited liability partnership of England and Wales, 32 Kinburn Street, London SE16 6DW; with Gotya Collect LLC, Cheyenne, Wyoming (&sect;&sect;0, 3, 39)</td></tr>
    <tr><th scope="row">Governing law</th><td><strong class="neg">England and Wales</strong> (&sect;36); English courts have exclusive jurisdiction for business users; no arbitration clause</td></tr>
    <tr><th scope="row">Categories</th><td>Pok&eacute;mon, One Piece, baseball, football, soccer</td></tr>
    <tr><th scope="row">Packs</th><td>10 listed, {minp}&ndash;$100; {n} collected in full</td></tr>
    <tr><th scope="row">Cards</th><td>One professionally graded card per pack, vaulted and insured</td></tr>
    <tr><th scope="row">Odds</th><td><strong class="pos">Value bands with percentages on every pack page</strong>, summing to exactly 100% on all {n}; recalculated in real time from vault inventory (&sect;13)</td></tr>
    <tr><th scope="row">Stated EV</th><td>&ldquo;Average item value&rdquo; posted per pack; homepage says expected value equals price</td></tr>
    <tr><th scope="row">Buyback</th><td>Standing offer at 90% of FMV, credited to the Wallet (&sect;17); the percentage may change</td></tr>
    <tr><th scope="row">Withdrawals</th><td>To a verified bank account in your own legal name (&sect;21); $25 cash-out floor per the free-pack page; no figures in the terms</td></tr>
    <tr><th scope="row">Marketplace</th><td>0% marketplace fees, per the homepage</td></tr>
    <tr><th scope="row">Storage</th><td>No deadline; but 180 days' inactivity triggers conversion to credit (&sect;30)</td></tr>
    <tr><th scope="row">FMV</th><td>&ldquo;A good-faith internal estimate&rdquo; (&sect;&sect;2, 14); no dispute process; returns refused for &ldquo;Disagreement with FMV&rdquo; (&sect;24)</td></tr>
    <tr><th scope="row">Free pack</th><td>One per person, 18+, phone and email verified, no deposit; shipping unlocks after a first deposit</td></tr>
    <tr><th scope="row">Age</th><td>18+ (&sect;4)</td></tr>
    <tr><th scope="row">Restricted</th><td>Cuba, Iran, North Korea, Syria, Crimea, Donetsk and Luhansk (&sect;4). <strong>No US state restrictions published</strong></td></tr>
  </tbody>
  </table>
  </div>

  <div class="callout">
    <h3>Why this page has no rating</h3>
    <p>Gotya publishes enough to calculate with, and the calculation supports its own headline claim &mdash; which is more than almost any platform here can say. What is still missing is the same thing missing everywhere: nobody has checked whether a platform's stated card values match real sold prices. On a platform whose entire proposition is that the pack contains its price in card value, that question decides everything, and until it is answered a score would imply a precision we do not have. <a href="/methodology/">Our methodology</a> explains why.</p>
    <p>If you have opened Gotya packs and can compare a pulled card's stated FMV against a comparable completed sale, that is the measurement we want.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/compare/?p=gotya,swishx,courtyard">Compare Gotya, SwishX and Courtyard side by side</a></li>
    <li><a href="/platforms/swishx/">SwishX, the other platform built to a 100% value target</a></li>
    <li><a href="/guides/bonus-offers/">Bonus offers ranked by what they are actually worth</a></li>
    <li><a href="/guides/withdrawals/">Who pays real money and who pays credit</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html, packs=pack_rows, n=s["n"],
           npaid=s["n_paid"], mid=pct(s["mid_avg"] * 100, 1),
           paid=pct(s["paid_avg"] * 100, 1), free=pct(s["free_ratio"] * 100, 1),
           trip=pct(s["trip_avg"] * 100, 0), minp=money(15.00),
           band_paid=band_table(rows[1]), band_free=band_table(rows[0]),
           **{"flags_gotya": flag_row("gotya")})

    ld = [faq_ld, jsonld({
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "Gotya published pack odds and expected values",
        "description": "Published card-value bands, stated average item values and derived expected values for %d Gotya packs, collected %s." % (s["n"], UPDATED),
        "url": BASE_URL + "/platforms/gotya/",
        "creator": {"@type": "Organization", "name": SITE_NAME},
        "license": "https://creativecommons.org/licenses/by/4.0/",
    })]

    return pages_written("/platforms/gotya/", page(
        "/platforms/gotya/",
        "Gotya review — does the pack really contain its price in card value?",
        "Gotya says each pack's expected value equals its price. We collected five packs: the odds sum to exactly 100% and the claim holds, averaging 100.5%. The free pack is the exception.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "Gotya")],
        updated=UPDATED, structured=ld))


def build_triumph():
    faq_html, faq_ld = faq_block([
        ("Does Rips by Triumph really have a 100% buyback guarantee?",
         "<p>Its FAQ headlines one. Its terms do not contain one. The FAQ is headed &ldquo;100% BUYBACK GUARANTEE&rdquo; and promises buyback at the fair market value in effect at purchase for at least seven days. Section 5.5 of the Terms of Use says Triumph &ldquo;is under no obligation to&rdquo; offer a Return, that Returns are final, and that Triumph may offer or end them at any time. The FAQ also reserves the right to change the guarantee on seven days' notice. Those are not the same promise, and the terms are the document that governs.</p>"),
        ("Can you withdraw money from Rips by Triumph?",
         "<p>Yes, and the rails are specific: debit card, bank account, or PayPal and Venmo subject to availability. The minimum is $6. Triumph may limit you to &ldquo;no more than $10,000 in withdrawals in any single day&rdquo; at its discretion, and Venmo is capped at &ldquo;no more than $4,000 per rolling twenty-four (24) hours.&rdquo; Section 6.3 says withdrawals process &ldquo;within two weeks of the request&rdquo; while the FAQ says instant withdrawals average about ten minutes. An instant-withdrawal fee applies; the amount is not published.</p>"),
        ("How long can you keep a card on Rips by Triumph?",
         "<p>Seven days. Section 5.3 states, in capitals, &ldquo;YOU MAY ONLY STORE A COLLECTIBLE FOR A MAXIMUM OF SEVEN DAYS.&rdquo; After that it becomes a Return at Triumph's discretion and you are credited the FMV as of when you received it. Triumph gives at least 24 hours' notice by push notification and may extend the deadline. Promotional cards are different: they carry no buyback value at all and may simply be removed after seven days unless shipped.</p>"),
        ("Does Rips by Triumph publish pack odds?",
         "<p>No. Section 5.2.1 requires a pack to show its producer, series or type, cost and number of collectibles, and says other details such as the chance of a given value tier &ldquo;may be&rdquo; provided. No figures appear anywhere public. The same section warns, in capitals, that &ldquo;THE DISTRIBUTION BETWEEN RANGES MAY NOT (AND IS LIKELY NOT TO BE) EQUAL.&rdquo; With no prices and no rates published, no expected value can be calculated.</p>"),
        ("Where is Rips by Triumph not available?",
         "<p>Nevada. Section 2.3 defines Eligible Locations as &ldquo;currently the United States except the State of Nevada,&rdquo; and Triumph's own help article confirms it. Three further states &mdash; Illinois, Utah and North Carolina &mdash; have the 50/50 pack feature restricted rather than the platform as a whole. That is the most detailed state disclosure of any platform we track, and it is on our <a href=\"/legal/\">by-state page</a>.</p>"),
        ("Who operates Rips by Triumph?",
         "<p>The Terms of Use name Triumph TCG, LLC, trading as &ldquo;Rips by Triumph,&rdquo; under Delaware law. The Google Play listing gives the developer as Triumph Labs, Inc., at &ldquo;2093 Philadelphia Pike Ste 4204 Claymont, DE 19703-2424.&rdquo; Disputes go to individual AAA arbitration, by default in San Francisco, with a $225 consumer filing fee, a class-action waiver and a 60-day informal resolution step first.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Rips by Triumph: the biggest platform here, and its terms are MintPull's</h1>
    <p class="lede">A million-plus installs, a &ldquo;100% BUYBACK GUARANTEE&rdquo; in the FAQ, and a &sect;5.5 saying Triumph is under no obligation to buy anything back. Its clauses match MintPull's word for word, section number for section number.</p>
    {flags_triumph}
  </div>

  <div class="finding">
    <p class="big">The FAQ is headed &ldquo;100% BUYBACK GUARANTEE.&rdquo; Section 5.5 of the Terms of Use says Triumph &ldquo;is under no obligation to&rdquo; offer a Return and may offer or end Returns at any time. The FAQ separately reserves the right to change the guarantee on seven days' notice, by editing the FAQ.</p>
    <p class="small muted">Read from docs.triumpharcade.com, the Triumph help centre and the Google Play listing on {collected}. No pack prices or odds are published anywhere public.</p>
  </div>

  <h2>The largest platform on this site</h2>
  <p>Scale first, because it changes what the rest of this page means. The Google Play listing shows <strong>1,000,000+ installs</strong> and about 64,500 reviews averaging 4.5. <a href="/platforms/letsgo/">LETSGO</a>, the next largest we have measured, shows 100,000+. Triumph is an order of magnitude bigger than anything else here, which means the terms below apply to more people than every other platform on this site combined.</p>

  <p>It is also, in several respects, better documented than most. It names its entity, publishes a state-by-state restriction list, specifies its withdrawal rails and caps, and requires identity verification with a liveness test. Those are real disclosures and we are not going to pretend otherwise.</p>

  <h2>The guarantee that the terms do not contain</h2>
  <div class="table-wrap">
  <table class="clauses">
  <caption>Rips by Triumph's buyback, as described in each document, {collected}.</caption>
  <thead><tr><th scope="col">Source</th><th scope="col">What it says</th></tr></thead>
  <tbody>
    <tr><td class="name">FAQ heading</td><td>&ldquo;100% BUYBACK GUARANTEE&rdquo;</td></tr>
    <tr><td class="name">FAQ body</td><td>Buyback at the FMV in effect at purchase, for at least seven days after the card enters Inventory &mdash; changeable on seven days' notice by updating the FAQ</td></tr>
    <tr><td class="name">Google Play listing</td><td>Sold cards are priced at &ldquo;100% fair market value&rdquo;</td></tr>
    <tr><td class="name">Terms of Use &sect;5.5</td><td><strong class="neg">Triumph &ldquo;is under no obligation to&rdquo; offer a Return; Returns are final; Triumph may offer or end them at any time</strong></td></tr>
  </tbody>
  </table>
  </div>

  <p>We have written this page before, about <a href="/platforms/fast-rips/">Fast Rips</a> and <a href="/platforms/letsgo/">LETSGO</a>. The pattern is the same: a confident number in the marketing, a discretionary clause in the contract, and nothing reconciling them.</p>

  <p>In fairness to Triumph, a discretionary clause is not evidence that the buyback fails in practice, and 64,500 reviews at 4.5 stars suggests it generally works. The point is narrower and still worth making: <strong>the word &ldquo;guarantee&rdquo; describes something the governing document declines to guarantee.</strong> If Triumph intends to honour it, writing it into section 5.5 would cost nothing.</p>

  <h2>The clauses are MintPull's, verbatim</h2>
  <p>This is the part we did not expect. Reading Triumph's terms against <a href="/platforms/mintpull/">MintPull's</a>, which we published two days ago, the overlap is not thematic. It is textual, and it runs through the same section numbers.</p>

  <div class="table-wrap">
  <table class="clauses">
  <caption>Clauses appearing in both platforms' Terms of Use.</caption>
  <thead><tr><th scope="col">&sect;</th><th scope="col">Rips by Triumph</th><th scope="col">MintPull</th></tr></thead>
  <tbody>
    <tr><td class="name">5.3</td><td>&ldquo;YOU MAY ONLY STORE A COLLECTIBLE FOR A MAXIMUM OF SEVEN DAYS&rdquo;</td><td>&ldquo;YOU MAY ONLY STORE A COLLECTIBLE FOR A MAXIMUM OF SEVEN DAYS&rdquo;</td></tr>
    <tr><td class="name">5.2</td><td>&ldquo;THE DISTRIBUTION BETWEEN RANGES MAY NOT (AND IS LIKELY NOT TO BE) EQUAL&rdquo;</td><td>&ldquo;THE DISTRIBUTION BETWEEN RANGES MAY NOT (AND LIKELY IS NOT) BE EQUAL&rdquo;</td></tr>
    <tr><td class="name">5.2</td><td>Pack shows producer, series or type, cost, number of collectibles; other details &ldquo;may be&rdquo; shown</td><td>Packs may show the producer, series, cost and item count; odds details may also be shown</td></tr>
    <tr><td class="name">5.4</td><td>&ldquo;The FMV that Triumph uses may not match published market values&rdquo;; &ldquo;subject to change at any time&rdquo;</td><td>&ldquo;May not match published market values&rdquo;; &ldquo;subject to change at any time&rdquo;</td></tr>
    <tr><td class="name">5.5</td><td>Returns are final; Triumph under no obligation to offer them</td><td>Returns credited as additional pack purchase credits</td></tr>
    <tr><td class="name">&mdash;</td><td>Eligible Locations: the United States except Nevada</td><td>Restricted: Nevada, and outside the United States</td></tr>
  </tbody>
  </table>
  </div>

  <p>Same capitalised sentences, same section numbering, same Nevada carve-out, same FMV disclaimer. Two platforms that share no branding, no website and no stated corporate link are working from one document.</p>

  <div class="callout">
    <h3>What this does and does not mean</h3>
    <p>It does <strong>not</strong> establish that Triumph and MintPull are the same company, and we are not saying they are. Triumph TCG, LLC operates under Delaware law; MintPull is Arcane Answers Studio Limited in Hong Kong. A shared template can come from common counsel, a vendor's boilerplate, or one operator copying another's public terms.</p>
    <p>It does mean something for readers. When you see &ldquo;seven-day storage limit&rdquo; and &ldquo;proprietary FMV that may not match published market values&rdquo; on a third platform, that is not independent convergence on fair terms &mdash; it is one document propagating. The clauses that favour the operator are the ones being copied, and they are spreading faster than the disclosure practices on <a href="/platforms/swishx/">SwishX</a> or <a href="/platforms/courtyard/">Courtyard</a>.</p>
  </div>

  <h2>Two places the documents contradict themselves</h2>
  <p>Separate from the guarantee, we found two internal inconsistencies while reading. Neither is severe. Both are the kind of thing that gets fixed once someone points at it.</p>

  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Tax threshold</th><td>The FAQ says withdrawals pause once you exceed <strong>$600</strong> in a year until tax forms are completed. Section 6.3 of the terms says tax forms may be required for withdrawals over <strong>$2,000</strong> in a calendar year</td></tr>
    <tr><th scope="row">Shipping insurance</th><td>One FAQ answer says Rips pays the insurance when FMV is over $1,000. Another says the buyer must purchase it. Insurance is optional below $1,000 and required at or above it</td></tr>
    <tr><th scope="row">Withdrawal speed</th><td>&sect;6.3: &ldquo;within two weeks of the request.&rdquo; FAQ: instant withdrawals average about ten minutes</td></tr>
  </tbody>
  </table>
  </div>

  <p>That last pairing is familiar &mdash; <a href="/platforms/packed/">Packed</a> has the same ten-minutes-versus-two-weeks split. The terms set an outer bound and the FAQ describes the norm, which is defensible, but a reader deciding whether to leave a balance on the platform is entitled to see both numbers in the same place.</p>

  <h2>What it does disclose well</h2>
  <ul>
    <li><strong>State restrictions, specifically.</strong> Nevada is excluded outright, and Illinois, Utah and North Carolina have the 50/50 pack feature restricted rather than the whole platform. That is the most granular state disclosure we have found anywhere in this category, and most platforms publish nothing at all.</li>
    <li><strong>Withdrawal mechanics, with numbers.</strong> $6 minimum, up to $10,000 a day at Triumph's discretion, Venmo capped at $4,000 per rolling 24 hours, four payout rails named. Compare <a href="/platforms/fast-rips/">Fast Rips</a>, which advertises cash and documents none of this.</li>
    <li><strong>A named entity and a real address.</strong> Triumph TCG, LLC in the terms; Triumph Labs, Inc. at a Claymont, Delaware address on Google Play. <a href="/platforms/letsgo/">LETSGO</a> names nothing on its own site at all.</li>
    <li><strong>Identity verification is described honestly</strong> &mdash; 18+, government ID, a liveness test, usually 24 hours, with manual review and possible notarised documents if it fails.</li>
  </ul>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>Triumph TCG, LLC d/b/a Rips by Triumph (terms); Triumph Labs, Inc., 2093 Philadelphia Pike Ste 4204, Claymont, DE 19703 (Google Play)</td></tr>
    <tr><th scope="row">Scale</th><td><strong>1,000,000+ Google Play installs</strong>; ~64,500 reviews averaging 4.5 &mdash; the largest platform we track</td></tr>
    <tr><th scope="row">Governing law</th><td>Delaware (&sect;14.1); AAA individual arbitration, San Francisco by default, $225 consumer filing fee, class waiver, 60-day informal step (&sect;14)</td></tr>
    <tr><th scope="row">Pack prices</th><td>Not published</td></tr>
    <tr><th scope="row">Odds</th><td>Not published. &sect;5.2.1 requires producer, series, cost and item count; tier chances &ldquo;may be&rdquo; shown</td></tr>
    <tr><th scope="row">Buyback</th><td>FAQ: 100% of the FMV in effect at purchase, seven days. &sect;5.5: no obligation to offer Returns at all</td></tr>
    <tr><th scope="row">Promotional cards</th><td><strong class="neg">No buyback value</strong>; may be removed after seven days unless shipped</td></tr>
    <tr><th scope="row">FMV</th><td>&ldquo;Realtime sales statistics&rdquo; and &ldquo;a proprietary system&rdquo;; &ldquo;may not match published market values&rdquo;; no dispute process described (&sect;5.4)</td></tr>
    <tr><th scope="row">Storage</th><td>&ldquo;YOU MAY ONLY STORE A COLLECTIBLE FOR A MAXIMUM OF SEVEN DAYS&rdquo; (&sect;5.3), then auto-returned at the locked FMV, with 24 hours' push notice</td></tr>
    <tr><th scope="row">Withdrawals</th><td>Debit, bank, PayPal or Venmo; $6 minimum; up to $10,000/day at discretion; Venmo $4,000 per rolling 24h; instant-withdrawal fee, amount not published</td></tr>
    <tr><th scope="row">Shipping</th><td>Buyer pays shipping, tracking and sales tax, debited from balance before release; insurance optional under $1,000 FMV, required at $1,000+</td></tr>
    <tr><th scope="row">Verification</th><td>18+, government ID and liveness test before any withdrawal or shipment</td></tr>
    <tr><th scope="row">Age</th><td>18+ in the terms (&sect;2.1(a)); the Google Play rating is Mature 17+</td></tr>
    <tr><th scope="row">States</th><td><strong>Not available in Nevada</strong>; the 50/50 pack is restricted in Illinois, Utah and North Carolina</td></tr>
  </tbody>
  </table>
  </div>

  <div class="callout danger">
    <h3>If you use Rips by Triumph</h3>
    <p>Mind the seven days. The window is longer than most of this category, but it ends in an automatic sale at a value locked when you pulled the card, not at today's price. Screenshot the FMV at the pull. Verify your identity before you want to ship or withdraw, not after. And treat promotional cards as entertainment only &mdash; they carry no buyback value and can be removed.</p>
    <p>If this has stopped feeling like fun, free and confidential help is available: call or text <strong>1-800-GAMBLER</strong>.</p>
  </div>

  <div class="callout">
    <h3>Why this page has no rating</h3>
    <p>No pack prices and no odds are published anywhere public, so no expected value can be calculated &mdash; three of our five inputs are unavailable. The buyback is stated two different ways in two of the platform's own documents, so the fourth cannot be scored with confidence either. <a href="/methodology/">Our methodology</a> explains why we leave a cell empty rather than guess.</p>
    <p>We have written to Triumph asking whether &sect;5.5 or the FAQ heading governs, and will publish the answer. If you have in-app screenshots of pack prices or tier odds, we would like to see them.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/platforms/mintpull/">MintPull, whose terms these are</a></li>
    <li><a href="/compare/?p=triumph,mintpull,swishx">Compare Triumph, MintPull and SwishX side by side</a></li>
    <li><a href="/legal/">Where each platform is restricted, state by state</a></li>
    <li><a href="/guides/buyback-rates/">What a buyback is actually worth, across every platform</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html,
           **{"flags_triumph": flag_row("triumph")})

    return pages_written("/platforms/triumph/", page(
        "/platforms/triumph/",
        "Rips by Triumph review — a 100% guarantee its terms do not contain",
        "Rips by Triumph headlines a 100% buyback guarantee; §5.5 of its terms says it is under no obligation to offer one. Its clauses match MintPull's verbatim.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"),
                (None, "Rips by Triumph")],
        updated=UPDATED, structured=faq_ld))


def build_swishx():
    rows = swishx_rows()
    s = swishx_stats()

    ev_rows = "".join(
        '<tr><td class="name">%s</td><td class="num">%s</td>'
        '<td class="num">%s</td><td class="num"><strong>%s</strong></td>'
        '<td class="num">%s</td><td class="num">%s</td>'
        '<td class="num"><strong class="neg">%s</strong></td></tr>'
        % (r["name"], money(r["price"]), money(r["stated"]),
           pct(r["posted_ratio"] * 100, 1), pct(r["calc_ratio"] * 100, 1),
           "%s&ndash;%s" % (pct(r["fast_lo"] * 100, 0), pct(r["fast_hi"] * 100, 0)),
           "%s&ndash;%s" % (pct(r["slow_lo"] * 100, 0), pct(r["slow_hi"] * 100, 0)))
        for r in rows)

    def tier_table(r):
        body = "".join(
            '<tr><td class="name">%s</td><td class="num">%s&ndash;%s</td>'
            '<td class="num">%s</td><td class="num">%s</td>'
            '<td class="num">%s</td></tr>'
            % (t[0], money(t[1]), money(t[2]), money(t[3]), pct(t[4], 2),
               money(t[3] * t[4] / 100.0))
            for t in r["tiers"])
        return (
            '<div class="table-wrap"><table>'
            '<caption>%s, %s &mdash; SwishX\'s published tiers, target fair '
            'market values and odds, collected %s. The last column is each '
            'tier\'s contribution to the expected value.</caption>'
            '<thead><tr><th scope="col">Tier</th>'
            '<th scope="col" class="num">FMV range</th>'
            '<th scope="col" class="num">Target FMV</th>'
            '<th scope="col" class="num">Odds</th>'
            '<th scope="col" class="num">Contributes</th></tr></thead>'
            '<tbody>%s</tbody>'
            '<tfoot><tr><th scope="row">Total</th><td class="num">&mdash;</td>'
            '<td class="num">&mdash;</td><td class="num">%s</td>'
            '<td class="num"><strong>%s</strong></td></tr></tfoot>'
            '</table></div>'
            % (r["name"], money(r["price"]), UPDATED, body,
               pct(r["psum"], 2), money(r["calc"])))

    faq_html, faq_ld = faq_block([
        ("Does SwishX publish pack odds?",
         "<p>More completely than any platform we track. Every pack page carries each tier's name, a fair market value range, an explicit <em>target</em> FMV, and the odds percentage &mdash; plus a posted expected value for the pack and the named card pool behind each tier, down to the player, year and set. Only <a href=\"/platforms/clutch-packs/\">Clutch Packs</a>, which publishes observed results rather than projections, makes a stronger claim.</p>"),
        ("Is the SwishX expected value accurate?",
         "<p>It checks out against their own numbers. We recomputed the posted expected value from the published target FMVs and odds on five packs and landed within %s of the posted figure every time. That is the first time on this site we have been able to verify a platform's posted EV from its own disclosure. It is not the same as verifying it against real sold prices, which nobody has done for any platform here, including this one.</p>"
         % pct(s["max_gap"] * 100, 1)),
        ("How much does SwishX pay to buy a card back?",
         "<p>The FAQ states it plainly: buyback offers &ldquo;can vary between 85-90% depending on the pack purchased,&rdquo; and after the initial 24-hour window a new offer &ldquo;will vary between 75-80%.&rdquo; Those are published bands rather than a fixed rate, so you cannot know your exact rate before buying, but a published band is more than any other platform here gives you.</p>"),
        ("What happens after 24 hours on SwishX?",
         "<p>Nothing is taken from you. Unlike <a href=\"/platforms/pickem/\">Pickem</a>, <a href=\"/platforms/packed/\">Packed</a> and <a href=\"/platforms/chalkboard/\">Chalkboard</a>, SwishX does not sell your card when the clock runs out. The card stays in your Vault and you can request a fresh buyback offer at any time &mdash; it is just worth less, at 75-80% instead of 85-90%. The deadline costs you about ten points rather than the card.</p>"),
        ("Can you withdraw money from SwishX?",
         "<p>Yes. The FAQ says withdrawals are &ldquo;processed to your linked payout method and verified through Stripe,&rdquo; from the Wallet. That puts SwishX among the minority of platforms we track where buyback proceeds become money rather than credit.</p>"),
        ("Who operates SwishX, and who can use it?",
         "<p>The site names no legal entity &mdash; the footer reads &ldquo;&copy; 2026 SwishX&rdquo; and the FAQ page is marked &ldquo;Powered by Swish Breaks.&rdquo; You must be 18 or older and may hold only one account. No state restrictions are published anywhere we could find.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>SwishX: the pack is worth what you paid. The exit is what costs you.</h1>
    <p class="lede">SwishX posts an expected value on every pack, publishes the odds and target card values behind it, and says packs are &ldquo;designed to a 100% value target.&rdquo; We checked the arithmetic and it holds. Then the buyback takes 12 to 22% back.</p>
    {flags_swishx}
  </div>

  <div class="finding">
    <p class="big">Across the {n} packs we collected, the posted expected value averages <strong>{posted}</strong> of the pack price &mdash; the only platform we track that does not price a margin into the pack. It takes the margin at the other end instead: the FAQ says buybacks &ldquo;can vary between 85-90% depending on the pack purchased,&rdquo; falling to &ldquo;75-80%&rdquo; on a re-quote after 24 hours.</p>
    <p class="small muted">Collected from swishx.co pack pages and FAQ on {collected}. Expected values are SwishX's own, computed from SwishX's own card valuations.</p>
  </div>

  <h2>What they publish</h2>
  <p>Most of this site is an exercise in working out what platforms will not tell you. This page is the opposite problem. SwishX publishes, on every pack page, with no account:</p>
  <ul>
    <li>A <strong>posted expected value</strong> for the pack, in dollars.</li>
    <li>Five tiers, each with a fair market value <strong>range</strong> and an explicit <strong>target</strong> FMV.</li>
    <li>The <strong>odds</strong> for each tier.</li>
    <li>The <strong>named card pool</strong> behind each tier &mdash; player, year, set and grade.</li>
  </ul>

  <p>That last item is rare. <a href="/platforms/fanatics-instant-rips/">Fanatics</a> publishes a checklist with no rates; <a href="/platforms/arena-club/">Arena Club</a> publishes rates with no values. SwishX publishes both, attached to each other.</p>

  {tier_cheap}

  <p>Because the target FMVs are published alongside the odds, the posted expected value is <strong>checkable</strong>. The contributions in the last column sum to the figure at the bottom, and that figure should match what SwishX posts at the top of the page.</p>

  <h2>We checked it on every pack</h2>
  <p>It matches. Recomputing the posted expected value from SwishX's own target FMVs and odds lands within <strong>{gap}</strong> of the posted figure on all {n} packs.</p>

  <div class="table-wrap">
  <table>
  <caption>SwishX packs: posted expected value, our recomputation from the published odds, and what a sell-back actually returns, {collected}.</caption>
  <thead><tr>
    <th scope="col">Pack</th><th scope="col" class="num">Price</th>
    <th scope="col" class="num">Posted EV</th>
    <th scope="col" class="num">Posted as % of price</th>
    <th scope="col" class="num">Our recomputation</th>
    <th scope="col" class="num">Sold back in 24h</th>
    <th scope="col" class="num">Sold back later</th>
  </tr></thead>
  <tbody>{evs}</tbody>
  </table>
  </div>

  <p>This is the first platform on this site whose posted expected value we have been able to verify from its own disclosure. <a href="/platforms/courtyard/">Courtyard</a> posts an expected value too, but does not publish the per-tier card values that would let you rebuild it. That difference matters: a number you can recompute is a commitment, and a number you cannot is a claim.</p>

  <div class="callout">
    <h3>What this does and does not prove</h3>
    <p>It proves SwishX's posted EV is consistent with SwishX's published odds and SwishX's own card valuations. It does not prove those valuations match what the cards actually sell for, and nobody &mdash; us included &mdash; has tested that for any platform in this category. A perfectly consistent expected value built on optimistic FMVs would look exactly like this.</p>
  </div>

  <h2>Where the money is made, in their own words</h2>
  <p>A platform returning 100% of the pack price in card value cannot make money on the pack. SwishX does not hide where it makes it instead. From the FAQ, under &ldquo;How much of what I pay goes into the cards?&rdquo;:</p>

  <blockquote>
    <p>&ldquo;Every pack on SwishX is designed to a 100% value target &mdash; built so the combined fair market value of the cards in its pool matches the price of the pack. The full value of your purchase lives in the cards you can pull, not in a markup on top of them.&rdquo;</p>
  </blockquote>

  <p>And under &ldquo;How is the instant buyback amount determined?&rdquo;:</p>

  <blockquote>
    <p>&ldquo;Buyback offers are set at a defined rate relative to the card's current fair market value &mdash; this can vary between 85-90% depending on the pack purchased. Note that after the initial 24-hour buyback period, you can request a new buyback offer, which will vary between 75-80%.&rdquo;</p>
  </blockquote>

  <p>So the model is explicit: no margin on the pack, a {fastspread} margin on the way out if you sell within a day, and a {slowspread} margin if you sell later. For a buyer who intends to sell everything back, the round trip averages <strong>{fast}</strong> inside the window and <strong>{slow}</strong> outside it.</p>

  <div class="table-wrap">
  <table>
  <caption>Round trip compared: what you get back if you sell every card straight back, across the platforms where both figures are known.</caption>
  <thead><tr><th scope="col">Platform</th><th scope="col" class="num">Pack EV</th><th scope="col" class="num">Buyback</th><th scope="col" class="num">Round trip</th><th scope="col">Form</th></tr></thead>
  <tbody>
    <tr><td class="name">SwishX, within 24h</td><td class="num">~101%</td><td class="num">85&ndash;90%</td><td class="num"><strong class="pos">~88%</strong></td><td>Cash via Stripe</td></tr>
    <tr><td class="name">Courtyard</td><td class="num">95%</td><td class="num">90% advertised, ~85% measured</td><td class="num">~81&ndash;85%</td><td>USDC, unverified</td></tr>
    <tr><td class="name">SwishX, after 24h</td><td class="num">~101%</td><td class="num">75&ndash;80%</td><td class="num">~78%</td><td>Cash via Stripe</td></tr>
    <tr><td class="name">Packz</td><td class="num">~100%</td><td class="num">90%</td><td class="num">~90%</td><td><strong class="neg">Site credit only</strong></td></tr>
    <tr><td class="name">Rare Candy</td><td class="num">~98&ndash;123%</td><td class="num">Up to 90%</td><td class="num">Not comparable</td><td><strong class="neg">Candy, no cash value</strong></td></tr>
    <tr><td class="name">Fanatics Instant Rips</td><td class="num">Not calculable</td><td class="num">84.6% effective</td><td class="num">Unknown</td><td><strong class="neg">Credit only</strong></td></tr>
  </tbody>
  </table>
  </div>

  <p>Read the first two rows together. SwishX returns more on a round trip than Courtyard <em>and</em> pays it in withdrawable money <em>and</em> publishes more of the working. On the numbers each platform discloses about itself, it is the best round trip we have measured.</p>

  <h2>The clock costs points, not the card</h2>
  <p>SwishX has a 24-hour window, which on most of this site is bad news. Here it works differently, and the difference is worth stating precisely.</p>

  <div class="table-wrap">
  <table class="plain">
  <caption>What the deadline actually does.</caption>
  <tbody>
    <tr><th scope="row">Pickem</th><td>3 hours, then <strong class="neg">your card is sold</strong> at Pickem's price</td></tr>
    <tr><th scope="row">Packed</th><td>1 day, then <strong class="neg">the card returns to Packed</strong></td></tr>
    <tr><th scope="row">Chalkboard Pulls</th><td>24 hours, then <strong class="neg">an automatic buyback</strong> is processed</td></tr>
    <tr><th scope="row"><strong>SwishX</strong></th><td>24 hours, then <strong>the offer drops from 85&ndash;90% to 75&ndash;80%</strong>. The card stays yours in the Vault and you can request a new offer whenever you like</td></tr>
  </tbody>
  </table>
  </div>

  <p>That is a materially better design. Falling asleep on SwishX costs you about ten points on an optional transaction. Falling asleep on Pickem costs you the card. We have criticised short windows on five platform pages now; this is the version of the mechanic that does not punish inattention.</p>

  <h2>What we would still push on</h2>
  <ul>
    <li><strong>The buyback is a band, not a rate.</strong> &ldquo;85-90% depending on the pack purchased&rdquo; means the rate is known to SwishX before you buy and not to you. Publishing it per pack, next to the expected value already there, would cost nothing and close the last real gap.</li>
    <li><strong>The odds sum to slightly over 100%.</strong> We measured {minsum} to {maxsum} across the packs. This is almost certainly rounding &mdash; the posted expected values match our recomputation once the rounding is normalised &mdash; but a disclosure this good deserves rates that total exactly 100%.</li>
    <li><strong>The valuations are still SwishX's own.</strong> Every figure on this page, including the ones we verified, rests on SwishX's fair market values. That is the same unresolved question we have raised on all twenty-four platforms.</li>
    <li><strong>No operating company is named.</strong> The footer says &ldquo;&copy; 2026 SwishX&rdquo; and the FAQ is &ldquo;Powered by Swish Breaks.&rdquo; We could not find a legal entity, a registered address or a governing-law clause. For a platform that discloses this much about its product, disclosing nothing about itself is a strange omission.</li>
  </ul>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>Not named; &ldquo;&copy; 2026 SwishX&rdquo;, FAQ marked &ldquo;Powered by Swish Breaks&rdquo;</td></tr>
    <tr><th scope="row">Categories</th><td>Basketball, baseball, football, Pok&eacute;mon, multisport, wax packs</td></tr>
    <tr><th scope="row">Packs</th><td>20 listed, {minp}&ndash;{maxp}; {n} collected in full</td></tr>
    <tr><th scope="row">Odds</th><td><strong class="pos">Per tier, with FMV range, target FMV and the named card pool</strong>, on the open web</td></tr>
    <tr><th scope="row">Posted EV</th><td><strong class="pos">Yes, on every pack</strong>, and it reconciles with the published odds</td></tr>
    <tr><th scope="row">Value target</th><td>&ldquo;Designed to a 100% value target&rdquo;; FAQ says the real figure floats around it, &ldquo;sometimes a touch under (say, 98.5%), sometimes over (say, 102%)&rdquo;</td></tr>
    <tr><th scope="row">Buyback</th><td>85&ndash;90% within 24 hours; 75&ndash;80% on a re-quote afterwards</td></tr>
    <tr><th scope="row">Decision window</th><td>24 hours at the higher rate; <strong class="pos">the card is never taken from you</strong></td></tr>
    <tr><th scope="row">Withdrawals</th><td>From the Wallet to a linked payout method, verified through Stripe</td></tr>
    <tr><th scope="row">Shipping</th><td>Sales tax by shipping address; shipping shown before you confirm; no published rate card</td></tr>
    <tr><th scope="row">Age</th><td>18+, one account per person</td></tr>
    <tr><th scope="row">States</th><td>None published</td></tr>
  </tbody>
  </table>
  </div>

  {tier_dear}

  <div class="callout">
    <h3>Why this page still has no rating</h3>
    <p>It is the best-disclosed platform we have found, and it would score well. But every score on this site is held back by one missing measurement: whether a platform's stated card values match real sold prices. SwishX's whole proposition is that the pack contains its price in card value, which makes that question more load-bearing here than anywhere else, not less. We will not publish a score until someone has tested it. <a href="/methodology/">Our methodology</a> explains why.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/compare/?p=swishx,courtyard,rare-candy">Compare SwishX, Courtyard and Rare Candy side by side</a></li>
    <li><a href="/platforms/courtyard/">Courtyard, the other platform that posts an expected value</a></li>
    <li><a href="/guides/buyback-rates/">What a buyback is actually worth, across every platform</a></li>
    <li><a href="/calculator/">Run these tiers through the pack EV calculator</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html, evs=ev_rows, n=s["n"],
           posted=pct(s["posted_avg"] * 100, 1),
           gap=pct(s["max_gap"] * 100, 1),
           fast=pct(s["fast_avg"] * 100, 0), slow=pct(s["slow_avg"] * 100, 0),
           fastspread="10 to 15%", slowspread="20 to 25%",
           minsum=pct(s["min_oversum"], 2), maxsum=pct(s["max_oversum"], 2),
           minp=money(s["min_price"]), maxp=money(s["max_price"]),
           tier_cheap=tier_table(rows[0]), tier_dear=tier_table(rows[-1]),
           **{"flags_swishx": flag_row("swishx")})

    ld = [faq_ld, jsonld({
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "SwishX published pack odds and posted expected values",
        "description": "Per-tier odds, fair market value ranges, target FMVs and posted expected values for %d SwishX packs, collected %s, with independent recomputation." % (s["n"], UPDATED),
        "url": BASE_URL + "/platforms/swishx/",
        "creator": {"@type": "Organization", "name": SITE_NAME},
        "license": "https://creativecommons.org/licenses/by/4.0/",
    })]

    return pages_written("/platforms/swishx/", page(
        "/platforms/swishx/",
        "SwishX review — posted EV, published odds, and an 85-90% buyback",
        "SwishX posts an expected value on every pack and publishes the odds and card values behind it. We recomputed all five and they match. The margin is in the buyback.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "SwishX")],
        updated=UPDATED, structured=ld))


def build_rarecandy():
    rows = rarecandy_rows()
    s = rarecandy_stats()

    legfloor = []
    for r in rows:
        v = sum(((lo + hi) / 2.0 if lab != "Legendary" else lo) * p / 100.0
                for lab, lo, hi, p in r["bands"])
        legfloor.append(v / r["price"])
    lf_avg = sum(legfloor) / len(legfloor)

    pack_rows = "".join(
        '<tr><td class="name">%s</td><td class="num">%s</td>'
        '<td class="num">%s</td><td class="num"><strong>%s</strong></td>'
        '<td class="num">%s</td><td class="num">%s</td></tr>'
        % (r["name"], money(r["price"]), pct(r["ratio_low"] * 100, 0),
           pct(r["ratio_mid"] * 100, 0), pct(r["ratio_high"] * 100, 0),
           pct(lf * 100, 0))
        for r, lf in zip(rows, legfloor))

    # The widest band on each pack, and what share of EV it carries.
    leg_rows = []
    for r in rows:
        lab, lo, hi, p = [b for b in r["bands"] if b[0] == "Legendary"][0]
        share = ((lo + hi) / 2.0 * p / 100.0) / r["mid"]
        leg_rows.append(
            '<tr><td class="name">%s</td><td class="num">%s</td>'
            '<td class="num">%s&ndash;%s</td><td class="num">%.0f&times;</td>'
            '<td class="num"><strong class="neg">%s</strong></td></tr>'
            % (r["name"], pct(p, 1), money(lo), money(hi), hi / float(lo),
               pct(share * 100, 0)))
    leg_share = sum(
        (([b for b in r["bands"] if b[0] == "Legendary"][0][1]
          + [b for b in r["bands"] if b[0] == "Legendary"][0][2]) / 2.0
         * [b for b in r["bands"] if b[0] == "Legendary"][0][3] / 100.0)
        / r["mid"] for r in rows) / len(rows)

    # Full published bands for the cheapest and dearest packs.
    def band_table(r):
        body = "".join(
            '<tr><td class="name">%s</td><td class="num">%s&ndash;%s</td>'
            '<td class="num">%s</td></tr>'
            % (lab, money(lo), money(hi), pct(p, 1))
            for lab, lo, hi, p in r["bands"])
        return (
            '<div class="table-wrap"><table>'
            '<caption>%s, %s &mdash; Rare Candy\'s published pull rates by '
            'total pack value, collected %s.</caption>'
            '<thead><tr><th scope="col">Band</th>'
            '<th scope="col" class="num">Pack value</th>'
            '<th scope="col" class="num">Chance</th></tr></thead>'
            '<tbody>%s</tbody></table></div>'
            % (r["name"], money(r["price"]), UPDATED, body))

    faq_html, faq_ld = faq_block([
        ("Does Rare Candy publish pack odds?",
         "<p>Yes, and more completely than almost anyone in this category. Every Instapack page carries a &ldquo;Pull Rates by Pack Value&rdquo; table with five bands, a dollar range and a percentage for each, plus a named list of top hits with their values. It is on the open web, with no app and no account needed. All eight packs we collected have rates summing to exactly 100%. Only Courtyard, which posts an exact expected value, discloses more.</p>"),
        ("What is the Rare Candy guaranteed minimum?",
         "<p>Every pack guarantees a floor in Candy if you exchange the whole pack, and on all eight packs we collected it is exactly 50% of the pack price. The $4.99 Deep Blue pack guarantees 250 Candy, the $499.99 Only Slabs pack guarantees 25,000 Candy, and 100 Candy equals $1 throughout. A published, checkable floor is something no other platform we track offers, and it is the most useful single number on the page.</p>"),
        ("Can you withdraw money from Rare Candy?",
         "<p>No. The exchange pays in Candy, and section 8.1 of the terms says Candies &ldquo;have no cash or monetary value and are not redeemable, refundable, or exchangeable for&rdquo; US dollars, cryptocurrency, outside goods or any monetary payment. Section 8.1 also says Rare Candy will not be required to redeem Candies for cash. Candy buys more packs. The only way value leaves Rare Candy is as a physical card you pay to ship.</p>"),
        ("What is Rare Candy's expected value?",
         "<p>Somewhere near break-even, but the published bands cannot pin it down. Taking the midpoint of every band gives an average of %s of the pack price across the eight packs, which cannot be right &mdash; an operator returning more than 100%% on every pack would lose money on every sale. The reason is the Legendary band: it is %.0f times wider than its own floor on average and carries about %s of the midpoint expected value while firing on %s to %s of packs. Valuing Legendary at its floor instead gives %s. The true figure is somewhere in that range and depends entirely on where cards actually sit inside that top band.</p>"
         % (pct(s["mid_avg"] * 100, 0), 13, pct(leg_share * 100, 0),
            pct(s["legendary_min"], 1), pct(s["legendary_max"], 1),
            pct(lf_avg * 100, 0))),
        ("What happens if you do nothing after opening a Rare Candy pack?",
         "<p>You keep the card. The FAQ says you have 48 hours to exchange a card, and if you do not, it is automatically kept in your collection. That makes Rare Candy the second platform we track, after <a href=\"/platforms/poke-collect/\">Poke-Collect</a>, where inaction leaves you holding the card rather than a balance. Pickem, Packed and Chalkboard all sell the card for you when their clocks run out.</p>"),
        ("Who operates Rare Candy?",
         "<p>Rare Candy Auctions, Inc., a Delaware corporation, with the vault in Dallas, Texas. Texas law governs and disputes go to AAA consumer arbitration seated in Dallas County, after at least 60 days of informal negotiation, with a class-action waiver. Instapacks are US-only and exclude Washington state. Rare Candy also runs a card scanner app and a marketplace; Instapacks is one product line of several.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Rare Candy: the best odds disclosure we have found since Courtyard, paid in a currency worth nothing outside the app</h1>
    <p class="lede">Every Instapack publishes five value bands with percentages and a guaranteed 50% floor, on the open web. Then section 8.1 says the Candy it all pays out in has no cash value.</p>
    {flags_rare_candy}
  </div>

  <div class="finding">
    <p class="big">We collected full published pull rates for all {n} Instapacks &mdash; the first new odds dataset we have been able to gather since Courtyard and Packz. Every pack guarantees a floor of exactly 50% of its price. And &sect;8.1 of the terms says Candies &ldquo;have no cash or monetary value and are not redeemable, refundable, or exchangeable for&rdquo; dollars or any monetary payment.</p>
    <p class="small muted">Collected from packs.rarecandy.com and rarecandy.com/terms on {collected}. Rates are Rare Candy's own; card values are Rare Candy's own.</p>
  </div>

  <h2>What they publish, and why it is better than the category norm</h2>
  <p>Ten of the twenty-four platforms we track publish no odds on the open web at all. Rare Candy publishes, on every pack page, with no account and no app: five named bands, a dollar range for each, a percentage for each, a guaranteed floor, and a list of top hits with named cards, grades and values.</p>

  <p>One detail makes this unusually honest. The bands are stated as <strong>total pack value</strong>, not per card. A platform wanting to flatter itself would quote per-card ranges and let the reader assume they stack. Rare Candy quotes the whole pack, which is the number that actually decides whether you are ahead.</p>

  {band_cheap}

  <p>That is a complete, checkable disclosure for a $4.99 purchase. The rates sum to exactly 100%, as they do on all {n} packs.</p>

  <h2>What it works out to</h2>
  <p>Here is every Instapack, with the expected value as a percentage of the pack price. We give three estimates because one number would be misleading.</p>

  <div class="table-wrap">
  <table>
  <caption>Rare Candy Instapacks: expected pack value as a share of pack price, from the published bands, {collected}.</caption>
  <thead><tr>
    <th scope="col">Pack</th><th scope="col" class="num">Price</th>
    <th scope="col" class="num">All bands at floor</th>
    <th scope="col" class="num">All at midpoint</th>
    <th scope="col" class="num">All at ceiling</th>
    <th scope="col" class="num">Top band at floor</th>
  </tr></thead>
  <tbody>{packs}</tbody>
  </table>
  </div>

  <p>The midpoint column averages <strong>{mid}</strong>, and that cannot be true. A platform returning more than the pack price on every pack, on average, loses money on every sale. So the midpoint assumption is wrong here, and it is worth understanding exactly why, because the same flaw affects every value-range disclosure in this category.</p>

  <h2>The problem is the top band</h2>
  <p>Four of the five bands on each pack are narrow and well behaved. The Legendary band is not.</p>

  <div class="table-wrap">
  <table>
  <caption>The Legendary band on each pack: how often it fires, how wide it is, and how much of the midpoint expected value it carries.</caption>
  <thead><tr>
    <th scope="col">Pack</th><th scope="col" class="num">Chance</th>
    <th scope="col" class="num">Band</th><th scope="col" class="num">Width</th>
    <th scope="col" class="num">Share of EV</th>
  </tr></thead>
  <tbody>{legs}</tbody>
  </table>
  </div>

  <p><strong>A band that fires on {legmin} to {legmax} of packs carries about {legshare} of the entire midpoint expected value, and it spans a range eleven times wide on average.</strong> On the Boosted Pack the Legendary band runs from $88 to $2,251 &mdash; twenty-six times. Where cards actually sit inside that range decides everything, and it is the one thing not published.</p>

  <p>Value the Legendary band at its floor and keep the midpoint everywhere else, and the average falls to <strong>{lf}</strong> &mdash; a touch under break-even, which is what you would expect a commercial pack to be. That is our best estimate, and it is an estimate, not a measurement.</p>

  <div class="callout">
    <h3>This is the midpoint problem, stated plainly</h3>
    <p>Every expected value on this site that comes from value ranges rather than exact odds &mdash; <a href="/platforms/packz/">Packz</a> included &mdash; rests on assuming cards sit in the middle of their band. Rare Candy's data shows how badly that assumption can fail when one band is wide and rare. <a href="/platforms/mintpull/">MintPull's terms</a> warn about exactly this, in capitals: &ldquo;THE DISTRIBUTION BETWEEN RANGES MAY NOT (AND LIKELY IS NOT) BE EQUAL.&rdquo;</p>
    <p>The fix is not for us to guess better. It is for platforms to publish the distribution inside the band, or an expected value, as <a href="/platforms/courtyard/">Courtyard</a> does.</p>
  </div>

  <h2>The guaranteed floor is real, and nobody else offers one</h2>
  <p>Every Instapack page carries a guarantee: exchange the whole pack and you receive a stated minimum in Candy. We checked all {n} packs and the figure is exactly 50% of the pack price every time, with 100 Candy equal to $1 throughout.</p>

  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Deep Blue, $4.99</th><td>Guaranteed 250 Candy = $2.50 = <strong>50%</strong></td></tr>
    <tr><th scope="row">Iconic Legends, $24.99</th><td>Guaranteed 1,250 Candy = $12.50 = <strong>50%</strong></td></tr>
    <tr><th scope="row">Modern Collector Gallery, $249.99</th><td>Guaranteed 12,500 Candy = $125 = <strong>50%</strong></td></tr>
    <tr><th scope="row">Only Slabs, $499.99</th><td>Guaranteed 25,000 Candy = $250 = <strong>50%</strong></td></tr>
  </tbody>
  </table>
  </div>

  <p>No other platform we track publishes a floor at all. <a href="/platforms/crown-rips/">Crown Rips</a> discloses a per-pack minimum pull value, which is the closest thing, and its floor is far lower in proportional terms. A guaranteed 50% means the worst case is knowable before you pay, which is genuinely more than the category offers.</p>

  <p>It is a floor in Candy, though, which brings us to the part that matters most.</p>

  <h2>Candy is not money, and the terms say so</h2>
  <div class="callout danger">
    <h3>&sect;8.1 of the Rare Candy terms</h3>
    <p>Candies &ldquo;have no cash or monetary value and are not redeemable, refundable, or exchangeable for&rdquo; US dollars, cryptocurrency, outside goods, or any monetary payment. Rare Candy will not be &ldquo;required to redeem Candies for cash or any monetary equivalent.&rdquo;</p>
  </div>

  <p>So the exchange, described in the FAQ as a trade-in &ldquo;worth up to 90% of the card's market value,&rdquo; pays in a currency that only buys more packs. This puts Rare Candy in the same group as <a href="/platforms/packz/">Packz</a>, <a href="/platforms/fanatics-instant-rips/">Fanatics</a>, <a href="/platforms/fast-rips/">Fast Rips</a> and <a href="/platforms/mintpull/">MintPull</a> &mdash; five of twenty-four platforms where buyback proceeds cannot become money.</p>

  <p>Note the phrasing too: section 3 defines the Exchange Price as &ldquo;calculated <em>up to</em> 90% of the Item's Fair Market Value.&rdquo; That is the same open-ended wording we flagged on <a href="/platforms/letsgo/">LETSGO</a>, and it means 90% is a ceiling rather than a rate.</p>

  <p>What you <em>can</em> take out is the card. Shipping runs $9.99 for 1&ndash;10 cards, $17.99 for 11&ndash;25 and $32.99 for 26&ndash;50, with most orders shipping within 10 business days. On a $4.99 pack, taking delivery costs twice the pack.</p>

  <h2>Three things it does better than almost anyone</h2>
  <ul>
    <li><strong>The clock ends in your favour.</strong> You have 48 hours to exchange; do nothing and the card is kept in your collection. Only <a href="/platforms/poke-collect/">Poke-Collect</a> also defaults to you keeping the card. Pickem, Packed and Chalkboard all sell it for you.</li>
    <li><strong>You keep legal title.</strong> Section 9.2 says title to the card remains with you, with Rare Candy holding it as bailee in its Dallas vault, and storage is currently free. No other platform we have read states this. A card you own outright is a different asset from a balance on a platform's books.</li>
    <li><strong>The terms admit their own limits.</strong> Section 6.2 calls Rare Candy's valuations &ldquo;inherently subjective&rdquo; and says they are not appraisals or guarantees. Section 4.2 declines to warrant that the published card list is accurate. We would rather a platform publish numbers and be candid about their status than publish nothing.</li>
  </ul>

  <h2>And one defect worth fixing</h2>
  <p>The arbitration clause in section 18.1 requires a user to send a Notice of Dispute before arbitrating. The address it must be sent to is an unfilled template placeholder: <strong>&ldquo;[insert physical or electronic mailing address]&rdquo;</strong>. A second bracketed placeholder appears in the same section.</p>

  <p>That is almost certainly an oversight rather than anything deliberate, and the practical effect is small because a user can contact support. But it is the gate to the only dispute process the contract provides, and it currently points nowhere. It belongs on this page for the same reason the rest does: it is what the document actually says.</p>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>Rare Candy Auctions, Inc., a Delaware corporation (&sect;1); vault in Dallas, Texas (&sect;9.1)</td></tr>
    <tr><th scope="row">Governing law</th><td>Texas (&sect;17); AAA consumer arbitration in Dallas County, 60 days' informal negotiation first, class-action waiver (&sect;18)</td></tr>
    <tr><th scope="row">Categories</th><td>Pok&eacute;mon, Magic: The Gathering, Lorcana, One Piece, Gundam</td></tr>
    <tr><th scope="row">Packs</th><td>{n} collected, {minp}&ndash;{maxp}; priced in dollars or Candy at 100 Candy = $1</td></tr>
    <tr><th scope="row">Odds</th><td>Five value bands per pack with percentages, on the open web; a &ldquo;Pack Print Run&rdquo; fixes contents at print with a unique ID (&sect;4.2)</td></tr>
    <tr><th scope="row">Guaranteed floor</th><td><strong class="pos">50% of pack price in Candy</strong>, on every pack we checked</td></tr>
    <tr><th scope="row">Exchange</th><td>&ldquo;Calculated up to 90%&rdquo; of FMV (&sect;3), paid in Candy; no additional exchange fees</td></tr>
    <tr><th scope="row">Candy</th><td><strong class="neg">No cash value; not redeemable for money</strong> (&sect;8.1). Buys more packs only</td></tr>
    <tr><th scope="row">Decision window</th><td>48 hours; do nothing and the card is kept in your collection</td></tr>
    <tr><th scope="row">Vault</th><td>Free at present; title stays with you, Rare Candy as bailee (&sect;9.2); report discrepancies within 30 days (&sect;9.3)</td></tr>
    <tr><th scope="row">Shipping</th><td>$9.99 for 1&ndash;10 cards, $17.99 for 11&ndash;25, $32.99 for 26&ndash;50; most orders within 10 business days; US only</td></tr>
    <tr><th scope="row">Age</th><td>18+ (&sect;2)</td></tr>
    <tr><th scope="row">States</th><td><strong>Excludes Washington</strong>, plus any others Rare Candy designates (&sect;2.1)</td></tr>
  </tbody>
  </table>
  </div>

  <div class="callout">
    <h3>Why this page has no rating</h3>
    <p>For once, the missing piece is not disclosure. Rare Candy publishes enough to calculate with, and we have. What we cannot do is pin the expected value inside the {lf}&ndash;{mid} range the bands allow, because the distribution inside the Legendary band is not published; and we have not tested whether its stated card values match real sold prices, which is the measurement that would make any of these figures mean something.</p>
    <p>If you have opened Instapacks and can share what you pulled against what the pack cost, that is the data that would close the gap. <a href="/methodology/">Our methodology</a> explains why we publish a range rather than a single number.</p>
  </div>

  {band_dear}

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/calculator/">Run these bands through the pack EV calculator yourself</a></li>
    <li><a href="/platforms/courtyard/">Courtyard, the only platform that posts an exact expected value</a></li>
    <li><a href="/platforms/packz/">Packz, the other platform publishing full value-band odds</a></li>
    <li><a href="/compare/?p=rare-candy,courtyard,packz">Compare Rare Candy, Courtyard and Packz side by side</a></li>
  </ul>
</div>
""".format(collected=UPDATED, faq=faq_html, packs=pack_rows,
           legs="".join(leg_rows), n=s["n"],
           mid=pct(s["mid_avg"] * 100, 0), lf=pct(lf_avg * 100, 0),
           legshare=pct(leg_share * 100, 0),
           legmin=pct(s["legendary_min"], 1), legmax=pct(s["legendary_max"], 1),
           minp=money(s["min_price"]), maxp=money(s["max_price"]),
           band_cheap=band_table(rows[0]), band_dear=band_table(rows[-1]),
           **{"flags_rare_candy": flag_row("rare-candy")})

    ld = [faq_ld, jsonld({
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "Rare Candy Instapacks published pull rates",
        "description": "Published value-band pull rates, guaranteed floors and derived expected values for %d Rare Candy Instapacks, collected %s." % (s["n"], UPDATED),
        "url": BASE_URL + "/platforms/rare-candy/",
        "creator": {"@type": "Organization", "name": SITE_NAME},
        "license": "https://creativecommons.org/licenses/by/4.0/",
    })]

    return pages_written("/platforms/rare-candy/", page(
        "/platforms/rare-candy/",
        "Rare Candy Instapacks review — full odds, 50% floor, no cash value",
        "Rare Candy publishes value-band pull rates and a guaranteed 50% floor on every Instapack. Its terms say the Candy it pays out in has no cash value. Full odds for all 8 packs.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "Rare Candy")],
        updated=UPDATED, structured=ld))

def build_saja():
    s = saja_stats()

    band_rows = "".join(
        '<tr><td class="name">%s</td><td class="num">%s</td></tr>'
        % (lab, pct(q, 1)) for lab, q in SAJA_PACK["bands"])

    MARGIN = [
        ("SAJA", "100%", "100%", "<strong>None stated anywhere</strong>", "neg"),
        ("SwishX", "100% target", "85&ndash;90%", "10&ndash;15%, on the sell-back", ""),
        ("Gotya", "&asymp;100% (we measured 100.5%)", "90%", "10%, on the sell-back", ""),
        ("LastPack", "95% posted", "100%", "5%, on the pack", ""),
        ("Courtyard", "~85% measured", "90% advertised", "Both ends", ""),
    ]
    margin_rows = "".join(
        '<tr><td class="name">%s</td><td class="num">%s</td>'
        '<td class="num">%s</td><td>%s</td></tr>'
        % (n, ev, bb, ('<span class="neg">%s</span>' % m) if k == "neg" else m)
        for n, ev, bb, m, k in MARGIN)

    faq_html, faq_ld = faq_block([
        ("Does SAJA really pay 100%?",
         "<p>That is what it advertises, on both sides: &ldquo;INDUSTRY HIGHEST &mdash; 100% EXPECTED VALUE&rdquo; and &ldquo;100% BUYBACK RATE,&rdquo; with each pack page showing &ldquo;PACK EV 100%.&rdquo; We cannot check the first figure, because SAJA publishes rarity percentages but no value ranges, so there is nothing to compute from. The second is a stated policy rather than an estimate: 100% of the displayed value, locked at the pull, good for seven days. What we can say is that 100% on both sides leaves no margin visible anywhere in the pack economics &mdash; and a business does have to make money somewhere. The terms show where some of it can come from; the headline numbers do not.</p>"),
        ("What is “Split the Difference”?",
         "<p>The only valuation-dispute remedy we have found on any of the twenty-four platforms we track. If SAJA has priced a card above the market, you can request a split and SAJA refunds the difference in cash while you keep the card. Its own worked example: market $512.60, SAJA price $550.80, you get $38.20 back. Every other platform we have read treats its own valuation as the end of the matter &mdash; <a href=\"/platforms/chalkboard/\">Chalkboard</a> explicitly makes its FMV non-appealable. Note the direction, though: this pays out when SAJA has overpriced a card, which is the case where the buyer was already getting a <em>higher</em> buyback. It does nothing for a card SAJA has priced too low.</p>"),
        ("Who sets the card values on SAJA?",
         "<p>Not SAJA. Its terms state that &ldquo;card values shown in the app come from third-party market pricing services.&rdquo; That makes it one of only three platforms we track that does not mark its own homework &mdash; the others being <a href=\"/platforms/fanatics-instant-rips/\">Fanatics</a> and <a href=\"/platforms/underdog/\">Underdog</a>, through Phygitals. It matters more here than anywhere, because SAJA's entire pitch is a percentage <em>of</em> those values. SAJA does not name the service, and we have asked which one it is.</p>"),
        ("Can SAJA take cards you already own?",
         "<p>Its terms say it can. Under &ldquo;unwinding an account,&rdquo; if SAJA suspects &mdash; &ldquo;on any basis and without any obligation to investigate or to prove it&rdquo; &mdash; that an account has been used fraudulently or abusively, &ldquo;or for any other reason in our sole and absolute discretion,&rdquo; it may void every transaction on the account, confiscate the cards in its vault and every sale proceed and credit, all of which you forfeit, and refund only what you actually paid. That refund is your sole remedy. This sits in the same document that says ownership of a pulled card passes to you when the pack opens. It is the broadest clause of its kind we have read in this category.</p>"),
        ("How long can you keep a card on SAJA?",
         "<p>As long as you like, as far as we can tell. The vault is free, the cards are graded, insured and stored in Oregon, and we found no auto-sell deadline in the terms &mdash; which would make SAJA one of only three platforms where doing nothing does not eventually trigger a forced sale, alongside <a href=\"/platforms/poke-collect/\">Poke-Collect</a> and <a href=\"/platforms/rare-candy/\">Rare Candy</a>. The seven-day clock applies to the instant 100% offer, not to the card. Compare <a href=\"/platforms/lastpack/\">LastPack</a>, where storage is capped at five days, and <a href=\"/platforms/packed/\">Packed</a>, where it is one.</p>"),
        ("Is there a catch on withdrawing money?",
         "<p>Two, both in the terms. Deposited funds &ldquo;must be used in the Service once before they can be withdrawn&rdquo; &mdash; you cannot put money in and take it straight out; it has to go through a pack first. And SAJA reserves the right to &ldquo;hold, withhold, limit, or decline any use, withdrawal, or payout of your balance, in whole or in part, at any time, in our sole and absolute discretion, for any reason whatsoever or for no reason.&rdquo; Payments and payouts run through Stripe, with an instant-payout fee shown in the app.</p>"),
        ("Who operates SAJA?",
         "<p>Zodiac Games Company, Inc., a Delaware corporation doing business as SAJA, at 52-16 Roosevelt Avenue, Suite 2C, Woodside, NY 11377. Its marketing page says Brooklyn; the legal address is in Queens. Delaware law, AAA consumer arbitration, class-action waiver, a 30-day opt-out and a liability cap of $100 or twelve months of fees. Terms last updated 15 September 2026. iOS app only at the time of writing.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>SAJA advertises 100% expected value and a 100% buyback. That leaves no margin anywhere</h1>
    <p class="lede">It also has the best structural disclosures we have read &mdash; third-party card values, ownership at the pull, a free vault with no deadline, and the only valuation-dispute remedy in the category &mdash; in the same document that lets it confiscate your cards on suspicion alone.</p>
    {flags_saja}
  </div>

  <div class="finding">
    <p class="big">Every other platform we track with a ~100% expected value takes its margin on the buyback. Every platform with a 100% buyback posts an expected value below 100%. SAJA claims <strong>both at once</strong>, and names no fee, spread or cut in between. The money has to come from somewhere, and the terms &mdash; not the marketing &mdash; are where you can see the candidates.</p>
    <p class="small muted">Collected from the saja.com marketing pages and the SAJA Terms of Use (last updated 15 September 2026) on {collected}. SAJA is an iOS app; we have not opened a pack.</p>
  </div>

  <h2>Where everyone else's margin sits</h2>

  <div class="table-wrap">
  <table class="clauses">
  <caption>Posted expected value against stated buyback rate, for the platforms that publish both. Figures as advertised by each platform except where noted; collected {collected}.</caption>
  <thead><tr>
    <th scope="col">Platform</th>
    <th scope="col" class="num">Posted EV</th>
    <th scope="col" class="num">Buyback</th>
    <th scope="col">Visible gross margin</th>
  </tr></thead>
  <tbody>{margins}</tbody>
  </table>
  </div>

  <p>This is not a gotcha, and it is not an accusation. A company can run at a loss deliberately, and several in this category plainly are: buying market share with venture money is a normal thing to do, and if that is what SAJA is doing then a customer today is getting a genuinely good deal. What we object to is nowhere in that paragraph. It is that <strong>100% / 100% is presented as a sustainable product rather than as a growth subsidy</strong>, and a reader has no way to tell which it is.</p>

  <p>From the terms, four places the money can come from are visible, none of them disclosed as such on the marketing pages:</p>

  <ul>
    <li><strong>A deposit playthrough.</strong> &ldquo;Deposited funds must be used in the Service once before they can be withdrawn.&rdquo; Money cannot be parked and retrieved; it has to pass through a pack. That produces float, and it produces breakage from balances nobody comes back for.</li>
    <li><strong>The vendor spread.</strong> SAJA describes an &ldquo;exclusive vendor network&rdquo; where cards held in the vault attract verified bids that &ldquo;often run 90% of value or better.&rdquo; If SAJA buys at 100% and places with vendors at a different number, the difference is the business.</li>
    <li><strong>Cards nobody sells back.</strong> The 100% offer is good for seven days. A card you keep, ship or forget costs SAJA nothing further.</li>
    <li><strong>Fees at the edges.</strong> An instant-payout fee, shown in the app; flat-rate shipping; the grading and storage SAJA absorbs while a card sits in the vault.</li>
  </ul>

  <p>Those are reasonable ways to run a business. They are also the answer to &ldquo;how can 100% and 100% both be true,&rdquo; and that answer belongs next to the claim, not nine screens into a contract.</p>

  <h2>The odds it does publish add up to 99.1%</h2>

  <p>SAJA's Silver Pack page carries a seven-tier rarity table. It is the only odds disclosure we could find outside the app.</p>

  <div class="table-wrap">
  <table>
  <caption>SAJA Silver Pack ({price}), rarity rates as published on saja.com, collected {collected}. No value range is given for any tier, so no expected value can be computed from this table.</caption>
  <thead><tr><th scope="col">Tier</th><th scope="col" class="num">Chance</th></tr></thead>
  <tbody>{bands}</tbody>
  <tfoot><tr><th scope="row">Total</th><td class="num"><strong class="neg">{psum}</strong></td></tr></tfoot>
  </table>
  </div>

  <p>It sums to {psum}, short of 100% by {gap} of a point. On its own this is almost certainly rounding or a tier left off the public page rather than anything meaningful &mdash; <a href="/platforms/swishx/">SwishX</a> ran 100.04&ndash;100.64% and <a href="/platforms/lastpack/">LastPack</a> landed on exactly 100.0%, so neither direction is unusual. We record it because an odds table that does not total 100% is the one check a reader can run without trusting anyone, and because the pack is labelled &ldquo;PACK EV 100%&rdquo; directly above a table that cannot produce that figure, or any figure.</p>

  <div class="callout">
    <h3>What is missing is the value ranges</h3>
    <p>Percentages without value bands cannot be turned into an expected value. <a href="/platforms/lastpack/">LastPack</a>, <a href="/platforms/rare-candy/">Rare Candy</a>, <a href="/platforms/packz/">Packz</a>, <a href="/platforms/catchback/">CatchBack</a> and <a href="/platforms/swishx/">SwishX</a> all publish both, which is why we could check their numbers and cannot check this one. SAJA's terms say the odds shown in the app at the moment you buy are the odds that apply to that purchase &mdash; a real commitment, and more than most platforms make &mdash; but a commitment to a number we cannot see from here.</p>
  </div>

  <h2>Split the Difference</h2>

  <p>This is the genuinely new thing, and it deserves credit on its own terms. If SAJA has priced a card above the market, you can ask for the difference back in cash and keep the card. Its worked example: market $512.60, SAJA price $550.80, refund $38.20.</p>

  <p>No other platform we have read has anything like it. Across twenty-four sets of terms, the house valuation is final everywhere else &mdash; <a href="/platforms/chalkboard/">Chalkboard</a> states outright that its fair market value is not appealable, and <a href="/platforms/rip-station/">Rip Station</a> does not publish its valuations at all. A mechanism that pays the user when the platform's own pricing is wrong is the opposite instinct, and it is worth more than any percentage on the marketing page.</p>

  <p>Two caveats, both structural rather than suspicious. It only runs one way: it corrects prices that are too <em>high</em>, which is the case where a seller was already better off, and offers nothing when a card is priced too low. And the thing you are disputing against is a third-party market price SAJA does not name, so you are comparing one unnamed figure to another.</p>

  <h2>The disclosures that are better than the headline numbers</h2>

  <p>Three things in SAJA's terms are category-leading, and none of them appear in its advertising:</p>

  <ul class="plain-list">
    <li><strong>Card values come from third-party market pricing services.</strong> The platform does not set the number its own percentage is a percentage of. Only <a href="/platforms/fanatics-instant-rips/">Fanatics</a> and <a href="/platforms/underdog/">Underdog</a> can say the same, and both name their source; SAJA does not.</li>
    <li><strong>Ownership of a pulled card passes to you when the pack opens.</strong> Not on shipment, not on request. <a href="/platforms/lastpack/">LastPack</a> passes title only when a card ships; several platforms never address it.</li>
    <li><strong>No deadline on the vault.</strong> Free storage, graded and insured, in Oregon, with no auto-sell clause we could find. Inaction does not cost you the card. That is true of only two other platforms we track.</li>
  </ul>

  <p>The terms are also, plainly, the best-written in this category &mdash; short sentences, no capitalised blocks, and an opening line telling you to actually read them. We have read twenty-four of these documents and this is the only one that reads as though it were written for a customer.</p>

  <h2>And then the discretion clauses</h2>

  <p>The same document contains the broadest reservations of power we have found anywhere in this category. Not the broadest in one clause &mdash; the broadest overall.</p>

  <blockquote>
    <p>&ldquo;we may hold, withhold, limit, or decline any use, withdrawal, or payout of your balance, in whole or in part, at any time, in our sole and absolute discretion, <strong>for any reason whatsoever or for no reason</strong>&rdquo;</p>
  </blockquote>

  <p>And, under the heading <em>unwinding an account</em>:</p>

  <blockquote>
    <p>&ldquo;If we suspect, <strong>on any basis and without any obligation to investigate or to prove it</strong>, that an account has been used fraudulently, abusively, or in violation of these terms, <strong>or for any other reason in our sole and absolute discretion</strong>, we may unwind the account&hellip; void every pack opening, pull, sale, buyback, promotion, and other transaction on it&hellip; confiscate the cards and other items in its vault and every sale proceed, credit, promotional value, and other gain (together, <strong>winnings</strong>), all of which you forfeit; and refund&hellip; only the amounts you actually paid us&hellip; That refund is your sole remedy.&rdquo;</p>
  </blockquote>

  <p>Read that against the clause four screens earlier saying ownership passed to you when the pack opened. Both are in the same contract. The forfeiture clause is the one that would govern.</p>

  <p>Two further points worth having. SAJA's word for what you forfeit is &ldquo;<strong>winnings</strong>&rdquo; &mdash; its own vocabulary, in a document that otherwise carefully describes a retail purchase, and relevant to <a href="/is-card-ripping-gambling/">the question of what this activity legally is</a>. And on errors: &ldquo;Our determination that a malfunction or error occurred is final, and our records are conclusive as to what occurred absent manifest error.&rdquo;</p>

  <p>Clauses of this shape exist to stop organised fraud, and most platforms have some version. What is different here is the stacking: suspicion on any basis, no obligation to investigate or prove, any other reason at sole discretion, forfeiture of property the same contract says is yours, and the platform's own records conclusive as to what happened. Any one of those is ordinary. Together they mean the 100% / 100% promise is, as drafted, revocable at will.</p>

  <h2>SAJA's own competitor table</h2>

  <p>SAJA publishes a comparison putting <a href="/platforms/courtyard/">Courtyard</a> at 80%. Courtyard advertises 90%, and our reading of all 92 of its packs put the measured figure around 85%. We do not know where 80% comes from. We note it because a platform's figures for its rivals are a reasonable test of how it handles numbers generally, and this one is lower than both the advertised rate and our own independent estimate.</p>

  <h2>Platform facts</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Operator</th><td>Zodiac Games Company, Inc., a Delaware corporation dba SAJA; 52-16 Roosevelt Ave, Suite 2C, Woodside, NY 11377 (marketing page says Brooklyn)</td></tr>
    <tr><th scope="row">Governing law</th><td>Delaware; AAA consumer arbitration, class-action waiver, 30-day opt-out, small claims preserved; liability capped at $100 or twelve months of fees</td></tr>
    <tr><th scope="row">Terms dated</th><td>15 September 2026</td></tr>
    <tr><th scope="row">Platform</th><td>iOS app only at the time of writing</td></tr>
    <tr><th scope="row">Categories</th><td>Pok&eacute;mon</td></tr>
    <tr><th scope="row">Packs</th><td>Tiered, $1&ndash;$1,000</td></tr>
    <tr><th scope="row">Odds</th><td>Seven rarity tiers with percentages on the web, summing to <strong class="neg">{psum}</strong>; <strong class="neg">no value ranges published</strong>; full odds shown in-app before purchase, and the odds at the moment of purchase govern</td></tr>
    <tr><th scope="row">Posted EV</th><td>&ldquo;PACK EV 100%&rdquo; per pack; not calculable from anything published</td></tr>
    <tr><th scope="row">Valuation</th><td><strong class="pos">Third-party market pricing services</strong>, unnamed</td></tr>
    <tr><th scope="row">Buyback</th><td><strong class="pos">100% of displayed value</strong>, locked at the pull, good for 7 days; paid to the SAJA balance</td></tr>
    <tr><th scope="row">Dispute remedy</th><td><strong class="pos">Split the Difference</strong> &mdash; cash refund of the gap when SAJA prices a card above market, card retained. Unique among the platforms we track</td></tr>
    <tr><th scope="row">Cash out</th><td>Stripe; <strong class="neg">deposits must be used once before withdrawal</strong>; instant-payout fee in-app; every payout subject to discretionary hold</td></tr>
    <tr><th scope="row">Ownership</th><td><strong class="pos">Passes to you when the pack opens</strong></td></tr>
    <tr><th scope="row">Vault</th><td>Free, graded, insured, Oregon; <strong class="pos">no deadline or auto-sell clause found</strong></td></tr>
    <tr><th scope="row">Shipping</th><td>Flat rate</td></tr>
    <tr><th scope="row">Forfeiture</th><td><strong class="neg">&ldquo;Unwinding an account&rdquo;</strong> permits voiding all transactions and confiscating vaulted cards on suspicion, with no obligation to investigate or prove; deposits refunded as sole remedy</td></tr>
    <tr><th scope="row">Age</th><td>18+, one account per person</td></tr>
    <tr><th scope="row">States</th><td>None published</td></tr>
  </tbody>
  </table>
  </div>

  <div class="callout">
    <h3>Why this page has no rating</h3>
    <p>SAJA is the hardest platform to place that we have looked at, because its best and worst features are both at the extreme end of the range. On disclosure of <em>structure</em> &mdash; who values the cards, when you own them, how long you can keep them, what happens if the price is wrong &mdash; it is the best in the category. On disclosure of <em>numbers</em> it is among the thinnest: a 100% claim with no value ranges published to test it against. And its contract reserves the power to undo all of it.</p>
    <p>We also have not opened a pack. There is no web app, and every figure above comes from SAJA's own published material. The measurement that would settle this &mdash; displayed value against real sold prices &mdash; is the <a href="/methodology/">test we have not yet run on any platform</a>.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/guides/buyback-rates/">What a 100% buyback actually pays, and who pays cash for it</a></li>
    <li><a href="/platforms/lastpack/">LastPack, the other 100% buyback &mdash; with a five-day storage cap</a></li>
    <li><a href="/platforms/swishx/">SwishX, the only posted expected value we have reconciled</a></li>
    <li><a href="/compare/?p=saja,lastpack,swishx,courtyard">Compare SAJA, LastPack, SwishX and Courtyard side by side</a></li>
  </ul>
</div>
""".format(collected=SAJA_COLLECTED, faq=faq_html, bands=band_rows,
           margins=margin_rows, price=money(s["price"]),
           psum=pct(s["psum"], 1), gap=pct(s["gap"], 1).rstrip("%"),
           **{"flags_saja": flag_row("saja")})

    ld = [faq_ld, jsonld({
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "SAJA Silver Pack published rarity rates",
        "description": "Published seven-tier rarity rates for the SAJA Silver Pack, collected %s. SAJA publishes no value ranges, so no expected value is derivable." % SAJA_COLLECTED,
        "url": BASE_URL + "/platforms/saja/",
        "creator": {"@type": "Organization", "name": SITE_NAME},
        "license": "https://creativecommons.org/licenses/by/4.0/",
    })]

    return pages_written("/platforms/saja/", page(
        "/platforms/saja/",
        "SAJA review — 100% EV and 100% buyback, and no margin in between",
        "SAJA advertises 100% expected value and a 100% buyback, uses third-party card values, and passes ownership at the pull. Its terms also allow confiscating vaulted cards on suspicion alone.",
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"), (None, "SAJA")],
        updated=SAJA_COLLECTED, structured=ld))

def build_compare_tool():
    DEFAULT = ["courtyard", "chalkboard", "poke-collect"]

    def cell(v):
        """A field is either (text, class) or a plain string."""
        if isinstance(v, tuple):
            text, kind = v
            cls = {"ok": "pos", "neg": "neg"}.get(kind, "")
            return '<strong class="%s">%s</strong>' % (cls, text) if cls else text
        return v

    # Column headers: one per platform, each carrying its slug for the picker.
    heads = "".join(
        '<th scope="col" class="cmp-col" data-p="%s"><a href="%s">%s</a></th>'
        % (p["slug"], p["path"], p["name"]) for p in PLATFORMS)

    # One row per comparable field, every platform rendered into the HTML.
    body_rows = []
    for key, label in COMPARE_ROWS:
        cells = "".join(
            '<td class="cmp-col" data-p="%s">%s</td>' % (p["slug"], cell(p[key]))
            for p in PLATFORMS)
        body_rows.append(
            '<tr><th scope="row">%s</th>%s</tr>' % (E(label), cells))

    # Flags and a deep link, as the last two rows.
    flagcells = "".join(
        '<td class="cmp-col" data-p="%s">%s</td>' % (p["slug"], flag_row(p["slug"]))
        for p in PLATFORMS)
    body_rows.append('<tr><th scope="row">Trust flags</th>%s</tr>' % flagcells)
    linkcells = "".join(
        '<td class="cmp-col" data-p="%s"><a href="%s">Full breakdown &rarr;</a></td>'
        % (p["slug"], p["path"]) for p in PLATFORMS)
    body_rows.append('<tr><th scope="row">Read more</th>%s</tr>' % linkcells)

    chips = "".join(
        '<label class="chip-opt"><input type="checkbox" value="%s"%s> %s</label>'
        % (p["slug"], " checked" if p["slug"] in DEFAULT else "", E(p["name"]))
        for p in PLATFORMS)

    summaries = "".join(
        '<li data-p="%s"><a href="%s"><strong>%s</strong></a> &mdash; %s</li>'
        % (p["slug"], p["path"], E(p["name"]), p["blurb"]) for p in PLATFORMS)

    faq_html, faq_ld = faq_block([
        ("How do I compare card ripping sites?",
         "<p>Compare four things, in this order. First, whether the platform publishes odds at all &mdash; only Clutch Packs, SwishX, Gotya, Courtyard, Packz, Poke-Collect and Rare Candy publish anything on the open web, and six publish nothing anywhere public. Second, whether the buyback money can leave the platform: eleven of the twenty-four pay into something withdrawable, six pay credit that cannot, and the rest do not say. Third, who sets the card's value, because a 100% buyback on a number the platform alone decides is worth less than 90% on a checkable one. Fourth, how long you can hold a card before the platform acts &mdash; windows run from three hours to indefinite.</p>"),
        ("Which card ripping site is best?",
         "<p>We do not publish a single answer, because the right platform depends on what you are doing. If you want to calculate before you buy, Courtyard posts an exact expected value on every pack. If you intend to sell every card straight back, Packed and Chalkboard Pulls pay 100% into withdrawable balances. If you intend to keep what you pull, Poke-Collect ships the card to you by default and Arena Club, Fanatics and Tilt Rips vault indefinitely. We leave platforms unrated where the data to rate them is not published.</p>"),
        ("Why are so many cells on this table blank or unknown?",
         "<p>Because the platforms do not publish the figures. Seven of the twenty-four publish no pack prices on the open web at all, and only nine publish odds there, so no expected value can be calculated for most of them. We leave those cells as &ldquo;not calculable&rdquo; rather than estimating. <a href=\"/methodology/\">Our methodology</a> explains why an empty cell is more useful than a guessed one.</p>"),
        ("Can I share a comparison?",
         "<p>Yes. The web address updates as you change the selection, so copying it from the address bar shares exactly the platforms you picked. The full table for all twenty-four platforms is in the page itself, so it also works with JavaScript turned off.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Compare card ripping sites</h1>
    <p class="lede">Pick any two to four platforms and put their odds disclosure, buyback terms, valuation source and decision windows side by side. Every figure comes from the platform's own published material.</p>
  </div>

  <div class="picker" id="picker">
    <p class="picker-label"><strong>Choose platforms to compare</strong> <span class="muted small">(2&ndash;4)</span></p>
    <div class="chip-opts">{chips}</div>
    <p class="small muted" id="picker-msg"></p>
  </div>

  <div class="table-wrap">
  <table class="cmp" id="cmp">
  <caption>Card ripping platforms compared, from each platform's own published material, {collected}.</caption>
  <thead><tr><th scope="col">&nbsp;</th>{heads}</tr></thead>
  <tbody>{rows}</tbody>
  </table>
  </div>

  <p class="small muted">With JavaScript off, this table shows all twenty-four platforms at once &mdash; scroll it sideways. Nothing here is hidden from readers or crawlers.</p>

  <h2>What these columns actually mean</h2>
  <p>Four rows carry most of the decision, and they are not the ones the marketing emphasises.</p>

  <ul>
    <li><strong>Odds published.</strong> Four platforms publish something on the open web. The rest show odds only inside an app, or not at all. If you cannot see the odds before you pay, you cannot calculate anything.</li>
    <li><strong>Can the money leave.</strong> An advertised buyback rate tells you nothing until you know this. Four platforms pay credit that can only buy more packs, which is not money at any rate.</li>
    <li><strong>Who sets the card's value.</strong> On most platforms the company paying the buyback also decides what the card is worth. Fanatics is the only one that outsources the number to a third party. Chalkboard's terms call its own figure &ldquo;final and non-appealable.&rdquo;</li>
    <li><strong>How long you can hold a card.</strong> Windows run from three hours to indefinite, and on one platform the clock ends by shipping the card to you rather than selling it. The platforms paying the highest buyback rates have the shortest windows, which is not a coincidence.</li>
  </ul>

  <h2>Every platform in one line</h2>
  <ul class="plain-list" id="summaries">{summaries}</ul>

  <h2>Want to run the numbers yourself?</h2>
  <p>The <a href="/calculator/">pack EV calculator</a> takes whatever odds a platform publishes and returns the average card value, the expected loss per pack and the chance of beating the pack price. For a worked head-to-head on the two platforms that publish enough to compare directly, see <a href="/compare/courtyard-vs-packz/">Courtyard vs Packz</a>.</p>

  <h2>Frequently asked</h2>
  {faq}
</div>

<script>
(function () {{
  var MIN = 2, MAX = 4;
  var picker = document.getElementById('picker');
  if (!picker) return;
  var table = document.getElementById('cmp');
  if (table) table.classList.add('js-on');
  var boxes = [].slice.call(picker.querySelectorAll('input[type=checkbox]'));
  var msg = document.getElementById('picker-msg');
  var all = boxes.map(function (b) {{ return b.value; }});

  function apply(sel) {{
    var set = {{}};
    sel.forEach(function (s) {{ set[s] = 1; }});
    [].forEach.call(document.querySelectorAll('[data-p]'), function (el) {{
      el.hidden = !set[el.getAttribute('data-p')];
    }});
    boxes.forEach(function (b) {{ b.checked = !!set[b.value]; }});
    msg.textContent = sel.length + ' selected. Tick up to ' + MAX + '.';
    boxes.forEach(function (b) {{
      b.disabled = !b.checked && sel.length >= MAX;
    }});
    try {{
      history.replaceState(null, '', '?p=' + sel.join(','));
    }} catch (e) {{}}
  }}

  function chosen() {{
    return boxes.filter(function (b) {{ return b.checked; }})
                .map(function (b) {{ return b.value; }});
  }}

  var params = new URLSearchParams(location.search);
  var fromUrl = (params.get('p') || '').split(',').filter(function (s) {{
    return all.indexOf(s) !== -1;
  }});
  var start = fromUrl.length >= MIN ? fromUrl.slice(0, MAX) : chosen();

  boxes.forEach(function (b) {{
    b.addEventListener('change', function () {{
      var sel = chosen();
      if (sel.length < MIN) {{
        b.checked = true;
        msg.textContent = 'Keep at least ' + MIN + ' selected.';
        return;
      }}
      apply(sel);
    }});
  }});

  apply(start);
}})();
</script>
""".format(chips=chips, heads=heads, rows="".join(body_rows),
           summaries=summaries, faq=faq_html, collected=UPDATED)

    ld = [faq_ld, jsonld({
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "Card ripping platform comparison",
        "description": "Odds disclosure, buyback rates, withdrawal routes, valuation sources, decision windows, operators and jurisdictions for 14 online card ripping platforms, compiled from each platform's own published material.",
        "url": BASE_URL + "/compare/",
        "creator": {"@type": "Organization", "name": SITE_NAME},
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "variableMeasured": [label for _k, label in COMPARE_ROWS],
    })]

    return pages_written("/compare/", page(
        "/compare/",
        "Compare card ripping sites — odds, buyback and withdrawal terms",
        "Pick any two to four card ripping platforms and compare their odds disclosure, buyback rates, withdrawal routes, valuation sources and decision windows side by side.",
        body, crumbs=[("/", "Home"), (None, "Compare")],
        updated=UPDATED, structured=ld))


def build_buyback():
    def ratecell(v):
        return pct(v * 100, 1).replace(".0%", "%") if v is not None else "Not disclosed"

    rows = []
    for name, head, eff, cash, form, _who in BUYBACK_TERMS:
        if cash is True:
            cashcell = '<strong class="pos">Yes</strong>'
        elif cash is False:
            cashcell = '<strong class="neg">No</strong>'
        elif cash == "n/a":
            cashcell = "N/A"
        else:
            cashcell = "Unconfirmed"
        gap = ""
        if head and eff and eff < head - 0.001:
            gap = ' <span class="muted small">(&minus;%s)</span>' % pct((head - eff) * 100, 1)
        rows.append(
            '<tr><td class="name">%s</td><td class="num">%s</td>'
            '<td class="num"><strong>%s</strong>%s</td><td class="num">%s</td>'
            '<td>%s</td></tr>' % (
                E(name), ratecell(head), ratecell(eff), gap, cashcell, form))

    # $100 of card value, converted
    conv = []
    for name, _h, eff, cash, _f, _w in BUYBACK_TERMS:
        if eff is None:
            conv.append('<tr><td class="name">%s</td><td class="num">Unknown</td>'
                        '<td>Not disclosed</td></tr>' % E(name))
        else:
            kind = "cash you can withdraw" if cash else (
                "credit, packs only" if cash is False else "USDC, withdrawal unconfirmed")
            conv.append('<tr><td class="name">%s</td>'
                        '<td class="num"><strong>%s</strong></td><td>%s</td></tr>'
                        % (E(name), money(eff * 100), kind))

    # round trip on a $100 pack
    trips = [
        ("Courtyard", 0.95, 0.85, "Posted EV 95%, buyback measured at ~85%"),
        ("Packz", 1.0029, 0.90, "Estimated EV ~100%, but the 90% is credit only"),
        ("Fanatics Instant Rips", None, 0.846, "No pull rates published, so no EV"),
        ("Clutch Packs", 1.010, None, "Observed EV 1.01&times;, but no buyback terms"),
        ("Arena Club", None, 0.90, "No card values published, so no EV"),
        ("Tilt Rips", None, 0.90, "No odds published, so no EV"),
    ]
    trip_rows = []
    for name, ev, bb, note in trips:
        if ev and bb:
            back = ev * bb * 100
            trip_rows.append(
                '<tr><td class="name">%s</td><td class="num">%s</td>'
                '<td class="num">%s</td>'
                '<td class="num"><strong class="neg">%s</strong></td>'
                '<td class="num">%s</td></tr>' % (
                    E(name), pct(ev * 100, 0), pct(bb * 100, 1),
                    money(back), money(100 - back)))
        else:
            trip_rows.append(
                '<tr><td class="name">%s</td><td class="num" colspan="4">%s</td></tr>'
                % (E(name), note))

    faq_html, faq_ld = faq_block([
        ("Which card ripping site has the best buyback?",
         "<p>Arena Club and Tilt Rips, because both pay 90% into a wallet you can withdraw from &mdash; Arena Club to a bank account or debit card through Stripe, Tilt Rips in US dollars or cryptocurrency. Packz also advertises 90% but pays site credit that cannot be withdrawn and can only buy more packs, and Fanatics' 90% becomes 84.6% after a 6% marketplace fee and is also paid in credit. Crown Rips claims 100% but we have not been able to verify it, and Clutch Packs discloses no buyback terms at all.</p>"),
        ("Is the Fanatics instant offer really 90%?",
         "<p>No, it is 84.6% in practice. Fanatics' own published example takes a $200 card, applies the 90% rate to reach $180, then deducts a 6% marketplace fee of $10.80, leaving an offer of $169.20. That is 84.6% of the card's appraised value. The formula is 0.90 multiplied by 0.94. The 90% figure is accurate as a rate; it is just not what arrives in your account.</p>"),
        ("What do you actually get back if you sell a card straight back?",
         "<p>On a $100 Courtyard pack, about $80.75. The pack's posted expected value is 95% of the price, so the average card is worth about $95, and applying the measured ~85% instant offer to that leaves roughly $80.75. On Packz the same round trip returns about $90, but in credit that can only buy more packs rather than money you can take out. Those are averages across many packs, not what any single pack returns.</p>"),
        ("Can you withdraw money from card ripping sites?",
         "<p>It depends entirely on the platform, and the advertised buyback rate tells you nothing about it. Arena Club, Tilt Rips, Pickem, LETSGO and SwishX pay into withdrawable wallets, as do Packed and Chalkboard Pulls at 100%. Packz and Fanatics pay credit locked to the platform. Courtyard settles in USDC, though we have not verified the withdrawal path ourselves. On the platforms that pay credit, the only route to actual money is to decline the offer, have the physical card shipped, and sell it yourself &mdash; which costs shipping and time, and on a low-value pull usually costs more than the card is worth.</p>"),
    ])

    body = """
<div class="wrap narrow">
  <div class="page-head">
    <h1>Every site advertises a 90% buyback. Here is what you actually get back.</h1>
    <p class="lede">Six of the twenty-four platforms we track advertise a 90% buyback. On close reading the phrase means six different things, and on two of them the money cannot leave the platform at all.</p>
  </div>

  <div class="finding">
    <p class="big">Six platforms advertise 90%. One of them pays 84.6% after fees. Two pay in credit that cannot be withdrawn, and one settles in USDC by a route we have not verified. Three &mdash; Arena Club, Tilt Rips and Pickem &mdash; pay 90% into a wallet you can actually take money out of, and two platforms beat all six by paying 100% withdrawable. The headline rate is the least informative number on the page.</p>
    <p class="small muted">Compiled from each platform's own published terms and worked examples, {collected}. Rates change; check before you buy.</p>
  </div>

  <h2>The headline against the reality</h2>
  <div class="table-wrap">
  <table>
  <caption>Advertised and effective buyback rates across the twenty-four platforms we track, {collected}.</caption>
  <thead><tr>
    <th scope="col">Platform</th><th scope="col" class="num">Advertised</th>
    <th scope="col" class="num">Effective</th><th scope="col" class="num">Withdrawable</th>
    <th scope="col">Payout form</th>
  </tr></thead>
  <tbody>{rows}</tbody>
  </table>
  </div>

  <h2>What $100 of card value is really worth</h2>
  <p>The cleanest way to compare is to hold the card constant. Pull a card the platform values at $100, accept the instant offer, and this is what lands:</p>

  <div class="table-wrap">
  <table>
  <caption>A card valued at $100, converted through each platform's buyback.</caption>
  <thead><tr><th scope="col">Platform</th><th scope="col" class="num">You receive</th><th scope="col">In what form</th></tr></thead>
  <tbody>{conv}</tbody>
  </table>
  </div>

  <p>The spread between the best and worst of the six that say 90% is $5.40 on every $100 of card value. That is the small part. The large part is that on Packz and Fanatics, the $90 and $84.60 are not money &mdash; they are a balance that can only be spent back inside the platform.</p>

  <h2>Credit is not cash</h2>
  <p>This is the single biggest thing the headline rates conceal, and it is worth being precise about.</p>

  <p><strong>On Packz, a sell-back is a re-roll, not a refund.</strong> The credit can only buy more packs. If you pull a card worth less than you paid and accept the 90%, you have not recovered 90% of your money; you have converted a bad pull into a slightly smaller stake in the next one. The only route to actual money is to have the card shipped and sell it yourself, which on a $2 card costs more than the card is worth.</p>

  <p><strong>On Fanatics the door is wider but still inside the same building.</strong> Fanatics Live credits work across any Fanatics Live purchase rather than packs alone. There is also a genuine cash route, and it is not the instant offer: decline it, take the card, and list it on the Fanatics Collect marketplace, where sales pay out with free ACH withdrawal. That costs 1% to 3% in fulfilment and 3 to 15 business days. So the convenient option is the expensive one.</p>

  <p><strong>On Arena Club and Tilt Rips the money reaches you.</strong> Arena Club credits an in-house wallet that withdraws to a bank account or debit card through Stripe. Tilt Rips withdraws in dollars or crypto with no fees beyond those shown in the app. Of everything here, those are the two buybacks that behave the way the word implies.</p>

  <h2>The round trip</h2>
  <p>Buy a $100 pack, reveal the card, accept the instant offer. Where both the expected value and the buyback rate are published, the whole journey can be costed:</p>

  <div class="table-wrap">
  <table>
  <caption>A $100 pack bought and sold straight back, on average. These are long-run averages across many packs, not what any single pack returns.</caption>
  <thead><tr>
    <th scope="col">Platform</th><th scope="col" class="num">Avg card value</th>
    <th scope="col" class="num">Buyback</th><th scope="col" class="num">You end with</th>
    <th scope="col" class="num">Average loss</th>
  </tr></thead>
  <tbody>{trip_rows}</tbody>
  </table>
  </div>

  <p><strong>About $80.75 back on a $100 Courtyard pack.</strong> That is the number worth carrying around. Courtyard posts an expected value of 95% on most packs, which is already a 5% house edge, and the buyback takes most of the next 15%. Neither figure is hidden &mdash; Courtyard publishes the EV and advertises the rate &mdash; but nobody multiplies them together for you.</p>

  <p><strong>Packz looks better and is harder to use.</strong> Its published odds imply roughly 100% of face in card value, so a 90% buyback returns about $90 of every $100. That is the best round trip here on paper. It is also credit, so "returning $90" means holding $90 of stake in a product that will do the same thing to it again.</p>

  <p><strong>On four platforms the round trip cannot be costed at all</strong>, because either the odds or the buyback terms are missing. That is not a neutral fact about those platforms; it is the thing that makes them impossible to evaluate.</p>

  <h2>Who decides what your card is worth</h2>
  <p>A rate is only as meaningful as the valuation it is applied to, and on five of the eight platforms the company paying the buyback also sets the number it is paying a percentage of.</p>

  <p>Fanatics is the exception worth naming: it uses Card Ladder, a third-party sales-data service, so the valuation can in principle be checked against data a buyer can also reach. That is the best practice in the category, and it belongs to the platform with the worst effective rate. Tilt Rips sits at the other end, paying the highest withdrawable rate against a valuation from an unnamed source that it states cannot be disputed.</p>

  <p>A verifiable 84.6% and an unverifiable 90% are not ranked in the order the percentages suggest. We will take that apart properly in a separate piece.</p>

  <h2>What to check before you buy</h2>
  <ol>
    <li><strong>Is the payout cash or credit?</strong> This matters more than the rate. Ask whether proceeds can be withdrawn, not just what percentage they are.</li>
    <li><strong>Is a fee deducted after the percentage?</strong> Fanatics' 6% marketplace fee is the difference between 90% and 84.6%.</li>
    <li><strong>Who sets the card's value, and can you dispute it?</strong></li>
    <li><strong>What does shipping cost, and how long does it take?</strong> This is the escape route when the instant offer is poor, and it ranges from 3 to 15 business days at Fanatics to up to six weeks at Tilt Rips.</li>
    <li><strong>Multiply the buyback by the pack's expected value.</strong> That product, not either number alone, is what you get back.</li>
  </ol>

  <div class="callout danger">
    <h3>Worth saying plainly</h3>
    <p>No buyback on this page turns a pack into a positive-value purchase. The best round trip we can calculate still loses money on average, and the rates above describe what happens to the value you already lost on the pull. Decide what you are willing to spend before you start, and treat it as the cost of the entertainment rather than a position you can trade out of.</p>
    <p>If this has stopped feeling like fun, free and confidential help is available: call or text <strong>1-800-GAMBLER</strong>.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Go deeper</h2>
  <ul>
    <li><a href="/platforms/fanatics-instant-rips/">How the Fanatics 90% becomes 84.6%</a></li>
    <li><a href="/platforms/packz/">Why the Packz buyback pays credit, not cash</a></li>
    <li><a href="/platforms/">All twenty-four platforms compared</a></li>
  </ul>
</div>
""".format(collected=CLUTCH_COLLECTED, rows="".join(rows), conv="".join(conv),
           trip_rows="".join(trip_rows), faq=faq_html)

    art = jsonld({
        "@context": "https://schema.org", "@type": "Article",
        "headline": "Every site advertises a 90% buyback. Here is what you actually get back.",
        "description": "Five card ripping platforms advertise a 90% buyback. One pays 84.6% after fees, three pay credit that cannot be withdrawn, and only two pay money you can take out.",
        "datePublished": UPDATED, "dateModified": UPDATED,
        "author": {"@type": "Organization", "name": SITE_NAME},
        "publisher": {"@type": "Organization", "name": SITE_NAME},
        "mainEntityOfPage": BASE_URL + "/guides/buyback-rates/",
    })

    return pages_written("/guides/buyback-rates/", page(
        "/guides/buyback-rates/",
        "Card ripping buyback rates — what 90% actually pays out",
        "Five pack ripping sites advertise a 90% buyback. One pays 84.6% after fees, three pay non-withdrawable credit, and a $100 Courtyard pack sold straight back returns about $80.75.",
        body, crumbs=[("/", "Home"), (None, "Buyback rates")],
        updated=CLUTCH_COLLECTED, structured=[faq_ld, art]))


def flag_row(slug):
    """Scannable trust flags for one platform."""
    keys = PLATFORM_FLAGS.get(slug, [])
    if not keys:
        return ""
    chips = "".join(
        '<li class="flag %s" title="%s">%s</li>'
        % (FLAGS[k][1], E(FLAGS[k][2]), E(FLAGS[k][0])) for k in keys)
    return '<ul class="flags">%s</ul>' % chips


def build_legal():
    STATES = [
        "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
        "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
        "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
        "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
        "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
        "New Hampshire", "New Jersey", "New Mexico", "New York",
        "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
        "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
        "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
        "West Virginia", "Wisconsin", "Wyoming",
    ]
    rows = []
    for s in STATES:
        blocked = STATE_RESTRICTIONS.get(s, [])
        if blocked:
            cell = ('<td><strong class="neg">%s</strong></td>'
                    % E(", ".join(blocked)))
            note = "Blocked by %d of the 11 platforms we track" % len(blocked)
        else:
            cell = '<td class="muted">None we could source</td>'
            note = "No platform we track publishes a restriction here"
        age = "19" if s == "Nebraska" else "18"
        rows.append('<tr><th scope="row">%s</th>%s<td class="num">%s+</td>'
                    '<td class="muted small">%s</td></tr>'
                    % (E(s), cell, age, E(note)))

    faq_html, faq_ld = faq_block([
        ("Which states block card ripping sites?",
         "<p>Based on the platforms' own published terms, five states are restricted by at least one platform we track: Michigan, Minnesota, Montana, Nevada and Washington are all excluded by Pickem, and Nevada is additionally excluded by MintPull. No platform we track publishes a restriction on any other state. That is not the same as saying ripping is legal everywhere else &mdash; it means no operator has told us otherwise.</p>"),
        ("Why do those five states appear and not others?",
         "<p>Because the platform restricting them, Pickem, operates its rip product inside a social casino. Michigan, Minnesota, Montana, Nevada and Washington are the states most active against sweepstakes-model operators. The exclusions look like a response to sweepstakes enforcement rather than to anything about trading cards, which tells you how at least one operator understands its own product.</p>"),
        ("Is card ripping legal in my state?",
         "<p>We cannot tell you that, and neither can anyone else with confidence. No state has ruled specifically on digital pack ripping, the question of whether it constitutes gambling or an unlawful lottery is being litigated now, and operators are making their own risk judgements state by state. What we can tell you is which platforms will accept you and what their own terms say. For the underlying legal arguments, see <a href=\"/is-card-ripping-gambling/\">our page on the legal position</a>. For an actual answer about your own circumstances, ask a lawyer.</p>"),
        ("What is the minimum age for card ripping sites?",
         "<p>18 on every platform we track, except that Pickem requires 19 in Nebraska, which reflects Nebraska's age of majority. Several platforms also carry a 21+ framing in promotional material. Age verification varies widely: Packed and Pickem require a government ID and a liveness check before you can withdraw or ship, while others verify only at the point of shipping.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Where card ripping sites are restricted, state by state</h1>
    <p class="lede">Which platforms will accept you, which states they exclude, and why the exclusions look the way they do. Sourced from each platform's own published terms rather than from our reading of the law.</p>
  </div>

  <div class="finding">
    <p class="big">Five states are excluded by at least one platform we track: Michigan, Minnesota, Montana, Nevada and Washington. Every one of those exclusions comes from Pickem, whose rip product sits inside a social casino, and Nevada is additionally excluded by MintPull. No platform we track publishes a restriction on any other state.</p>
    <p class="small muted">Compiled from published terms, {collected}. This is availability, not legality &mdash; see the caveat below.</p>
  </div>

  <div class="callout">
    <h3>What this page is and is not</h3>
    <p>This is a record of <strong>where platforms say they will and will not operate</strong>. It is not legal advice and it is not a map of where ripping is lawful. No state has ruled specifically on digital pack ripping; the question is unsettled and being litigated. A state's absence from the restricted list means no operator has published a restriction there, not that anyone has blessed it.</p>
    <p>We would rather publish five states we can source than fifty we cannot. Where we have nothing, the table says so.</p>
  </div>

  <h2>The pattern in the exclusions</h2>
  <p>Michigan, Minnesota, Montana, Nevada and Washington are the states most active against sweepstakes-model operators. They are not states with unusual views on trading cards.</p>

  <p>That tells you something useful about how operators read their own product. Pickem runs its packs inside a social casino alongside slots and table games, and it has drawn its exclusion map the way a sweepstakes operator would. <a href="/platforms/crown-rips/">Crown Rips</a> has the same shape, sitting inside Crown Coins. Whatever the marketing says about collectibles, the compliance teams are treating these as gaming products in the states that scrutinise gaming products.</p>

  <p>The platforms that sell packs as straightforward retail &mdash; <a href="/platforms/courtyard/">Courtyard</a>, <a href="/platforms/arena-club/">Arena Club</a>, <a href="/platforms/fanatics-instant-rips/">Fanatics</a> &mdash; publish no state exclusions at all. Both groups are selling a randomised card for a fixed price. Only one group is behaving as though that might be regulated.</p>

  <h2>Availability by state</h2>
  <div class="table-wrap">
  <table>
  <caption>Platform-published restrictions by state, {collected}. &ldquo;None we could source&rdquo; means no platform we track publishes a restriction, not that the activity is approved.</caption>
  <thead><tr><th scope="col">State</th><th scope="col">Platforms that exclude it</th><th scope="col" class="num">Min age</th><th scope="col">Note</th></tr></thead>
  <tbody>{rows}</tbody>
  </table>
  </div>

  <h2>Platform availability at a glance</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">US only, no state detail published</th><td>Packz, Packed, Fast Rips, MintPull, Crown Rips</td></tr>
    <tr><th scope="row">US only, with state exclusions</th><td>Pickem (MI, MN, MT, NV, WA)</td></tr>
    <tr><th scope="row">Excludes Nevada specifically</th><td>MintPull</td></tr>
    <tr><th scope="row">Not restricted to the US</th><td>Courtyard &mdash; redeems worldwide</td></tr>
    <tr><th scope="row">No availability detail published</th><td>Arena Club, Clutch Packs, Tilt Rips, Fanatics Instant Rips</td></tr>
  </tbody>
  </table>
  </div>

  <h2>Age requirements</h2>
  <p>Every platform we track requires 18, with Pickem requiring 19 in Nebraska in line with that state's age of majority. Some carry 21+ framing in promotional material without making it a condition of use.</p>
  <p>Verification differs more than the headline age does. <a href="/platforms/packed/">Packed</a> and <a href="/platforms/pickem/">Pickem</a> require a government ID and a liveness check before you can withdraw or ship anything. <a href="/platforms/arena-club/">Arena Club</a> verifies through Stripe at withdrawal. Several verify only when you ask for a card to be shipped, which means you can buy packs before anyone has confirmed who you are. Given how much of this category's audience overlaps with Pok&eacute;mon collecting, that gap is worth noting.</p>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/is-card-ripping-gambling/">Is card ripping gambling? The legal arguments and the live cases</a></li>
    <li><a href="/platforms/">All twenty-four platforms compared</a></li>
  </ul>
</div>
""".format(collected=UPDATED, rows="".join(rows), faq=faq_html)

    return pages_written("/legal/", page(
        "/legal/",
        "Card ripping by state — where each platform is restricted",
        "Five states are excluded by at least one card ripping platform: Michigan, Minnesota, Montana, Nevada and Washington. Availability and age rules from each platform's own terms.",
        body, crumbs=[("/", "Home"), (None, "By state")],
        updated=UPDATED, structured=faq_ld))


ALTERNATIVES = {
    "courtyard": {
        "name": "Courtyard",
        "why": "it publishes an exact expected value on every pack, settles in "
               "USDC, and vaults cards indefinitely",
        "picks": [
            ("clutch-packs", "Clutch Packs",
             "If you came to Courtyard for the published EV, this is the only "
             "platform that goes further: 158,556 recorded pulls published "
             "on-chain, averaging 1.01&times; the pack price. It discloses no "
             "buyback terms, which is the trade."),
            ("packz", "Packz",
             "Publishes dollar-range odds on every pack and implies roughly "
             "100% of face in card value on its $25-and-up packs. The buyback "
             "pays credit that cannot be withdrawn."),
            ("arena-club", "Arena Club",
             "If the vaulting mattered more than the EV: indefinite storage "
             "and a 90% buyback that withdraws to a bank account. No card "
             "values are published, so no EV can be calculated."),
        ],
    },
    "fanatics-instant-rips": {
        "name": "Fanatics Instant Rips",
        "why": "it is the largest brand in the category, uses third-party "
               "Card Ladder valuations, and vaults cards free with no time limit",
        "picks": [
            ("arena-club", "Arena Club",
             "The closest like-for-like: graded slabs, indefinite vaulting, "
             "and a 90% buyback that reaches a bank account rather than the "
             "84.6% in non-withdrawable credit Fanatics pays."),
            ("courtyard", "Courtyard",
             "Publishes an exact expected value on every pack, which Fanatics "
             "does not do for any pack. Vaults indefinitely and insures."),
            ("tilt-rips", "Tilt Rips",
             "90% withdrawable in dollars or crypto with free vaulting. But it "
             "publishes no odds at all and will not name its valuation source, "
             "which is the one thing Fanatics does better than anyone."),
        ],
    },
    "packz": {
        "name": "Packz",
        "why": "its buyback pays site credit that can only buy more packs",
        "picks": [
            ("arena-club", "Arena Club",
             "Same 90% headline rate, but paid into a wallet that withdraws to "
             "a bank account or debit card through Stripe."),
            ("tilt-rips", "Tilt Rips",
             "90% withdrawable in dollars or crypto, free vaulting, no time "
             "limit. The catch is that it publishes no odds and will not name "
             "its valuation source."),
            ("courtyard", "Courtyard",
             "Lower stated return at 95% of the pack price, but it publishes "
             "that figure on every pack rather than leaving it to be estimated "
             "from value ranges."),
        ],
    },
}


def build_alternatives(slug):
    a = ALTERNATIVES[slug]
    cards = "".join(
        '<article class="card"><h3><a href="/platforms/%s/">%s</a></h3>%s'
        '<p>%s</p><p class="more"><a href="/platforms/%s/">Full breakdown '
        '&rarr;</a></p></article>' % (s, E(n), flag_row(s), why, s)
        for s, n, why in a["picks"])

    faq_html, faq_ld = faq_block([
        ("What is the best alternative to %s?" % a["name"],
         "<p>It depends which part of %s you are replacing. %s</p>" % (
             a["name"],
             " ".join("<strong>%s</strong> if %s" % (E(n), why[0].lower() + why[1:])
                      for _s, n, why in a["picks"][:2]))),
        ("Are there card ripping sites with better buyback terms than %s?" % a["name"],
         "<p>Our <a href=\"/guides/buyback-rates/\">buyback comparison</a> ranks all twenty-four platforms by what the headline rate actually converts to. The short version: Arena Club and Tilt Rips pay 90% into wallets you can withdraw from, Packed pays 100% withdrawable but gives you one day to decide, and Packz and Fanatics pay credit that cannot be withdrawn at all.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Alternatives to {name}</h1>
    <p class="lede">People look past {name} because {why}, or because they want something it does not do. Here is what each of the credible alternatives trades away.</p>
  </div>

  <div class="finding">
    <p class="big">There is no platform in this category that is better than {name} on every axis. Each of these is better on something and worse on something else, and which matters depends on whether you care most about published odds, withdrawable money, or being allowed to keep what you pull.</p>
    <p class="small muted">Based on published terms and odds collected {collected}.</p>
  </div>

  <div class="card-grid">{cards}</div>

  <h2>How to choose between them</h2>
  <ul>
    <li><strong>If you want to know the odds before you buy:</strong> Clutch Packs publishes observed results from 158,556 recorded pulls, and Courtyard publishes an exact expected value on every pack. Everyone else is a step down.</li>
    <li><strong>If you want to convert cards into money:</strong> Arena Club, Tilt Rips, Pickem and Packed all pay into accounts you can withdraw from. Packz, Fanatics, Fast Rips and MintPull do not.</li>
    <li><strong>If you want to keep what you pull:</strong> Courtyard, Arena Club, Fanatics and Tilt Rips vault indefinitely. Pickem gives you three hours, Packed one day, Crown Rips and MintPull seven.</li>
  </ul>

  <p>The <a href="/guides/buyback-rates/">full buyback comparison</a> and the <a href="/platforms/">platform directory</a> cover all twenty-four.</p>

  <h2>Frequently asked</h2>
  {faq}
</div>
""".format(name=E(a["name"]), why=a["why"], cards=cards,
           collected=COLLECTED, faq=faq_html)

    return pages_written("/alternatives/%s/" % slug, page(
        "/alternatives/%s/" % slug,
        "%s alternatives — what each one trades away" % a["name"],
        "The credible alternatives to %s, compared on published odds, "
        "whether the buyback reaches real money, and how long you can keep a "
        "card." % a["name"],
        body,
        crumbs=[("/", "Home"), ("/platforms/", "Platforms"),
                (None, "%s alternatives" % a["name"])],
        updated=COLLECTED, structured=faq_ld))


def build_withdrawals():
    rows = []
    for name, head, eff, cash, form, _who in BUYBACK_TERMS:
        if cash is True:
            verdict, cls = "Yes", "pos"
        elif cash is False:
            verdict, cls = "No", "neg"
        elif cash == "n/a":
            verdict, cls = "No balance", ""
        else:
            verdict, cls = "Unconfirmed", ""
        rows.append('<tr><td class="name">%s</td>'
                    '<td class="num"><strong class="%s">%s</strong></td>'
                    '<td>%s</td></tr>' % (E(name), cls, verdict, form))

    faq_html, faq_ld = faq_block([
        ("Which card ripping sites let you withdraw real money?",
         "<p>Eleven of the twenty-four we track pay into something you can withdraw from. Arena Club pays 90% to a bank account or debit card through Stripe. Tilt Rips pays 90% in US dollars or several cryptocurrencies. Packed pays 100% to a debit card, bank, PayPal or Venmo. Chalkboard Pulls pays 100% as Buyback Credit, withdrawable by ACH through Aeropay. Pickem pays 90% to a bank card, capped at $2,500 per withdrawal. LETSGO pays to PayPal, Venmo, debit card or bank transfer. SwishX pays from its Wallet through Stripe. SAJA pays 100% to its own balance and out through Stripe, though deposits must be spent once before anything can be withdrawn. Rips by Triumph pays to debit card, bank, PayPal or Venmo. LastPack's FAQ describes cash-outs through Coinflow or USDC while its &sect;4.5 calls the same credit pack credit. Packz, Fanatics, Fast Rips, Holofoil, Rare Candy and MintPull all pay credit that cannot be withdrawn, and Courtyard settles in USDC with a withdrawal path we have not verified.</p>"),
        ("Which card ripping site pays to PayPal?",
         "<p>Packed is the only platform we track that lists PayPal and Venmo as withdrawal options, alongside debit card and bank transfer, with a minimum around $5 to $10. Tilt Rips pays in US dollars or cryptocurrency. Arena Club and Pickem pay to a bank account or card. No other platform we track publishes PayPal as an option.</p>"),
        ("Are there withdrawal limits on card ripping sites?",
         "<p>MintPull caps withdrawals at $250 per seven days, which is the lowest by a wide margin &mdash; a $2,500 balance takes ten weeks to withdraw. Pickem caps at $2,500 per withdrawal with a $6 minimum. Packed, Arena Club and Tilt Rips publish no cap. Several platforms, including MintPull and Packed, also restrict withdrawals to proceeds from selling cards, meaning deposits cannot be taken back out.</p>"),
        ("How long do card ripping withdrawals take?",
         "<p>Packed's FAQ says instant withdrawals average about ten minutes, while its terms allow up to two weeks. MintPull states up to one week. Arena Club pays through Stripe on standard processing times. Fanatics offers free ACH or a $50 wire. Most platforms require identity verification before a first withdrawal, which is usually the longest part of the process.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Which card ripping sites actually pay out money</h1>
    <p class="lede">Seven of the twenty-four platforms we track let you withdraw. The rest pay credit you can only spend on more packs, or do not say. Here is who pays what, by which method, and with which limits.</p>
  </div>

  <div class="finding">
    <p class="big">Eleven platforms of twenty-four pay into an account you can withdraw from: Arena Club, Tilt Rips, Packed, Pickem, Chalkboard Pulls, LETSGO, SwishX, Gotya, Rips by Triumph, LastPack and SAJA. Six pay credit that cannot be withdrawn at all, and six do not say. One &mdash; MintPull &mdash; credits the buyback as pack credit under &sect;5.5 while a separate clause caps withdrawable proceeds at $250 per seven days.</p>
    <p class="small muted">From published terms and FAQs, {collected}.</p>
  </div>

  <h2>Can you get money out?</h2>
  <div class="table-wrap">
  <table>
  <caption>Whether buyback proceeds reach money you control, across all twenty-four platforms.</caption>
  <thead><tr><th scope="col">Platform</th><th scope="col" class="num">Withdrawable</th><th scope="col">How it is paid</th></tr></thead>
  <tbody>{rows}</tbody>
  </table>
  </div>

  <h2>By payment method</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">Bank account</th><td>Arena Club (via Stripe), Tilt Rips, Packed, Fanatics (ACH, free)</td></tr>
    <tr><th scope="row">Debit card</th><td>Arena Club, Packed, Pickem</td></tr>
    <tr><th scope="row">PayPal or Venmo</th><td>Packed only</td></tr>
    <tr><th scope="row">Cryptocurrency</th><td>Tilt Rips; Courtyard settles in USDC</td></tr>
    <tr><th scope="row">Wire transfer</th><td>Fanatics, $50 fee</td></tr>
    <tr><th scope="row">Nothing &mdash; credit only</th><td>Packz, Fanatics instant offers, Fast Rips, MintPull returns</td></tr>
  </tbody>
  </table>
  </div>

  <h2>Limits and minimums</h2>
  <div class="table-wrap">
  <table class="plain">
  <tbody>
    <tr><th scope="row">MintPull</th><td><strong class="neg">$250 per seven days</strong>; $5 minimum; sale proceeds only; up to a week to process</td></tr>
    <tr><th scope="row">Pickem</th><td>$2,500 maximum per withdrawal; $6 minimum; sale proceeds only</td></tr>
    <tr><th scope="row">Packed</th><td>No stated cap; roughly $5&ndash;$10 minimum; sale proceeds only; instant averages ~10 minutes per the FAQ, &ldquo;within two weeks&rdquo; per the terms</td></tr>
    <tr><th scope="row">Arena Club</th><td>No stated cap; Stripe's $1 minimum</td></tr>
    <tr><th scope="row">Tilt Rips</th><td>No stated cap; no fees beyond those shown in the app</td></tr>
    <tr><th scope="row">Fanatics</th><td>Free ACH or $50 wire; applies to marketplace sales, not instant offers</td></tr>
  </tbody>
  </table>
  </div>

  <h2>Three things that catch people out</h2>
  <p><strong>Deposits are often not withdrawable.</strong> MintPull, Packed and Pickem all restrict withdrawals to proceeds from selling inventory. Money you put in can only be spent on packs; only money you get back from cards can come out.</p>

  <p><strong>The convenient option is usually the expensive one.</strong> On Fanatics, the instant offer pays 84.6% in non-withdrawable credit, while declining it and selling the card on the Fanatics Collect marketplace pays real money. The same logic applies anywhere with a credit-only buyback: the cash route exists, it just runs through shipping and selling the card yourself.</p>

  <p><strong>Verification is the real delay.</strong> Most platforms require a government ID, and some a liveness check, before a first withdrawal. Doing that in advance rather than at the moment you want your money is worth the ten minutes &mdash; particularly on <a href="/platforms/packed/">Packed</a> and <a href="/platforms/pickem/">Pickem</a>, where a clock is running on the card itself.</p>

  <h2>Frequently asked</h2>
  {faq}

  <h2>Next</h2>
  <ul>
    <li><a href="/guides/buyback-rates/">What a 90% buyback actually pays</a></li>
    <li><a href="/platforms/">All twenty-four platforms compared</a></li>
  </ul>
</div>
""".format(collected=UPDATED, rows="".join(rows), faq=faq_html)

    return pages_written("/guides/withdrawals/", page(
        "/guides/withdrawals/",
        "Card ripping withdrawals — which sites actually pay out",
        "Eleven of twenty-four card ripping platforms let you withdraw real money. Which pay to bank, PayPal or crypto, which pay credit only, and what the limits are.",
        body, crumbs=[("/", "Home"), (None, "Withdrawals")],
        updated=UPDATED, structured=faq_ld))


def build_changelog():
    items = []
    for date, title, detail, url in CHANGELOG:
        items.append(
            '<li class="log-item"><div class="log-date"><time datetime="%s">%s'
            '</time></div><div class="log-body"><h3><a href="%s">%s</a></h3>'
            '<p>%s</p></div></li>' % (date, date, E(url), E(title), detail))

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>What we have found, and when</h1>
    <p class="lede">A dated record of every platform we have collected, every figure we have published, and every change we have caught. Platforms revise their odds and terms without announcing it, so the date on a number matters as much as the number.</p>
  </div>

  <div class="finding">
    <p class="big">We date every dataset because this category changes underneath you. In one month, Arena Club's entire $25 Pok&eacute;mon checklist rotated &mdash; not one card from September appeared in October, the common tier shrank from 50 cards to 24, and the displayed rates stopped adding up to 100%.</p>
  </div>

  <ol class="changelog">{items}</ol>

  <h2>Open questions</h2>
  <p>Things we have published as unresolved rather than guessed at:</p>
  <ul>
    <li><strong>Arena Club's October odds summing to 49.07%.</strong> Either the displayed per-card rates go stale as inventory sells out, or part of the checklist did not load. We are rechecking.</li>
    <li><strong>Whether Clutch Packs has a buyback at all.</strong> No terms appear anywhere, which is the one gap in otherwise category-leading disclosure.</li>
    <li><strong>Whether Fast Rips' advertised cash-out exists.</strong> Its homepage promises a bank payout; its terms say platform credit is not withdrawable.</li>
    <li><strong>Whether any platform's valuations match real sold prices.</strong> Every expected value on this site still rests on the platform's own numbers.</li>
  </ul>

  <h2>Corrections</h2>
  <p>We publish these rather than quietly editing.</p>
  <ul>
    <li><strong>Courtyard referral offer.</strong> Earlier research described a Courtyard referral guaranteeing a $25 buyback on a $25 starter pack. We could not substantiate it. Courtyard has no welcome offer; its referral pays the referrer in points of undisclosed value. Corrected on the <a href="/guides/bonus-offers/">bonus offers page</a>.</li>
  </ul>

  <p class="small muted">Found something we have wrong? The <a href="/methodology/">methodology page</a> explains how we handle corrections.</p>
</div>
""".format(items="".join(items))

    return pages_written("/changelog/", page(
        "/changelog/",
        "Changelog — what we have found, and when",
        "A dated record of every platform collected, figure published and change caught across twenty-four card ripping platforms.",
        body, crumbs=[("/", "Home"), (None, "Changelog")], updated=UPDATED))


def build_methodology():
    body = """
<div class="wrap">
  <div class="page-head">
    <h1>How we rate card ripping platforms</h1>
    <p class="lede">What goes into a score, what we refuse to guess at, and how we handle the money side so you can judge whether our numbers deserve your trust.</p>
  </div>

  <h2>The scoring weights</h2>
  <p>Most of the weight sits on things that can be measured rather than impressions of a website. A platform's score is out of 10.</p>

  <div class="table-wrap">
  <table class="plain">
  <thead><tr><th scope="col">Factor</th><th scope="col" class="num">Weight</th><th scope="col">What it measures</th></tr></thead>
  <tbody>
    <tr><th scope="row">Pack expected value against price</th><td class="num">35%</td><td>What the average pack returns, calculated from published odds and checked against real sold prices</td></tr>
    <tr><th scope="row">Buyback quality</th><td class="num">25%</td><td>The rate, and crucially whether it pays withdrawable money or site credit</td></tr>
    <tr><th scope="row">Odds transparency</th><td class="num">20%</td><td>Whether a buyer can work out their own expected value before spending</td></tr>
    <tr><th scope="row">Payouts and shipping</th><td class="num">10%</td><td>Getting the card or the money out, and what that costs</td></tr>
    <tr><th scope="row">Trust and support</th><td class="num">10%</td><td>Track record, dispute handling, how clearly terms are stated</td></tr>
  </tbody>
  </table>
  </div>

  <h2>Where the numbers come from</h2>
  <p>We collect each platform's published odds directly from its own pack pages and record the date. Those collections are published as CSV files on our <a href="/data/">open data page</a> so anyone can check our arithmetic or redo it themselves.</p>

  <p>Where a platform publishes an exact expected value, as Courtyard does, we report that figure and say that it is the platform's own. Where a platform publishes only value ranges, as Packz does, we calculate a band and report the midpoint as the headline with the full span alongside it. Where a platform publishes no values at all, as Arena Club does, we say the expected value cannot be calculated rather than inventing one.</p>

  <h2>What we will not do</h2>
  <ul>
    <li><strong>Publish a score before we have the data.</strong> A platform shows no rating here until we have collected its odds ourselves. An empty cell is more useful than a guess.</li>
    <li><strong>Pass off a platform's valuations as verified.</strong> Every expected value on this site currently rests on the platform's own view of what its cards are worth. We label that clearly, and checking a sample against real sold prices is our current priority.</li>
    <li><strong>Reuse another site's data.</strong> Other trackers exist and some do good work. We link to them where useful and build our own ratings only on numbers we have collected.</li>
    <li><strong>Let a commission move a score.</strong> See below.</li>
  </ul>

  <h2>How we make money, and what that cannot buy</h2>
  <p>Some outbound links on this site are affiliate links, which means we may earn a commission if you sign up or buy through them. Every such link is marked and the disclosure appears in the footer of every page.</p>
  <p>Commissions do not affect a score, a ranking, or any published number. We will publish an unfavourable finding about a platform we earn from, and we have no agreement with any platform that restricts what we can write. If a platform ever asks for one, we will say so on this page.</p>
  <p>We also send each platform our figures before publishing and invite corrections. If a platform improves its disclosure or raises its buyback, we re-score it and say so.</p>

  <h2>Corrections</h2>
  <p>If you think a number here is wrong, tell us and show your working. We date every dataset so that a figure can be checked against what the platform published at the time, and we note changes rather than quietly overwriting them. Platforms do change their odds, and a corrected figure is a better outcome for everyone than a confident wrong one.</p>
</div>
"""
    return pages_written("/methodology/", page(
        "/methodology/",
        "How we rate card ripping platforms — methodology",
        "Our scoring weights, where our odds data comes from, what we refuse to estimate, and how affiliate commissions are kept out of the ratings.",
        body, crumbs=[("/", "Home"), (None, "How we rate")]))


def build_gambling():
    faq_html, faq_ld = faq_block([
        ("Is card ripping legal in the United States?",
         "<p>Digital pack ripping is not currently banned outright, and the major platforms operate openly in the US. But the legal position is unsettled and varies by state. Lawyers advising operators identify gambling and lottery law as the biggest risk, on the basis that paying money for a random prize of uncertain value can meet the legal test for an unlawful lottery. Several cases are testing that question now, so the honest answer is that it is legally grey rather than clearly settled.</p>"),
        ("Are there lawsuits against pack ripping sites?",
         "<p>Yes. A California False Claims Act suit filed in 2025 targets Whatnot and Fanatics Live over what it characterises as unlicensed box-break lotteries. PackDraw faces suits in Minnesota and New York alleging it drew a minor into offshore crypto gambling. Those allegations are untested in court and none of the cases has produced a final ruling, so they indicate regulatory attention rather than a settled legal conclusion.</p>"),
        ("Is ripping a good way to make money?",
         "<p>No. Every pack we have measured returns less than it costs on average, which is by design: operators set the return below the price the same way a casino sets a house edge. Published odds across the platforms we have checked imply returns of roughly 92% to 100% of the pack price, and after a buyback of 90% or less the realistic cash return is in the low-to-mid 80s. Treat money spent ripping as the cost of entertainment rather than an investment.</p>"),
    ])

    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Is card ripping gambling?</h1>
    <p class="lede">Digital pack ripping sits in a legal grey area that is being tested in court right now. Whatever the law decides, the mathematics already works like a casino game.</p>
  </div>

  <div class="finding">
    <p class="big">Whether digital pack ripping is legally gambling is unresolved and may differ by state. What is not in question is the economics: on every pack we have measured, the average payout is less than the pack price, which is the same structure as a house edge.</p>
  </div>

  <h2>How a digital rip works</h2>
  <p>You pay for a pack. A random card is revealed. You receive a real graded collectible, which you can keep, have shipped, or sell back to the platform at its buyback rate. Platforms argue that because you always receive something of value, this is a retail purchase rather than a wager.</p>

  <h2>The legal argument against that</h2>
  <p>The counter-argument is that the three classic elements of gambling are all present: you pay consideration, the outcome turns on chance, and the prize varies in value. Lawyers advising operators in this sector flag gambling and lottery law as the most serious risk they face, and some regulators and plaintiffs have argued that these products amount to unlicensed lotteries.</p>

  <p>That question is live. A California False Claims Act suit filed in 2025 targets Whatnot and Fanatics Live over what it describes as unlicensed box-break lotteries, and PackDraw faces suits in Minnesota and New York alleging it recruited a minor into offshore crypto gambling. Those allegations have not been tested in court. The outcome matters beyond the named companies, because a ruling that these products are gambling would reshape the whole category.</p>

  <p>Pok&eacute;mon packs sharpen the issue, because the audience skews young and age verification across the sector is inconsistent. Several platforms are restricted to adults; not all of them check carefully.</p>

  <h2>What the maths says, regardless of the law</h2>
  <p>Every pack we have measured returns less than it costs on average. Courtyard publishes an expected value of 95% of the pack price on most of its packs. Packz's published odds imply around {pzstd} at midpoint values, and less on its cheapest packs. Once you apply a buyback of 90% or less, the realistic cash return on a sell-back is in the low-to-mid 80s as a percentage of what you spent.</p>

  <p>That is not a criticism of any particular operator. It is how the product has to work for the business to exist, exactly as a slot machine's return-to-player sits below 100%. The difference is that regulated casinos are generally required to publish their return-to-player figure, while in this sector publishing an expected value is currently a voluntary choice that most platforms do not make.</p>

  <div class="callout danger">
    <h3>Rip with a budget</h3>
    <p>Decide what you are willing to lose before you start and treat it as the price of the entertainment. Do not chase losses by buying another pack to recover the last one; the odds on the next pack are identical regardless of what just happened. These products are for adults.</p>
    <p>If ripping has stopped feeling like fun, free and confidential help is available: call or text <strong>1-800-GAMBLER</strong>.</p>
  </div>

  <h2>Frequently asked</h2>
  {faq}

  <p class="small muted">Nothing on this page is legal advice. We are not lawyers, and if you are operating in this sector or making a decision that turns on the legal position, get advice from someone who is.</p>
</div>
""".format(pzstd=pct(PZ_STD_MID * 100, 0), faq=faq_html)

    return pages_written("/is-card-ripping-gambling/", page(
        "/is-card-ripping-gambling/",
        "Is card ripping gambling? The legal position and the maths",
        "Digital pack ripping is legally unsettled and being tested in court. What the gambling and lottery arguments are, which lawsuits are live, and why every pack loses money on average.",
        body, crumbs=[("/", "Home"), (None, "Is it gambling?")],
        structured=faq_ld))


def build_data():
    body = """
<div class="wrap">
  <div class="page-head">
    <h1>Open data</h1>
    <p class="lede">Every odds table we have collected, published as CSV with the date it was collected. Check our arithmetic, redo it differently, or use it in your own work.</p>
  </div>

  <p>We publish the raw data because a rating is only worth as much as the numbers behind it. Each file records the odds exactly as the platform displayed them on the collection date. Platforms do change their odds, so dated snapshots also let us show what changed and when.</p>

  <div class="table-wrap">
  <table class="plain">
  <thead><tr><th scope="col">Dataset</th><th scope="col">Contents</th><th scope="col">Collected</th><th scope="col">Download</th></tr></thead>
  <tbody>
    <tr>
      <td class="name">Courtyard pack odds</td>
      <td>{cyn} packs: price, dollar-range tiers, odds per tier, and Courtyard's posted expected value</td>
      <td>{collected}</td>
      <td><a href="/data/courtyard_odds_2026-09-21.csv">CSV</a></td>
    </tr>
    <tr>
      <td class="name">Packz pack odds</td>
      <td>{pzn} packs: price, dollar-range tiers and odds per tier</td>
      <td>{collected}</td>
      <td><a href="/data/packz_odds_2026-09-21.csv">CSV</a></td>
    </tr>
    <tr>
      <td class="name">Rare Candy Instapack odds</td>
      <td>8 packs: price, five value bands by total pack value, odds per band, and the guaranteed Candy floor</td>
      <td>{collected}</td>
      <td><a href="/data/rarecandy_odds_2026-10-22.csv">CSV</a></td>
    </tr>
  </tbody>
  </table>
  </div>

  <h3>Format</h3>
  <p>All three files use the same columns: <code>platform</code>, <code>category</code>, <code>pack_name</code>, <code>pack_price</code>, <code>tier_min</code>, <code>tier_max</code>, <code>odds_pct</code>, one row per value tier. The Courtyard file additionally carries a row per pack in the form <code>EV,[pack_name],[value]</code> holding the expected value Courtyard publishes for that pack. The Rare Candy file carries two extra columns, <code>band</code> and <code>guaranteed_candy</code>, because its bands are named and its tiers describe total pack value rather than a single card; 100 Candy equals $1.</p>

  <h3>Licence and citation</h3>
  <p>Free to use with attribution, under a <a href="https://creativecommons.org/licenses/by/4.0/" rel="nofollow">CC BY 4.0</a> licence. Please cite as: {site}, &ldquo;{cy} pack odds,&rdquo; collected {collected}, {base}/data/.</p>

  <h3>Not yet published</h3>
  <p>Arena Club publishes per-card hit rates with no values attached, so there is no comparable odds table to release. We have collected two complete card checklists and will publish them once the card identifiers are detailed enough to be matched to real sale prices.</p>
</div>
""".format(cyn=CY_N, pzn=PZ_N, collected=COLLECTED, site=SITE_NAME,
           cy="Courtyard and Packz", base=BASE_URL)

    ld = jsonld({
        "@context": "https://schema.org", "@type": "DataCatalog",
        "name": "%s pack odds datasets" % SITE_NAME,
        "url": BASE_URL + "/data/",
        "description": "Published odds tables collected from online card ripping platforms.",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "dataset": [
            {"@type": "Dataset", "name": "Courtyard pack odds and expected values",
             "url": BASE_URL + "/platforms/courtyard/", "dateModified": COLLECTED},
            {"@type": "Dataset", "name": "Packz pack odds",
             "url": BASE_URL + "/platforms/packz/", "dateModified": COLLECTED},
        ],
    })
    return pages_written("/data/", page(
        "/data/",
        "Open data — card ripping pack odds datasets",
        "Download the raw odds tables we collected from Courtyard and Packz as CSV, dated and free to reuse with attribution.",
        body, crumbs=[("/", "Home"), (None, "Open data")],
        updated=COLLECTED, structured=ld))


# ================================================================== assets
FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
<rect width="32" height="32" rx="5" fill="#2447B0"/>
<rect x="9" y="6" width="14" height="20" rx="2" fill="#fff"/>
<rect x="11.5" y="9" width="9" height="2" rx="1" fill="#2447B0"/>
<rect x="11.5" y="13" width="9" height="2" rx="1" fill="#9BB4F2"/>
<rect x="11.5" y="17" width="6" height="2" rx="1" fill="#9BB4F2"/>
</svg>"""

ROBOTS = """# {site} — all crawlers welcome, including AI crawlers.

User-agent: *
Allow: /

# AI and answer-engine crawlers, named explicitly so there is no ambiguity.
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Applebot
Allow: /

User-agent: Applebot-Extended
Allow: /

User-agent: Bingbot
Allow: /

User-agent: CCBot
Allow: /

User-agent: Meta-ExternalAgent
Allow: /

User-agent: Amazonbot
Allow: /

User-agent: cohere-ai
Allow: /

User-agent: DuckAssistBot
Allow: /

User-agent: MistralAI-User
Allow: /

User-agent: YouBot
Allow: /

Sitemap: {base}/sitemap.xml
""".format(site=SITE_NAME, base=BASE_URL)


def write_sitemap(paths):
    urls = []
    priorities = {"/": "1.0", "/platforms/": "0.9",
                  "/compare/courtyard-vs-packz/": "0.9", "/calculator/": "0.9"}
    for p in paths:
        urls.append(
            "  <url>\n    <loc>%s%s</loc>\n    <lastmod>%s</lastmod>\n"
            "    <changefreq>weekly</changefreq>\n    <priority>%s</priority>\n  </url>"
            % (BASE_URL, p, UPDATED, priorities.get(p, "0.8")))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(urls) + "\n</urlset>\n")
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(xml)


def write_indexnow_script(paths):
    """A one-shot script that submits every URL to IndexNow (Bing, Yandex, et al)."""
    urls = ",\n    ".join('"%s%s"' % (BASE_URL, x) for x in paths)
    host = BASE_URL.replace("https://", "")
    body = '''#!/usr/bin/env python3
"""Submit every page to IndexNow. Run after a deploy.

    python3 indexnow.py

IndexNow notifies Bing, Yandex, Seznam and Naver within minutes. Google does
not participate, so use Search Console for Google.
"""
import json
import urllib.request

KEY = "%s"
HOST = "%s"
URLS = [
    %s
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
''' % (INDEXNOW_KEY, host, urls)
    with open(os.path.join(OUT, "indexnow.py"), "w", encoding="utf-8") as fh:
        fh.write(body)


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    paths = [
        build_home(),
        build_platforms_index(),
        build_courtyard(),
        build_packz(),
        build_arena_club(),
        build_clutch(),
        build_fanatics(),
        build_crown_rips(),
        build_tilt(),
        build_compare(),
        build_chase(),
        build_bonuses(),
        build_mintpull(),
        build_legal(),
        build_withdrawals(),
        build_changelog(),
        build_alternatives("courtyard"),
        build_alternatives("fanatics-instant-rips"),
        build_alternatives("packz"),
        build_pickem(),
        build_packed(),
        build_fast_rips(),
        build_chalkboard(),
        build_poke_collect(),
        build_letsgo(),
        build_rarecandy(),
        build_swishx(),
        build_triumph(),
        build_gotya(),
        build_holofoil(),
        build_catchback(),
        build_ripstation(),
        build_underdog(),
        build_lastpack(),
        build_saja(),
        build_compare_tool(),
        build_buyback(),
        build_calculator(),
        build_methodology(),
        build_gambling(),
        build_data(),
    ]

    shutil.copy("styles.css", os.path.join(OUT, "styles.css"))

    # IndexNow: key file must be served at the site root.
    with open(os.path.join(OUT, INDEXNOW_KEY + ".txt"), "w",
              encoding="utf-8") as fh:
        fh.write(INDEXNOW_KEY)
    with open(os.path.join(OUT, "favicon.svg"), "w", encoding="utf-8") as fh:
        fh.write(FAVICON)
    with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write(ROBOTS)
    write_sitemap(paths)
    write_indexnow_script(paths)

    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
    with open(os.path.join(OUT, "data", "rarecandy_odds_2026-10-22.csv"),
              "w", encoding="utf-8") as fh:
        fh.write("platform,category,pack_name,pack_price,band,tier_min,"
                 "tier_max,odds_pct,guaranteed_candy\n")
        import html as _h
        for nm, price, guar, bands in RARECANDY_PACKS:
            clean = _h.unescape(nm).replace('"', "'")
            for lab, lo, hi, p in bands:
                fh.write('Rare Candy,Instapacks,"%s",%.2f,%s,%s,%s,%s,%d\n'
                         % (clean, price, lab, lo, hi, p, guar))

    for f in ("courtyard_odds_2026-09-21.csv", "packz_odds_2026-09-21.csv"):
        shutil.copy(f, os.path.join(OUT, "data", f))

    # Vercel config: clean URLs, noindex the preview host, cache assets.
    with open(os.path.join(OUT, "..", "vercel.json"), "w", encoding="utf-8") as fh:
        fh.write("""{
  "cleanUrls": true,
  "trailingSlash": true,
  "headers": [
    {
      "source": "/(.*)",
      "has": [{ "type": "host", "value": "(?<h>.*\\\\.vercel\\\\.app)" }],
      "headers": [{ "key": "X-Robots-Tag", "value": "noindex" }]
    },
    {
      "source": "/styles.css",
      "headers": [{ "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }]
    },
    {
      "source": "/data/(.*)",
      "headers": [{ "key": "Cache-Control", "value": "public, max-age=86400" }]
    }
  ]
}
""")

    print("Built %d pages:" % len(paths))
    for p in paths:
        print("  " + p)


if __name__ == "__main__":
    main()
