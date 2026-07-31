import os
import re
import json
import zipfile

SITE_BASE = "https://lsvdealer.com"

# Shared Organization node reused across structured-data blocks.
ORG_SCHEMA = {
    "@type": "Organization",
    "name": "LSVDealer.com",
    "url": SITE_BASE + "/",
    "telephone": "1-844-844-6638",
    "email": "info@lsvdealer.com",
}

_STATE_ZIP = re.compile(r"^(.*),\s*([A-Za-z .]+),\s*([A-Z]{2})\s+(\d{5})$")


def _postal_address(address):
    """Parse a US address string into a schema.org PostalAddress dict."""
    m = _STATE_ZIP.match(address.strip())
    if m:
        street, city, state, zip_ = m.groups()
        return {
            "@type": "PostalAddress",
            "streetAddress": street.strip(),
            "addressLocality": city.strip(),
            "addressRegion": state.strip(),
            "postalCode": zip_.strip(),
            "addressCountry": "US",
        }
    return {"@type": "PostalAddress", "streetAddress": address.strip(),
            "addressCountry": "US"}


def _dealer_kind(dealer):
    """Classify a dealer as a physical location, nationwide, or service area."""
    address = (dealer["address"] or "").strip()
    if address and address.lower() != "nationwide":
        return "local"
    if address.lower() == "nationwide":
        return "nationwide"
    return "service"


def dealer_title(dealer):
    """Build a search-intent-matched, unique title tag for a dealer page."""
    name = dealer["name"]
    if "golf" in name.lower():
        return f"{name} – Street-Legal Golf Carts & LSVs | LSVDealer.com"
    if _dealer_kind(dealer) == "service":
        return f"{name} Golf Cart Dealers – Street-Legal LSVs | LSVDealer.com"
    return f"{name} Golf Cart Dealer – Street-Legal LSVs | LSVDealer.com"


def dealer_meta_description(dealer):
    """Build a unique, CTR-focused meta description for a dealer page."""
    name, phone = dealer["name"], dealer["phone"]
    kind = _dealer_kind(dealer)
    if kind == "local":
        desc = (f"Shop street-legal golf carts, LSVs & electric carts at our {name} "
                f"dealership. New & used models.")
    elif kind == "nationwide":
        desc = (f"Shop street-legal golf carts, LSVs & electric carts with {name}, "
                f"serving customers nationwide. New & used models.")
    else:
        desc = (f"Looking for a golf cart dealer in {name}? Shop street-legal golf "
                f"carts, LSVs & electric carts. New & used models.")
    if phone:
        desc += f" Call {phone} or get directions today."
    else:
        desc += " Contact us today."
    return desc


def dealer_faq_pairs(dealer):
    """Return location-specific (question, answer) pairs built from real data."""
    name = dealer["name"]
    kind = _dealer_kind(dealer)
    pairs = [(
        f"Does {name} sell street-legal golf carts?",
        (f"Yes. {name} sells street-legal low speed vehicles (LSVs) and electric golf "
         "carts equipped with headlights, turn signals, mirrors, seat belts, and a "
         "windshield for legal use on roads posted at 35 mph or less."),
    )]
    if kind == "local":
        pairs.append((f"Where is {name} located?",
                      f"{name} is located at {dealer['address']}."))
    elif kind == "nationwide":
        pairs.append((f"What areas does {name} serve?",
                      f"{name} serves customers across the United States."))
    else:
        pairs.append((f"What areas does {name} serve?",
                      f"{name} serves customers throughout {name} and the "
                      "surrounding region."))
    if dealer["phone"]:
        pairs.append((f"How do I contact {name}?",
                      f"Call {name} at {dealer['phone']} to check current golf cart "
                      "availability, pricing, and directions."))
    pairs.append((
        "Are low speed vehicles and golf carts street legal?",
        ("Low speed vehicles (LSVs) are street legal on most roads posted at 35 mph or "
         f"less when equipped with the required safety features. {name} can help you "
         "find a street-legal golf cart that meets your local requirements."),
    ))
    return pairs


def dealer_faq_section(dealer):
    """Return the FAQ HTML section plus FAQPage JSON-LD for a dealer page."""
    import html as _html
    pairs = dealer_faq_pairs(dealer)
    rows = "\n".join(
        f"                <h3>{_html.escape(q)}</h3>\n"
        f"                <p>{_html.escape(a)}</p>"
        for q, a in pairs
    )
    faq_obj = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in pairs
        ],
    }
    return (
        '<section class="dealer-faq">\n'
        "                <h2>Frequently Asked Questions</h2>\n"
        f"{rows}\n"
        "            </section>\n"
        '            <script type="application/ld+json">\n'
        + json.dumps(faq_obj, indent=2)
        + "\n            </script>"
    )


