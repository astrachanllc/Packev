"""Shared page shell. Everything renders to static HTML at build time."""
import html
import json

SITE_NAME = "PackEV"
# Change this one constant when the real domain is registered.
BASE_URL = "https://packev.xyz"
TAGLINE = "Card ripping sites, rated by the math"

# Google tag (GA4 measurement ID, e.g. "G-XXXXXXXXXX"). Empty = no tag emitted.
GA_ID = "G-BCTDNF4LCD"


def analytics_tag():
    """Google tag snippet, or nothing if no ID is configured."""
    if not GA_ID:
        return ""
    return (
        '<script async src="https://www.googletagmanager.com/gtag/js?id=%s"></script>\n'
        "<script>\n"
        "  window.dataLayer = window.dataLayer || [];\n"
        "  function gtag(){dataLayer.push(arguments);}\n"
        "  gtag('js', new Date());\n"
        "  gtag('config', '%s');\n"
        "</script>" % (GA_ID, GA_ID)
    )

NAV = [
    ("/platforms/", "Platforms"),
    ("/compare/", "Compare"),
    ("/calculator/", "Pack EV calculator"),
    ("/guides/buyback-rates/", "Buyback rates"),
    ("/legal/", "By state"),
    ("/methodology/", "How we rate"),
]

FOOTER_NAV = [
    ("/", "Home"),
    ("/platforms/", "Platforms"),
    ("/compare/", "Compare platforms"),
    ("/calculator/", "Pack EV calculator"),
    ("/guides/chase-card-odds/", "Chase card odds"),
    ("/guides/bonus-offers/", "Bonus offers"),
    ("/guides/buyback-rates/", "Buyback rates"),
    ("/guides/withdrawals/", "Withdrawals"),
    ("/legal/", "By state"),
    ("/methodology/", "How we rate"),
    ("/is-card-ripping-gambling/", "Is it gambling?"),
    ("/changelog/", "Changelog"),
    ("/data/", "Open data"),
]

E = html.escape


def jsonld(obj):
    return ('<script type="application/ld+json">'
            + json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            + "</script>")


def breadcrumbs(items):
    """items: [(url, label)] ending with the current page (url may be None)."""
    if not items:
        return "", ""
    parts = []
    for url, label in items[:-1]:
        parts.append('<a href="%s">%s</a>' % (E(url), E(label)))
    parts.append("<span aria-hidden='true'>/</span>".join([]))
    sep = '<span aria-hidden="true">/</span>'
    trail = sep.join('<a href="%s">%s</a>' % (E(u), E(l)) for u, l in items[:-1])
    html_out = ('<nav class="crumbs" aria-label="Breadcrumb"><div class="wrap">'
                + trail + sep + "<span class='muted'>" + E(items[-1][1])
                + "</span></div></nav>")
    ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": label,
             **({"item": BASE_URL + url} if url else {})}
            for i, (url, label) in enumerate(items)
        ],
    }
    return html_out, jsonld(ld)


def faq_block(qa):
    """qa: [(question, answer_html)] -> rendered FAQ + FAQPage JSON-LD."""
    import re
    rows = []
    for q, a in qa:
        rows.append(
            '<details><summary>%s</summary><div class="answer">%s</div></details>'
            % (E(q), a)
        )
    ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer",
                                "text": re.sub(r"<[^>]+>", "", a).strip()}}
            for q, a in qa
        ],
    }
    return '<div class="faq">' + "".join(rows) + "</div>", jsonld(ld)


def page(path, title, description, body, extra_head="", crumbs=None,
         updated=None, structured=None):
    """Render one complete HTML page."""
    canonical = BASE_URL + path
    crumb_html, crumb_ld = breadcrumbs(crumbs) if crumbs else ("", "")

    nav_links = "".join(
        '<a href="%s"%s>%s</a>' % (
            E(url), ' aria-current="page"' if url == path else "", E(label))
        for url, label in NAV
    )
    footer_links = "".join(
        '<a href="%s">%s</a>' % (E(url), E(label)) for url, label in FOOTER_NAV
    )

    ld = [crumb_ld] if crumb_ld else []
    if structured:
        ld.extend(structured if isinstance(structured, list) else [structured])

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{site}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/styles.css">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
{ld}
{analytics}
{extra_head}
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="mark" href="/"><span class="chip" aria-hidden="true"></span>{site}</a>
    <nav class="site-nav" aria-label="Main">{nav}</nav>
    <span class="age-badge">21+</span>
  </div>
</header>
{crumbs}
<main>
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <nav class="footer-nav" aria-label="Footer">{footer}</nav>
    <p><strong>Affiliate disclosure:</strong> some outbound links on {site} are affiliate or referral links, and we may earn a commission or a sign-up bonus if you use them. They cost you nothing extra. Where we have such a link, we say so on the page and state what we receive. No commission, bonus or agreement changes a rating, a ranking, or a published number, and we publish unfavourable findings about platforms we earn from.</p>
    <p>{site} is independent and not affiliated with any platform listed here. Platform and product names are trademarks of their owners. Nothing here is financial or legal advice. Intended for adults; check your local laws before using any pack ripping site.{updated}</p>
    <p>&copy; 2026 {site}</p>
  </div>
</footer>
</body>
</html>
""".format(
        title=E(title), desc=E(description), canonical=E(canonical),
        site=E(SITE_NAME), nav=nav_links, footer=footer_links,
        body=body, extra_head=extra_head, crumbs=crumb_html,
        analytics=analytics_tag(),
        ld="\n".join(ld),
        updated=(" Data on this page collected %s." % updated) if updated else "",
    )
