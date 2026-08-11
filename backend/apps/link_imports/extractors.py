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


def _isbn(value) -> str:
    """Return a normalised ISBN-10/13 from retailer text or structured metadata."""
    if isinstance(value, (list, tuple)):
        for item in value:
            found = _isbn(item)
            if found:
                return found
        return ""
    if isinstance(value, dict):
        return _isbn(value.get("isbn") or value.get("value") or value.get("identifier"))
    for candidate in re.findall(r"(?:97[89][\d\s-]{10,16}|[\d][\d\s-]{7,12}[\dXx])", str(value or "")):
        cleaned = re.sub(r"[^0-9Xx]", "", candidate).upper()
        if len(cleaned) in {10, 13}:
            return cleaned
    return ""


def _book_payload(value: dict, *, source_url="", source_site="") -> dict:
    authors = value.get("author") or value.get("authors") or []
    if isinstance(authors, (str, dict)):
        authors = [authors]
    author_names = []
    for author in authors:
        name = author.get("name", "") if isinstance(author, dict) else str(author)
        if name and name not in author_names:
            author_names.append(name)
    subjects = value.get("subjects") or value.get("genre") or value.get("categories") or []
    if isinstance(subjects, (str, dict)):
        subjects = [subjects]
    genres = []
    for subject in subjects:
        name = subject.get("name", "") if isinstance(subject, dict) else str(subject)
        if name and name not in genres:
            genres.append(name)
    cover = value.get("cover") or value.get("image") or value.get("imageLinks") or {}
    if isinstance(cover, dict):
        cover = cover.get("large") or cover.get("medium") or cover.get("thumbnail") or cover.get("small") or cover.get("url") or ""
    pages = value.get("number_of_pages") or value.get("numberOfPages") or value.get("pageCount")
    try:
        pages = int(pages) if pages else None
    except (TypeError, ValueError):
        pages = None
    return {
        "kind": "book", "source_url": source_url, "source_site": source_site,
        "title": str(value.get("title") or value.get("name") or "").strip()[:255],
        "author": ", ".join(author_names)[:255], "publication_date": str(value.get("publish_date") or value.get("datePublished") or value.get("publishedDate") or "")[:32],
        "pages": pages, "genre": ", ".join(genres[:3])[:120],
        "isbn": _isbn(value.get("isbn") or value.get("identifiers") or value.get("industryIdentifiers") or value.get("sku") or value.get("gtin13")),
        "description": str(value.get("description") or value.get("notes") or "").strip()[:5000],
        "cover_url": str(_image(cover))[:1000], "warnings": [],
    }


def extract_book(query: str) -> dict:
    """Preview a book from an ISBN or a safely fetched public book/product page."""
    raw = (query or "").strip()
    is_url = raw.lower().startswith(("http://", "https://"))
    direct: dict = {}
    isbn = _isbn(raw) if not is_url else ""
    if is_url:
        result = fetch_public(raw)
        html = result.content.decode("utf-8", errors="replace")
        parser = _MetadataParser(); parser.feed(html)
        structured = None
        for root in parser.json_ld:
            structured = next((row for row in _walk(root) if _types(row) & {"book", "product"}), None)
            if structured:
                break
        structured = structured or {}
        direct = _book_payload(
            structured,
            source_url=urljoin(result.url, parser.canonical) if parser.canonical else result.url,
            source_site=parser.meta.get("og:site_name") or (urlsplit(result.url).hostname or "").removeprefix("www."),
        )
        if not direct["title"]:
            title = parser.meta.get("og:title") or parser.title
            direct["title"] = "" if _is_interstitial_title(title) else title.strip()[:255]
        if not direct["cover_url"] and parser.meta.get("og:image"):
            direct["cover_url"] = urljoin(result.url, parser.meta["og:image"])
        elif direct["cover_url"]:
            direct["cover_url"] = urljoin(result.url, direct["cover_url"])
        isbn = direct["isbn"] or _isbn(structured) or _isbn(html)
    if not isbn:
        if direct.get("title"):
            direct["warnings"] = ["No ISBN was found, so only metadata exposed by the page could be filled."]
            return direct
        raise LinkFetchError("No ISBN or usable book metadata could be found.")

    api_url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    result = fetch_public(api_url, accepted_types=("application/json",), max_bytes=500_000)
    try:
        payload = json.loads(result.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LinkFetchError("The book catalogue returned invalid metadata.") from exc
    catalogue = payload.get(f"ISBN:{isbn}") or {}
    enriched = _book_payload(catalogue, source_url=direct.get("source_url", ""), source_site=direct.get("source_site", "Open Library"))
    enriched["isbn"] = isbn
    for key in ("title", "author", "publication_date", "pages", "genre", "description", "cover_url"):
        if not enriched.get(key) and direct.get(key):
            enriched[key] = direct[key]
    warnings = []
    if not catalogue:
        warnings.append("The ISBN was not found in Open Library; review the details found on the source page.")
    for label, key in (("title", "title"), ("author", "author"), ("page count", "pages"), ("publication date", "publication_date"), ("cover", "cover_url")):
        if not enriched.get(key):
            warnings.append(f"The {label} was not available; enter it manually if known.")
    enriched["warnings"] = warnings
    return enriched


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