def dealer_jsonld(dealer):
    """Build AutoDealer JSON-LD structured data for a dealer page."""
    url = f'{SITE_BASE}/{dealer["filename"]}'
    obj = {
        "@context": "https://schema.org",
        "@type": "AutoDealer",
        "name": f'{dealer["name"]} - LSVDealer.com',
        "url": url,
        "parentOrganization": ORG_SCHEMA,
    }
    if dealer["phone"]:
        obj["telephone"] = dealer["phone"]
    if dealer["address"] and dealer["address"].lower() != "nationwide":
        obj["address"] = _postal_address(dealer["address"])
    elif dealer["address"].lower() == "nationwide":
        obj["areaServed"] = "United States"
    else:
        obj["areaServed"] = dealer["name"]
    if dealer["latlon"]:
        try:
            lat, lon = [p.strip() for p in dealer["latlon"].split(",")]
            if lat and lon:
                obj["geo"] = {"@type": "GeoCoordinates",
                              "latitude": lat, "longitude": lon}
        except ValueError:
            pass
    same_as = [dealer[k] for k in ("website", "facebook", "youtube", "pinterest")
               if dealer.get(k)]
    if same_as:
        obj["sameAs"] = same_as
    # Explicit product-category signals so search engines associate the page
    # with LSVs and golf carts (not generic auto/truck dealerships).
    obj["knowsAbout"] = ["Low Speed Vehicles", "Electric Golf Carts",
                         "Street-Legal Golf Carts", "Neighborhood Electric Vehicles"]
    obj["makesOffer"] = [
        {"@type": "Offer", "itemOffered": {
            "@type": "Product", "name": "Electric Low Speed Vehicle (LSV)",
            "category": "Low Speed Vehicle"}},
        {"@type": "Offer", "itemOffered": {
            "@type": "Product", "name": "Street-Legal Electric Golf Cart",
            "category": "Golf Cart"}},
    ]
    return json.dumps(obj, indent=2)


def dealer_breadcrumb_jsonld(dealer):
    """BreadcrumbList JSON-LD reinforcing the Home > Dealers > location taxonomy."""
    url = f'{SITE_BASE}/{dealer["filename"]}'
    obj = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home",
             "item": SITE_BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Find Dealers",
             "item": SITE_BASE + "/find-dealers.html"},
            {"@type": "ListItem", "position": 3, "name": dealer["name"],
             "item": url},
        ],
    }
    return json.dumps(obj, indent=2)


def dealer_breadcrumb_html(dealer):
    """Visible breadcrumb trail (must accompany the BreadcrumbList JSON-LD)."""
    import html as _html
    return ('<nav class="breadcrumb" aria-label="Breadcrumb">\n'
            '                <a href="index.html">Home</a> &rsaquo; '
            '<a href="find-dealers.html">Find Dealers</a> &rsaquo; '
            f'<span aria-current="page">{_html.escape(dealer["name"])}</span>\n'
            '            </nav>')


def dealer_category_link_html(dealer):
    """Contextual internal links from a dealer page to the LSV hub and the
    dealership directory (exact-match anchor text builds the hub's authority).
    State pages also deep-link to the hub's by-state section."""
    state_pages = {fn for _, fn, _ in STATE_DEALERSHIPS}
    extra = ""
    if dealer["filename"] in state_pages:
        extra = (' View all <a href="find-dealers.html#browse-dealerships-by-state">'
                 f'low speed vehicle dealerships in {dealer["name"]}</a> and nearby '
                 'states.')
    return ('<section class="category-link">\n'
            '                <p>New to low speed vehicles? Explore our guide to '
            '<a href="electric-lsv-vehicles.html">electric low speed vehicles for '
            'sale</a>, or <a href="find-dealers.html">find a low speed vehicle '
            f'dealership</a> near you.{extra}</p>\n'
            '            </section>')


def directory_itemlist_jsonld(dealer_list):
    """ItemList of AutoDealer entries for the dealership directory (find-dealers).

    Compact per-location records (name, url, telephone, address) suitable for a
    directory hub — the full AutoDealer markup lives on each dealer page."""
    items = []
    for i, d in enumerate(dealer_list, start=1):
        node = {
            "@type": "AutoDealer",
            "name": d["name"],
            "url": f'{SITE_BASE}/{d["filename"]}',
        }
        if d["phone"]:
            node["telephone"] = d["phone"]
        if d["address"] and d["address"].lower() != "nationwide":
            node["address"] = _postal_address(d["address"])
        else:
            node["areaServed"] = ("United States"
                                  if d["address"].lower() == "nationwide"
                                  else d["name"])
        items.append({"@type": "ListItem", "position": i, "item": node})
    obj = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Low Speed Vehicle Dealership Directory",
        "itemListElement": items,
    }
    return json.dumps(obj, indent=2)


