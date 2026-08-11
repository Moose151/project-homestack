# Core Spec — Safe Link Import & Enrichment

> **Status:** Product slice shipped in v0.31.0 and URL/ISBN book enrichment shipped in v0.34.1.
> Initial consumers are Homestead room-plan products, Atlas personal shopping/wish items and Books;
> Hearth recipe import remains a later adapter. This
> is preview-and-confirm enrichment, not a blind generic web scraper.

## 1. Purpose

Let a user paste an ordinary public product, book or recipe URL—or a bare ISBN for a book—and receive an editable draft populated
with the useful information exposed by that page.

For products, attempt: title, retailer/site name, price, currency and primary image. For recipes,
attempt: title, author/site, image, ingredients, method/instruction steps, preparation/cooking/
total time, yield/servings and source URL. Missing or ambiguous fields remain blank and editable.
The linked page is provenance, but the user-confirmed HomeStack record becomes the saved source of
truth; imports never overwrite later manual corrections automatically.

For books, accept either ISBN-10/ISBN-13 or a public retailer/publisher/catalogue URL. Prefer an
ISBN exposed by Schema.org `Book`/`Product` metadata, then enrich the exact edition from the public
Open Library Books API. Attempt title, authors, publication date as published (year or full date),
page count, subjects/genre, description, cover and source URL. This remains a user-triggered,
rate-limited lookup; Open Library is not used as HomeStack's persistent database.

## 2. User experience

Product lists in Homestead and Atlas gain **Paste product link**. Books gains **Book link or
ISBN**, always followed by the same review-before-save flow. Hearth later gains **Import recipe link**.

```text
Paste a link
┌────────────────────────────────────────────────────────────┐
│ https://shop.example/item                                  │
└────────────────────────────────────────────────────────────┘
                         [Get details]

Review imported details
┌───────────┐  Name      Oak bedside table
│  image    │  Shop      Example Store
│  preview  │  Price     $149.00 AUD
└───────────┘  Source    shop.example                [Open]

             [Cancel] [Save item]
```

The result is always a review form. Show which fields were found, warnings (price missing,
currency mismatch, blocked image) and an **Open source** action. A partial result is success: the
user can finish it manually. Never create a list/product/recipe record merely because a URL was
fetched.

## 3. Extraction order

Use stable public metadata before brittle page-specific selectors:

1. Parse Schema.org JSON-LD (`Product`, `Offer`, `AggregateOffer`, `Recipe`, `Organization`).
2. Parse Open Graph/product metadata (`og:title`, `og:image`, product price/currency fields).
3. Parse ordinary title, canonical URL, site name and narrowly defined meta fallbacks.
4. Optional reviewed per-domain adapters only for important household retailers/sites whose
   public structured data is consistently incomplete.

Do not begin with a headless browser. JavaScript-only, authenticated, CAPTCHA-protected or bot-
blocked pages return an honest partial/manual result. Extraction failures must never prevent
manual item entry.

## 4. Shared service contract

Implement one backend-owned `link_imports` service with context adapters, rather than scraper code
inside each node. A suggested endpoint is:

```text
POST /api/v1/link-imports/preview/
{ "url": "https://…", "kind": "product" | "recipe" }
{ "query": "https://… or ISBN", "kind": "book" }
```

It returns an ephemeral normalised preview plus field-level provenance/warnings. Saving happens
through the ordinary Homestead, Atlas or future Hearth endpoint after the user edits/confirms.
Keep `source_url`, canonical URL where available, source site and `imported_at` on the resulting
record; do not persist raw HTML. Strip fragments and known tracking parameters without destroying
a retailer's meaningful product variant.

Product consumers should share a small field contract (`title`, `source_url`, `source_site`,
`image`, `price`, `currency`) even if their owning models differ. Recipe is a separate adapter
because ingredients/instructions are domain data, not generic metadata.

## 5. Network and security boundary

Fetching an arbitrary user-provided URL creates an SSRF boundary and must be server-side and deny
by default:

- Accept only `http`/`https`; reject embedded credentials, non-standard ports and malformed hosts.
- Resolve DNS and reject loopback, private, link-local, multicast, reserved and metadata-service
  addresses for IPv4 and IPv6. Connect to the validated address and protect against DNS rebinding.
- Revalidate every redirect target; cap redirects, connection/read time, response bytes and
  decompressed bytes; accept only expected HTML/JSON/image content types.
- Use a recognisable fixed user agent, rate-limit per user/household/domain and limit concurrency.
- Never forward browser cookies, HomeStack sessions, authentication headers or arbitrary request
  headers. Never fetch `localhost`, Docker/service names, LAN devices or Home Assistant.
- Redact credentials/tokens/query secrets from errors, audit metadata and logs.
- Test alternate numeric IP forms, IPv6, redirect-to-private, DNS changes, oversized/compressed
  responses, slow responses and deceptive content types before enabling the feature.

This safety layer must also wrap image retrieval. Do not treat an image URL found in page metadata
as automatically safe.

## 6. Images, prices and provenance

