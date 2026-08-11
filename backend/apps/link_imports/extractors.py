from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from apps.link_imports.fetch import fetch_public


class _MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.json_ld: list[object] = []
        self.title = ""
        self.canonical = ""
        self._in_title = False
        self._json_buffer: list[str] | None = None
        self.price_candidates: list[str] = []
        self._price_depth = 0

    def handle_starttag(self, tag, attrs):
        values = {str(key).lower(): value or "" for key, value in attrs}
        if self._price_depth:
            self._price_depth += 1
        elif values.get("itemprop", "").lower() == "price" or values.get("data-locator", "").lower() == "product-price":
            candidate = values.get("content") or values.get("value")
            if candidate:
                self.price_candidates.append(candidate)
            self._price_depth = 1
        if tag.lower() == "meta":
            key = (values.get("property") or values.get("name") or values.get("itemprop") or "").lower()
            if key and values.get("content") and key not in self.meta:
                self.meta[key] = values["content"].strip()
        elif tag.lower() == "link" and values.get("rel", "").lower() == "canonical":
            self.canonical = values.get("href", "")
        elif tag.lower() == "title":
            self._in_title = True
        elif tag.lower() == "script" and "ld+json" in values.get("type", "").lower():
            self._json_buffer = []

    def handle_endtag(self, tag):
        if self._price_depth:
            self._price_depth -= 1
        if tag.lower() == "title":
            self._in_title = False
        elif tag.lower() == "script" and self._json_buffer is not None:
            try:
                self.json_ld.append(json.loads("".join(self._json_buffer)))
            except (json.JSONDecodeError, ValueError):
                pass
            self._json_buffer = None

    def handle_data(self, data):
        if self._json_buffer is not None:
            self._json_buffer.append(data)
        elif self._in_title:
            self.title += data
        if self._price_depth and data.strip():
            self.price_candidates.append(data.strip())


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _types(value) -> set[str]:
    raw = value.get("@type", []) if isinstance(value, dict) else []
    if isinstance(raw, str):
        raw = [raw]
    return {str(item).lower() for item in raw}


def _money(value) -> Decimal | None:
    if value is None:
        return None
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(value))
    if not match:
        return None
    try:
        amount = Decimal(match.group(0).replace(",", ""))
        return amount.quantize(Decimal("0.01")) if amount >= 0 else None
    except InvalidOperation:
        return None


def _image(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value:
        return _image(value[0])
    if isinstance(value, dict):
        return str(value.get("url") or value.get("contentUrl") or "")
    return ""


def _is_interstitial_title(value: str) -> bool:
    """Reject common bot/error-page titles without discarding useful partial metadata."""
    title = re.sub(r"\s+", " ", value).strip().casefold()
    exact = {
        "access denied",
        "attention required!",
        "bot verification",
        "pardon our interruption",
        "request unsuccessful",
        "security check",
        "temporarily unavailable",
    }
    return title in exact or title.startswith("just a moment")


def extract_product(url: str) -> dict:
    result = fetch_public(url)
    encoding = "utf-8"
    content_type = result.headers.get("content-type", "")
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    if match:
        encoding = match.group(1)
    html = result.content.decode(encoding, errors="replace")
    parser = _MetadataParser()
    parser.feed(html)

    product = None
    for root in parser.json_ld:
        product = next((row for row in _walk(root) if "product" in _types(row)), None)
        if product:
            break
    product = product or {}
    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    offers = offers if isinstance(offers, dict) else {}

    title = str(product.get("name") or parser.meta.get("og:title") or parser.title).strip()
    rejected_title = _is_interstitial_title(title)
    if rejected_title:
        title = ""
    image = _image(product.get("image")) or parser.meta.get("og:image", "")
    price = _money(
        offers.get("price") or offers.get("lowPrice")
        or parser.meta.get("product:price:amount")
        or next(iter(parser.price_candidates), None)
    )
    list_price = _money(
        offers.get("highPrice") or parser.meta.get("product:original_price:amount")
        or parser.meta.get("product:price:original_amount")
    )
    currency = str(offers.get("priceCurrency") or parser.meta.get("product:price:currency") or "AUD").upper()[:3]
    brand = product.get("brand") or ""
    if isinstance(brand, dict):
        brand = brand.get("name", "")
    site_name = parser.meta.get("og:site_name") or str(brand)
    retailer = site_name.strip() or (urlsplit(result.url).hostname or "").removeprefix("www.")
    canonical = urljoin(result.url, parser.canonical) if parser.canonical else result.url
    image = urljoin(result.url, image) if image else ""
    warnings: list[str] = []
    if rejected_title:
        warnings.append("The shop showed a security/interruption page, so its page title was ignored; enter the product name manually.")
    elif not title:
        warnings.append("The product name could not be found.")
    if price is None:
        warnings.append("The current price could not be found; enter it manually.")
    if not image:
        warnings.append("The product image could not be found; paste the image link manually if you want one.")
    return {
        "kind": "product", "source_url": canonical, "source_site": retailer,
        "title": title[:255], "retailer": retailer[:160], "image_url": image[:1000],
        "price": str(price) if price is not None else None,
        "list_price": str(list_price) if list_price is not None else None,
        "currency": currency or "AUD", "is_sale": bool(price is not None and list_price and price < list_price),
        "warnings": warnings,
    }