# State-level dealer pages used by the find-dealers directory, the homepage
# "by state" grid, and the state-page back-links (single source of truth).
STATE_DEALERSHIPS = [
    ("Pennsylvania", "dealer-pennsylvania.html",
     "Serving Philadelphia, the Poconos, Scranton–Wilkes-Barre, and Hatfield with "
     "street-legal LSVs and electric golf carts."),
    ("New Jersey", "dealer-new-jersey.html",
     "Covering the Jersey Shore and beyond, including Ocean View and Pleasantville, "
     "with neighborhood-ready electric low speed vehicles."),
    ("Delaware", "dealer-delaware.html",
     "Dover-area and statewide street-legal golf carts and electric LSVs across the "
     "First State."),
    ("Virginia", "dealer-virginia.html",
     "From Virginia Beach and Portsmouth to Gloucester Point, serving coastal and "
     "inland communities with LSVs."),
    ("North Carolina", "dealer-north-carolina.html",
     "Raleigh-area and statewide LSV sales and service for neighborhoods, campuses, "
     "and resorts."),
    ("South Carolina", "dealer-south-carolina.html",
     "Orangeburg-area and statewide street-legal golf carts and electric low speed "
     "vehicles."),
    ("Florida", "dealer-florida.html",
     "Lecanto-area and statewide coverage for LSVs suited to Florida's planned "
     "communities and warm-weather driving."),
    ("Ohio", "dealer-ohio.html",
     "Swanton-area and statewide sales and service of electric low speed vehicles and "
     "utility carts."),
    ("Indiana", "dealer-indiana.html",
     "South Bend-area and statewide street-legal LSVs for campuses, communities, and "
     "job sites."),
    ("Maryland", "dealer-maryland.html",
     "Statewide coverage for street-legal golf carts and neighborhood electric "
     "vehicles."),
    ("New York", "dealer-new-york.html",
     "Statewide LSV sales and service for towns, campuses, and planned communities."),
]


def find_dealers_state_section_html():
    """The 'Browse All Low Speed Vehicle Dealerships by State' section for the hub."""
    import html as _html
    rows = "\n".join(
        f'                <li><a href="{fn}">Low speed vehicle dealerships in '
        f'{_html.escape(state)}</a> — {_html.escape(desc)}</li>'
        for state, fn, desc in STATE_DEALERSHIPS
    )
    return (
        '        <section class="content-section" id="browse-dealerships-by-state">\n'
        "            <h2>Browse All Low Speed Vehicle Dealerships by State</h2>\n"
        "            <p>Explore low speed vehicle dealerships by state below. Each "
        "regional page lists the authorized low speed vehicle dealerships serving that "
        "state, along with contact details and directions. Our network of low speed "
        "vehicle dealerships spans 11 states across the East Coast, Southeast, and "
        "Midwest.</p>\n"
        "            <ul>\n"
        f"{rows}\n"
        "            </ul>\n"
        "        </section>"
    )


def homepage_state_grid_html():
    """A card grid of state dealer pages with keyword-rich anchor text."""
    import html as _html
    cards = "\n".join(
        '                <div class="dealer-card">\n'
        f'                    <h3>Low Speed Vehicle Dealers in {_html.escape(state)}</h3>\n'
        f'                    <p>{_html.escape(desc)}</p>\n'
        f'                    <a href="{fn}" class="btn">View {_html.escape(state)} Dealers</a>\n'
        "                </div>"
        for state, fn, desc in STATE_DEALERSHIPS
    )
    return (
        '            <section id="dealers-by-state">\n'
        "                <h2>Low Speed Vehicle Dealers by State</h2>\n"
        "                <p>Find certified low speed vehicle dealers in your state:</p>\n"
        '                <div class="dealer-grid">\n'
        f"{cards}\n"
        "                </div>\n"
        "            </section>"
    )


def dealer_head_extras(dealer):
    """Return meta description, canonical link, and JSON-LD for a dealer <head>."""
    desc = dealer_meta_description(dealer).replace('"', "&quot;")
    url = f'{SITE_BASE}/{dealer["filename"]}'
    return (f'<meta name="description" content="{desc}">\n'
            f'        <link rel="canonical" href="{url}">\n'
            f'        <script type="application/ld+json">\n{dealer_jsonld(dealer)}\n'
            f'        </script>\n'
            f'        <script type="application/ld+json">\n'
            f'{dealer_breadcrumb_jsonld(dealer)}\n        </script>')