Retailer hotlinking is unreliable. After the user confirms an import, fetch the chosen
image through the same safe client and store a bounded local copy through the shared attachment/
media service, recording its source and content hash. Enforce image type, pixel/byte limits and
remove the cached copy when no saved record references it. If copying is disabled or fails, keep
the remote URL with the existing visible blocked-image fallback. Local copying after confirmation
is the settled default; previewing alone must not permanently copy the image.

Price is a snapshot, not live pricing. Preserve currency, show when it was imported and require
confirmation before mapping it to a model that assumes household currency. A future **Refresh
from source** action must preview differences and never silently replace a chosen/actual cost.
Daily observations for a watched wish are stored separately from the user-confirmed estimate.

Keep a clear source link and attribution for imported recipes. Import for personal household use
does not justify republishing a site's images or text; release documentation must acknowledge
site terms and allow a domain to be disabled.

## 7. Daily price watch and sale notifications

Wishlist/personal-list product items with a public source URL may enable **Watch price**. The
default for an imported wish may be on, but it must be visible and individually switchable. A
watch records the source reference, owner Person, canonical URL, currency, imported/baseline
price, latest observed price, lowest observed price, last checked/succeeded/notified timestamps,
failure state and notification rule. It does not modify a Homestead chosen/actual cost, a Solace
amount or a Meridian point cost.

Offer three understandable rules:

- **When it is marked on sale** — structured data exposes a current price below a list/original
  price.
- **Any meaningful price drop** — recommended default; initially 5% below the baseline or last
  notified price, avoiding repeated alerts for cent-level changes.
- **At or below my target** — user supplies a price in the item's currency.

Notify only on a new qualifying state/new low, not every daily check at the same sale price. The
notification names the item, old/current price and shop and deep-links to the saved wish. The item
owner and any explicit watchers receive it; never notify the entire household automatically.
Record a compact price history so the UI can show “$149 → $119 · checked today” and explain why
the alert fired. If the page stops exposing a comparable product/variant/currency, mark the check
uncertain instead of inventing a price.

Run checks once per local day at approximately **9:00 am in the configured Household timezone**.
Under D5, use an idempotent Django scheduled command invoked by cron rather than an in-process
timer. It may run hourly and claim watches only after 09:00 whose `last_checked_on` is before the
local date; this safely catches up after a brief server outage. Batch/jitter requests per domain,
respect rate limits and reuse conditional requests where sites support them. A database claim/
lock prevents duplicate work. After repeated failures, show “Price check unavailable” on the
item and send at most one failure notice—not daily noise. Move to M7 background infrastructure
only if real watch volume makes sequential cron work inadequate.

Recommended host cron (the command itself applies the Household-local 09:00 and once-per-day gate):

```cron
7 * * * * docker exec homestack-backend python manage.py link_imports_run_scheduled
```

## 8. Delivery slices

1. **Safe fetch foundation:** URL validator, pinned/revalidated request client, limits, rate
   limiting, audit-safe errors and adversarial SSRF tests.
2. **Product preview:** JSON-LD/Open Graph extraction, editable preview, Homestead room-plan
   product integration, then Atlas shopping/wish integration.
3. **Reliable media and provenance:** confirmed image caching decision, source metadata,
   lifecycle cleanup, duplicate URL hinting and explicit refresh preview.
4. **Price watch:** shared watch records, 09:00 household-local idempotent command, compact price
   history, sale/drop/target rules, notification deduplication and failure/status UI.
5. **Hearth recipe adapter:** Schema.org Recipe parsing into editable ingredients and ordered
   method steps, with times/yield/image/source. Build only with the Hearth data model so an import
   cannot dictate a poor recipe schema.
6. **Evidence-driven adapters:** add a retailer/recipe-site adapter only after real URLs show that
   structured metadata is inadequate and the maintenance cost is justified.
7. **Books adapter (shipped v0.34.1):** safely extract page ISBN/Book metadata, enrich through Open
   Library, show partial-field warnings and save only the user-reviewed fields.

## 9. Acceptance gate

Across a representative set of public shop URLs, a user can paste a link, review title/shop/
price/image, correct it and save one source-owned item from Homestead or Atlas. Partial and blocked
sites degrade to manual entry. Security tests prove no route to localhost, private/LAN/container/
metadata addresses through direct URLs, DNS or redirects. Later, representative recipe links
produce editable structured drafts without overwriting user edits or claiming unsupported data.
A watched wish is checked once after 09:00 household-local time, a qualifying lower price creates
one actionable notification, an unchanged price does not repeat it, and downtime can catch up
without duplicate checks or notifications.

## 10. Settled owner decisions (2026-08-11)

1. Product images are copied locally **after confirmation** for dependable display.
2. The confirmed imported price is an informational snapshot; background observations and alerts
   never silently overwrite saved/chosen/actual costs.
3. Watched wishlist URLs are checked once daily at approximately **09:00 household-local time**
   and notify their owner when a qualifying sale/drop is detected.

The owner supplied eight Australian retailer acceptance URLs and approved the recommended 5%
“meaningful drop” default. Retailers that block or omit metadata continue through the editable
manual-entry path; target-price and explicit-sale rules remain available.
