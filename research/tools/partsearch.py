# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""Query JLCPCB's PCBA parts library and HQ Online (NextPCB Rev0's component
source) for a part, reporting stock and the unit price at 100 pieces.

Usage:
    uv run partsearch.py <keyword> [<keyword> ...]

For each keyword, prints JSON lines with the matching parts found on each
service.
"""

import html
import json
import re
import sys

import requests

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)

JLC_API = (
    "https://jlcpcb.com/api/overseas-pcb-order/v1/"
    "shoppingCart/smtGood/selectSmtComponentList"
)


def price_at(prices, qty):
    """Pick the unit price applying at the given order quantity from a list of
    {startNumber, endNumber, productPrice} tiers (endNumber -1 = no limit)."""
    for tier in prices:
        end = tier.get("endNumber", -1)
        if tier.get("startNumber", 0) <= qty and (end == -1 or qty <= end):
            return tier.get("productPrice")
    # Fall back to the lowest tier that starts below qty.
    best = None
    for tier in prices:
        if tier.get("startNumber", 0) <= qty:
            best = tier.get("productPrice")
    return best


def jlc_search(keyword, page_size=10):
    r = requests.post(
        JLC_API,
        json={"currentPage": 1, "pageSize": page_size, "keyword": keyword},
        headers={"User-Agent": UA},
        timeout=30,
    )
    r.raise_for_status()
    out = []
    for c in r.json()["data"]["componentPageInfo"]["list"]:
        out.append(
            {
                "service": "jlcpcb",
                "mpn": c["componentModelEn"],
                "brand": c["componentBrandEn"],
                "lcsc": c["componentCode"],
                "library": c["componentLibraryType"],  # base / expand
                "preferred": c.get("preferredComponentFlag"),
                "stock": c["stockCount"],
                "price@100": price_at(c.get("componentPrices") or [], 100),
                "url": "https://jlcpcb.com/partdetail/" + c["urlSuffix"],
                "datasheet": c.get("dataManualUrl"),
                "category": c.get("componentTypeEn"),
                "package": c.get("componentSpecificationEn"),
                "desc": (c.get("describe") or "")[:120],
            }
        )
    return out


def hq_search(keyword):
    r = requests.get(
        "https://www.hqonline.com/search/" + requests.utils.quote(keyword),
        headers={"User-Agent": UA},
        timeout=30,
    )
    r.raise_for_status()
    links = sorted(set(re.findall(r"product-detail/[a-z0-9-]+", r.text)))
    return [l for l in links if l != "product-detail"]


def hq_product(path):
    url = "https://www.hqonline.com/" + path
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    text = r.text
    info = {"service": "hqonline(nextpcb)", "url": url}
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
    if m:
        try:
            ld = json.loads(m.group(1))
            info["mpn"] = ld.get("mpn") or ld.get("sku")
            brand = ld.get("brand")
            info["brand"] = brand.get("name") if isinstance(brand, dict) else brand
            offers = ld.get("offers") or {}
            info["availability"] = (offers.get("availability") or "").rsplit("/", 1)[-1]
        except json.JSONDecodeError:
            pass
    m = re.search(r"ladder-price-table.*?</table>", text, re.S)
    if m:
        rows = re.findall(
            r"(\d+)\+.*?\$([0-9.]+)", html.unescape(re.sub(r"<[^>]+>", " ", m.group(0)))
        )
        tiers = [
            {"startNumber": int(q), "endNumber": -1, "productPrice": float(p)}
            for q, p in rows
        ]
        # Convert open-ended tiers into ranges so price_at picks the right one.
        for i in range(len(tiers) - 1):
            tiers[i]["endNumber"] = tiers[i + 1]["startNumber"] - 1
        info["price@100"] = price_at(tiers, 100)
        info["tiers"] = [(t["startNumber"], t["productPrice"]) for t in tiers]
    m = re.search(r"([\d,]+)\s*In Stock", text)
    if m:
        info["stock"] = int(m.group(1).replace(",", ""))
    if not info.get("mpn"):
        m = re.search(r"<title[^>]*>([^<|]+)", text)
        if m:
            info["mpn"] = m.group(1).strip()
    return info


def main():
    for keyword in sys.argv[1:]:
        print(f"### {keyword}")
        try:
            for part in jlc_search(keyword):
                print(json.dumps(part, ensure_ascii=False))
        except Exception as e:
            print(f"jlcpcb error: {e}")
        try:
            for path in hq_search(keyword)[:5]:
                if keyword.split()[0].lower().replace("-", "") not in path.replace("-", ""):
                    continue
                print(json.dumps(hq_product(path), ensure_ascii=False))
        except Exception as e:
            print(f"hqonline error: {e}")
        print()


if __name__ == "__main__":
    main()