# Dealer info as dictionaries
dealers = [
    {
        "filename": "dealer-tigon.html",
        "name": "TIGON National",
        "phone": "1-844-844-6638",
        "address": "Nationwide",
        "latlon": "",
        "cid": "https://www.google.com/maps?cid=913687030872245288",
        "facebook": "https://www.facebook.com/Tigongolfcarts",
        "youtube": "https://www.youtube.com/@TigonGolfCarts",
        "website": "https://tigongolfcarts.com",
        "pinterest": "https://www.pinterest.com/tigongolfcarts/",
        "review": "https://g.page/r/CSiEBX-DEa4MEBM/review"
    },
    {
        "filename": "dealer-dover-de.html",
        "name": "Dover, DE",
        "phone": "302-546-0010",
        "address": "5158 N Dupont Hwy, Dover, DE 19901",
        "latlon": "39.22044318468275, -75.57452048907642",
        "cid": "https://www.google.com/maps?cid=12843447677705895190",
        "facebook": "https://www.facebook.com/TigonGolfCartsDover/",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsDoverDE",
        "website": "https://tigongolfcarts.com/dover/",
        "pinterest": "",
        "review": "https://g.page/r/CRa9-YidFz2yEBM/review"
    },
    {
        "filename": "dealer-pocono-pa.html",
        "name": "Pocono, PA",
        "phone": "570-643-0152",
        "address": "1712 Pennsylvania 940, Pocono Pines, PA 18350",
        "latlon": "41.10286354605563, -75.48758590250345",
        "cid": "https://www.google.com/maps?cid=17137841834562046914",
        "facebook": "https://www.facebook.com/TigonGolfCartsPoconos/",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsPoconosPA",
        "website": "https://tigongolfcarts.com/pocono/",
        "pinterest": "",
        "review": "https://g.page/r/CcJL5i1Z2NXtEBM/review"
    },
    {
        "filename": "dealer-ocean-view-nj.html",
        "name": "Ocean View, NJ",
        "phone": "609-840-0404",
        "address": "101 NJ-50, Ocean View, NJ 08230",
        "latlon": "39.22254797811702, -74.70417212536503",
        "cid": "https://www.google.com/maps?cid=6446924254429489274",
        "facebook": "https://www.facebook.com/TigonGolfCartsOceanView/",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsOceanViewNJ",
        "website": "https://tigongolfcarts.com/ocean-view/",
        "pinterest": "",
        "review": "https://g.page/r/CXqoHr9zE3hZEBM/review"
    },
    {
        "filename": "dealer-hatfield-pa.html",
        "name": "Hatfield, PA",
        "phone": "215-595-8736",
        "address": "2333 Bethlehem Pike, Hatfield, PA 19440",
        "latlon": "40.29839945958623, -75.28308913039525",
        "cid": "https://www.google.com/maps?cid=8221925612164093496",
        "facebook": "https://www.facebook.com/TigonGolfCartsHatfield/",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsHatfieldPA",
        "website": "https://tigongolfcarts.com/hatfield/",
        "pinterest": "",
        "review": "https://g.page/r/CTgWulrIJRpyEBM/review"
    },
    {
        "filename": "dealer-scranton-wilkes-barre-pa.html",
        "name": "Scranton-Wilkes-Barre, PA",
        "phone": "570-344-4443",
        "address": "1225 N Keyser Ave #2, Scranton, PA 18504",
        "latlon": "41.4374075,-75.6835104",
        "cid": "https://www.google.com/maps?cid=13243686786001524416",
        "facebook": "https://www.facebook.com/TigonGolfCartsScranton/",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsScrantonWilkesPA",
        "website": "https://tigongolfcarts.com/scranton-wilkes-barre/",
        "pinterest": "",
        "review": "https://g.page/r/CcDWJ7z2Bsu3EBM/review"
    },
    {
        "filename": "dealer-raleigh-nc.html",
        "name": "Raleigh, NC",
        "phone": "984-489-0298",
        "address": "2700 S Wilmington St, Raleigh, NC 27603",
        "latlon": "35.7471032,-78.6452007",
        "cid": "https://www.google.com/maps?cid=14570072271497929915",
        "facebook": "https://www.facebook.com/TigonGolfCartsRaleigh/",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsRaleighNC",
        "website": "https://tigongolfcarts.com/raleigh/",
        "pinterest": "https://www.pinterest.com/tigongolfcarts/tigon-golf-carts-in-raleigh/",
        "review": "https://g.page/r/CbskZw6JSzPKEBM/review"
    },
    {
        "filename": "dealer-orangeburg-sc.html",
        "name": "Orangeburg, SC",
        "phone": "803-596-0246",
        "address": "4166 North Rd, Orangeburg, SC 29118",
        "latlon": "33.547201,-80.9162039",
        "cid": "https://www.google.com/maps?cid=17192321019507936230",
        "facebook": "https://www.facebook.com/TigonGolfCartsOrangeburg/",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsOrangeburgSC",
        "website": "https://tigongolfcarts.com/orangeburg/",
        "pinterest": "",
        "review": ""
    },
    {
        "filename": "dealer-swanton-oh.html",
        "name": "Swanton, OH",
        "phone": "419-402-8400",
        "address": "10420 AIrport Hwy, Swanton, OH 43558",
        "latlon": "41.6013184,-83.7926472",
        "cid": "https://www.google.com/maps?cid=16517552730289967239",
        "facebook": "https://www.facebook.com/TigonGolfCartsSwanton/",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsSwantonOH",
        "website": "https://tigongolfcarts.com/swanton/",
        "pinterest": "",
        "review": "https://g.page/r/CYeQt8exIjrlEBM/review"
    },
    {
        "filename": "dealer-south-bend-in.html",
        "name": "South Bend, IN",
        "phone": "574-703-0456",
        "address": "52129 State Road 933, South Bend, IN 46637",
        "latlon": "41.7360283,-86.2511865",
        "cid": "https://www.google.com/maps?cid=17532455648086849827",
        "facebook": "https://www.facebook.com/TigonGolfCartsSouthBend/",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsSouthBendIN",
        "website": "https://tigongolfcarts.com/south-bend/",
        "pinterest": "",
        "review": ""
    },
    {
        "filename": "dealer-gloucester-point-va.html",
        "name": "Gloucester Point, VA",
        "phone": "804-792-0234",
        "address": "2810 George Washington Memorial Hwy, Gloucester Point, VA 23072",
        "latlon": "37.2850625,-76.5074161",
        "cid": "https://www.google.com/maps?cid=16682967888503617377",
        "facebook": "https://www.facebook.com/TigonGolfCartsGloucesterPoint/",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsGloucesterPoint",
        "website": "https://tigongolfcarts.com/gloucester-point/",
        "pinterest": "",
        "review": ""
    },
    {
        "filename": "dealer-lecanto-fl.html",
        "name": "Lecanto, FL",
        "phone": "352-453-0345",
        "address": "299 E. Gulf to Lake Hwy, Lecanto, FL 34461",
        "latlon": "28.858622,-82.4295381",
        "cid": "https://www.google.com/maps?cid=4773802157529013859",
        "facebook": "https://www.facebook.com/TigonGolfCartsLecanto/",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsLecantoFL",
        "website": "https://tigongolfcarts.com/lecanto/",
        "pinterest": "",
        "review": "https://g.page/r/CWOeggPF8z9CEBM/review"
    },
    {
        "filename": "dealer-pleasantville-nj.html",
        "name": "Pleasantville, NJ",
        "phone": "640-444-3094",
        "address": "7000 Black Horse Pike, Pleasantville, NJ 08232",
        "latlon": "39.38812835576412, -74.5186949022294",
        "cid": "https://www.google.com/maps?cid=7635149767591436869",
        "facebook": "https://www.facebook.com/TigonGolfCartPleasantville",
        "youtube": "",
        "website": "https://tigongolfcarts.com/pleasantville/",
        "pinterest": "https://www.pinterest.com/tigongolfcarts/tigon-golf-carts-in-pleasantville-nj/",
        "review": "https://g.page/r/CUWiMchCgPVpEBM/review"
    },
    {
        "filename": "dealer-portsmouth-va.html",
        "name": "Portsmouth, VA",
        "phone": "757-977-0146",
        "address": "2008 Portsmouth Blvd, Portsmouth, VA 23704",
        "latlon": "36.817786,-76.3235434",
        "cid": "https://www.google.com/maps?cid=5113923461119431468",
        "facebook": "https://www.facebook.com/TigonGolfCartsPortsmouthVA/",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsPortsmouthVA",
        "website": "https://tigongolfcarts.com/portsmouth/",
        "pinterest": "",
        "review": "https://g.page/r/CSxTjwxLTvhGEBM/review"
    },
    {
        "filename": "dealer-virginia-beach-va.html",
        "name": "Virginia Beach, VA",
        "phone": "1-844-844-6638",
        "address": "1101 Virginia Beach Blvd, Virginia Beach, VA 23451",
        "latlon": "36.8414381,-75.9965854",
        "cid": "https://www.google.com/maps?cid=17806490138133315425",
        "facebook": "https://www.facebook.com/TigonGolfCartsVirginiaBeach/",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsVirginiaBeachVA",
        "website": "https://tigongolfcarts.com/virginia-beach/",
        "pinterest": "",
        "review": ""
    },
    {
        "filename": "dealer-tristate.html",
        "name": "TriState Golf Cars",
        "phone": "",
        "address": "",
        "latlon": "",
        "cid": "",
        "facebook": "",
        "youtube": "",
        "website": "",
        "pinterest": "",
        "review": "https://g.page/r/CcfFABSQEz-VEBM/review"
    },
    # Service states (next 12)
    {
        "filename": "dealer-pennsylvania.html",
        "name": "Pennsylvania",
        "phone": "1-844-844-6638",
        "address": "",
        "latlon": "41.1169824,-77.6047047",
        "cid": "https://www.google.com/maps?cid=13935683838976847185",
        "facebook": "",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsPennsylvania",
        "website": "https://tigongolfcarts.com/pennsylvania/",
        "pinterest": "",
        "review": "https://g.page/r/CVHtXfydfmXBEBM/review"
    },
    {
        "filename": "dealer-new-jersey.html",
        "name": "New Jersey",
        "phone": "1-844-844-6638",
        "address": "",
        "latlon": "40.073132,-74.724323",
        "cid": "https://www.google.com/maps?cid=15178469885958324473",
        "facebook": "",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsNewJersey",
        "website": "https://tigongolfcarts.com/new-jersey/",
        "pinterest": "",
        "review": "https://g.page/r/CfmAgjrxwaTSEBM/review"
    },
    {
        "filename": "dealer-delaware.html",
        "name": "Delaware",
        "phone": "1-844-844-6638",
        "address": "",
        "latlon": "39.145324,-75.386594",
        "cid": "https://www.google.com/maps?cid=11044789483047204293",
        "facebook": "",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsDelaware",
        "website": "https://tigongolfcarts.com/delaware/",
        "pinterest": "",
        "review": "https://g.page/r/CcW1_1uE-UaZEBM/review"
    },
    {
        "filename": "dealer-virginia.html",
        "name": "Virginia",
        "phone": "1-844-844-6638",
        "address": "",
        "latlon": "37.5334624,-78.866703",
        "cid": "https://www.google.com/maps?cid=6737760967527982175",
        "facebook": "",
        "youtube": "https://www.youtube.com/@TigonGolfCartsVirginia",
        "website": "https://tigongolfcarts.com/virginia/",
        "pinterest": "",
        "review": "https://g.page/r/CV9k_9rmVYFdEBM/review"
    },
    {
        "filename": "dealer-north-carolina.html",
        "name": "North Carolina",
        "phone": "1-844-844-6638",
        "address": "",
        "latlon": "",
        "cid": "",
        "facebook": "",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsNorthCarolina",
        "website": "https://tigongolfcarts.com/north-carolina/",
        "pinterest": "",
        "review": ""
    },
    {
        "filename": "dealer-south-carolina.html",
        "name": "South Carolina",
        "phone": "1-844-844-6638",
        "address": "",
        "latlon": "",
        "cid": "",
        "facebook": "",
        "youtube": "",
        "website": "https://tigongolfcarts.com/south-carolina/",
        "pinterest": "",
        "review": ""
    },
    {
        "filename": "dealer-florida.html",
        "name": "Florida",
        "phone": "1-844-844-6638",
        "address": "",
        "latlon": "27.698638,-83.804601",
        "cid": "https://www.google.com/maps?cid=15821077580647342669",
        "facebook": "",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsFlorida",
        "website": "https://tigongolfcarts.com/florida/",
        "pinterest": "",
        "review": "https://g.page/r/CU2iYWY8wo_bEBM/review"
    },
    {
        "filename": "dealer-indiana.html",
        "name": "Indiana",
        "phone": "1-844-844-6638",
        "address": "",
        "latlon": "",
        "cid": "",
        "facebook": "",
        "youtube": "",
        "website": "https://tigongolfcarts.com/indiana/",
        "pinterest": "",
        "review": "https://g.page/r/CU_4NMYL3ORdEBM/review"
    },
    {
        "filename": "dealer-ohio.html",
        "name": "Ohio",
        "phone": "1-844-844-6638",
        "address": "",
        "latlon": "40.3633984,-82.669505",
        "cid": "https://www.google.com/maps?cid=7815966071951211924",
        "facebook": "",
        "youtube": "",
        "website": "https://tigongolfcarts.com/ohio/",
        "pinterest": "",
        "review": "https://g.page/r/CZQ9KE-743dsEBM/review"
    },
    {
        "filename": "dealer-maryland.html",
        "name": "Maryland",
        "phone": "1-844-844-6638",
        "address": "",
        "latlon": "",
        "cid": "",
        "facebook": "",
        "youtube": "https://www.youtube.com/@TIGONGolfCartsMaryland",
        "website": "https://tigongolfcarts.com/maryland/",
        "pinterest": "",
        "review": "https://g.page/r/CeRBOVZDpiHzEBM/review"
    },
    {
        "filename": "dealer-philadelphia.html",
        "name": "Philadelphia",
        "phone": "1-844-844-6638",
        "address": "",
        "latlon": "40.0024979,-75.1180146",
        "cid": "https://www.google.com/maps?cid=6103352888615501339",
        "facebook": "",
        "youtube": "",
        "website": "",
        "pinterest": "",
        "review": "https://g.page/r/CRv-x4Add7NUEBM/review"
    },
    {
        "filename": "dealer-new-york.html",
        "name": "New York",
        "phone": "1-844-844-6638",
        "address": "",
        "latlon": "",
        "cid": "",
        "facebook": "",
        "youtube": "",
        "website": "",
        "pinterest": "",
        "review": "https://g.page/r/Ca-zWbvWZcPcEBM/review"
    },
]

# Dealer H2s/content generator
def dealer_content(dealer):
    content = f'''
    <h2>Why Choose {dealer["name"]} for Your Low Speed Vehicle?</h2>
    <p>
        {dealer["name"]} offers specialized sales and service for low speed vehicles (LSVs) and electric golf carts.
        Customers benefit from knowledgeable staff, convenient location, and a selection of street-legal vehicles for every lifestyle.
        Whether you need a new LSV for your neighborhood, business, or recreation, {dealer["name"]} delivers value and peace of mind.
    </p>
    <h2>Dealer Info & Contact</h2>
    <ul>
        <li><strong>Phone:</strong> {dealer["phone"] if dealer["phone"] else "Call for details"}</li>
        <li><strong>Address:</strong> {dealer["address"] if dealer["address"] else "Service Area: " + dealer["name"]}</li>
        {"<li><strong>Website:</strong> <a href='%s' target='_blank'>Visit Dealer Site</a></li>" % dealer["website"] if dealer["website"] else ""}
        {"<li><strong>Facebook:</strong> <a href='%s' target='_blank'>Facebook</a></li>" % dealer["facebook"] if dealer["facebook"] else ""}
        {"<li><strong>YouTube:</strong> <a href='%s' target='_blank'>YouTube</a></li>" % dealer["youtube"] if dealer["youtube"] else ""}
        {"<li><strong>Pinterest:</strong> <a href='%s' target='_blank'>Pinterest</a></li>" % dealer["pinterest"] if dealer["pinterest"] else ""}
    </ul>
    <h2>Low Speed Vehicle Options</h2>
    <p>
        At {dealer["name"]}, we offer a variety of low speed vehicles to meet your specific needs:
    </p>
    <ul>
        <li><strong>Street Legal Golf Carts:</strong> Perfect for neighborhood transportation</li>
        <li><strong>Electric Utility Vehicles:</strong> Ideal for work sites and property maintenance</li>
        <li><strong>Personal Transportation Vehicles:</strong> Comfortable, efficient community travel</li>
        <li><strong>Custom LSVs:</strong> Tailored to your specific requirements</li>
    </ul>
    <h2>Benefits of Low Speed Vehicles</h2>
    <p>
        Low speed vehicles offer numerous advantages over traditional transportation options:
    </p>
    <ul>
        <li>Eco-friendly electric operation</li>
        <li>Lower operating costs than conventional vehicles</li>
        <li>Street-legal on roads with speed limits up to 35 mph</li>
        <li>Easy parking and maneuverability</li>
        <li>Reduced carbon footprint</li>
        <li>Community-friendly transportation</li>
    </ul>
    {"<h2>Visit Our Location</h2><p>Come visit our showroom at %s to see our selection of low speed vehicles and speak with our knowledgeable staff.</p>" % dealer["address"] if dealer["address"] else ""}
    {"<h2>Leave a Review</h2><p>Had a great experience? <a href='%s' target='_blank'>Leave us a review</a> to let others know!</p>" % dealer["review"] if dealer["review"] else ""}
    '''
    return content

# Generate HTML files
def generate_html_files():
    # Create index.html
    index_html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LSV Dealer – Certified Low Speed Vehicle Dealers Nationwide</title>
        <meta name="description" content="Find street-legal golf carts and low speed vehicles (LSVs) from authorized dealers near you. Shop electric carts &amp; NEVs nationwide — browse dealers and call today.">
        <link rel="canonical" href="https://lsvdealer.com/">
        <link rel="stylesheet" href="css/styles.css">
        <script type="application/ld+json">
        [
          {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "LSVDealer.com",
            "url": "https://lsvdealer.com/",
            "telephone": "1-844-844-6638",
            "email": "info@lsvdealer.com",
            "description": "Directory of authorized low speed vehicle (LSV) dealers across the United States."
          },
          {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "LSVDealer.com",
            "url": "https://lsvdealer.com/"
          }
        ]
        </script>
    </head>
    <body>
        <header>
            <div class="container">
                <h1>LSVDealer.com</h1>
                <p>Your nationwide electric LSV &amp; low speed vehicle dealership network</p>
            </div>
        </header>

        <nav>
            <div class="container">
                <ul>
                    <li><a href="index.html">Home</a></li>
                    <li><a href="about.html">About LSVs</a></li>
                    <li><a href="electric-lsv-vehicles.html">Electric LSVs</a></li>
                    <li><a href="find-dealers.html">Find Dealers</a></li>
                    <li><a href="contact.html">Contact</a></li>
                </ul>
            </div>
        </nav>

        <main class="container">
            <section id="hero">
                <h1>America's Network of Certified Low Speed Vehicle Dealers</h1>
                <p>LSVDealer.com connects buyers with authorized low speed vehicle dealers across the United States. Browse our network of trusted LSV dealers in <a href="find-dealers.html">Pennsylvania, New Jersey, Delaware, Virginia, Florida, and more</a>.</p>
            </section>
            
            <section id="about">
                <h2>About Low Speed Vehicles</h2>
                <p>Low Speed Vehicles (LSVs) are electric vehicles that can travel at speeds of 20-25 mph. They are street legal on roads with posted speed limits of 35 mph or less in most states. LSVs offer an eco-friendly, cost-effective transportation alternative for neighborhoods, planned communities, campuses, and small towns.</p>
                <p>All street-legal LSVs include required safety features such as headlights, turn signals, mirrors, windshield, seat belts, and more. They provide convenient transportation with lower operating costs than traditional vehicles.</p>
            </section>
            
            <section id="dealers">
                <h2>Our Dealer Network</h2>
                <p>Find a low speed vehicle dealer near you:</p>
                
                <div class="dealer-grid">
    '''
    
    # Add dealer cards to index.html
    for dealer in dealers:
        dealer_card = f'''
                    <div class="dealer-card">
                        <h3>{dealer["name"]}</h3>
                        <p>{dealer["address"] if dealer["address"] else "Service Area: " + dealer["name"]}</p>
                        <p>{dealer["phone"] if dealer["phone"] else ""}</p>
                        <a href="{dealer["filename"]}" class="btn">View Dealer</a>
                    </div>
        '''
        index_html += dealer_card
    
    # Complete index.html
    index_html += '''
                </div>
            </section>
            
            <section id="contact">
                <h2>Contact Us</h2>
                <p>For general inquiries about our dealer network:</p>
                <p>Email: <!--email_off--><a href="mailto:info@lsvdealer.com">info@lsvdealer.com</a><!--/email_off--></p>
                <p>Phone: 1-844-844-6638</p>
            </section>
        </main>
        
        <footer>
            <div class="container">
                <p>&copy; 2025 LSVDealer.com - All Rights Reserved</p>
            </div>
        </footer>
    </body>
    </html>
    '''
    
    # Inject the keyword-rich "by state" grid ahead of the full dealer network.
    index_html = index_html.replace(
        '            <section id="dealers">',
        homepage_state_grid_html() + '\n\n            <section id="dealers">', 1)

    # Write index.html
    with open('index.html', 'w') as f:
        f.write(index_html)
    
    # Generate individual dealer pages
    for dealer in dealers:
        dealer_html = f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{dealer_title(dealer)}</title>
            <link rel="stylesheet" href="css/styles.css">
            {dealer_head_extras(dealer)}
        </head>
        <body>
            <header>
                <div class="container">
                    <h1>LSVDealer.com</h1>
                    <p>Your Source for Low Speed Vehicle Dealers Nationwide</p>
                </div>
            </header>
            
            <nav>
                <div class="container">
                    <ul>
                        <li><a href="index.html">Home</a></li>
                        <li><a href="about.html">About LSVs</a></li>
                        <li><a href="electric-lsv-vehicles.html">Electric LSVs</a></li>
                        <li><a href="find-dealers.html">Find Dealers</a></li>
                        <li><a href="contact.html">Contact</a></li>
                    </ul>
                </div>
            </nav>

            <main class="container">
                {dealer_breadcrumb_html(dealer)}

                <section class="dealer-header">
                    <h1>{dealer["name"]}</h1>
                    <p class="subtitle">Golf Cart &amp; Low Speed Vehicle (LSV) Dealer</p>
                    {f'<a href="{dealer["cid"]}" target="_blank" class="map-link">View on Google Maps</a>' if dealer["cid"] else ""}
                </section>

                <section class="dealer-content">
                    {dealer_content(dealer)}
                </section>

                {dealer_category_link_html(dealer)}

                {dealer_faq_section(dealer)}

                <section class="back-link">
                    <a href="index.html#dealers">&larr; Back to All Dealers</a>
                </section>
            </main>
            
            <footer>
                <div class="container">
                    <p>&copy; 2025 LSVDealer.com - All Rights Reserved</p>
                </div>
            </footer>
        </body>
        </html>
        '''
        
        # Write dealer page
        with open(f'{dealer["filename"]}', 'w') as f:
            f.write(dealer_html)

# Call the function to generate HTML files
if __name__ == "__main__":
    generate_html_files()
