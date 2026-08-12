from __future__ import annotations

import mimetypes
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone

from apps.attachments.services import create_attachment
from apps.core.models import get_active_household
from apps.link_imports.fetch import LinkFetchError, fetch_public
from apps.link_imports.models import LinkWatch, PriceObservation
from apps.nodes.selectors import get_node_by_key
from apps.notifications.services import notify_person


def cache_remote_image(
    *, acting_user, image_url: str, source_node: str, record_type: str, record_id: int,
    visibility: str = "household",
):
    result = fetch_public(
        image_url, accepted_types=("image",), max_bytes=5_000_000, timeout=8,
    )
    suffix = mimetypes.guess_extension(result.content_type) or Path(urlsplit(result.url).path).suffix or ".img"
    uploaded = SimpleUploadedFile(
        f"product-{record_id}{suffix[:8]}", result.content, content_type=result.content_type
    )
    return create_attachment(
        uploaded_file=uploaded, acting_user=acting_user,
        linked_node=get_node_by_key(source_node), linked_record_type=record_type,
        linked_record_id=record_id, visibility=visibility, sensitivity="normal",
    )


@transaction.atomic
def sync_watch(
    *, acting_user, owner_person, source_node: str, record_type: str, record_id: int,
    url: str, title: str, retailer: str, currency: str, price: Decimal, enabled: bool,
) -> LinkWatch | None:
    existing = LinkWatch.objects.filter(
        source_node=source_node, source_record_type=record_type,
        source_record_id=record_id, owner_person=owner_person,
    ).first()
    if not enabled:
        if existing:
            existing.is_active = False
            existing.updated_by = acting_user
            existing.save(update_fields=["is_active", "updated_by", "updated_at"])
        return existing
    defaults = {
        "url": url, "title": title, "retailer": retailer, "currency": currency or "AUD",
        "baseline_price": price, "current_price": price, "lowest_price": price,
        "is_active": True, "updated_by": acting_user,
    }
    if existing:
        for field, value in defaults.items():
            setattr(existing, field, value)
        existing.save()
        return existing
    return LinkWatch.objects.create(
        household=get_active_household(), source_node=source_node,
        source_record_type=record_type, source_record_id=record_id, owner_person=owner_person,
        created_by=acting_user, **defaults,
    )


def serialize_watch(watch: LinkWatch | None) -> dict | None:
    if watch is None:
        return None
    return {
        "id": watch.id, "is_active": watch.is_active, "rule": watch.rule,
        "threshold_percent": str(watch.threshold_percent),
        "target_price": str(watch.target_price) if watch.target_price is not None else None,
        "baseline_price": str(watch.baseline_price), "current_price": str(watch.current_price),
        "lowest_price": str(watch.lowest_price),
        "last_checked_at": watch.last_checked_at, "last_succeeded_at": watch.last_succeeded_at,
        "consecutive_failures": watch.consecutive_failures, "last_error": watch.last_error,
    }


def update_watch(acting_user, watch: LinkWatch, **data) -> LinkWatch:
    for field in {"is_active", "rule", "threshold_percent", "target_price"}:
        if field in data:
            setattr(watch, field, data[field])
    watch.updated_by = acting_user
    watch.save()
    return watch


def _qualifies(watch: LinkWatch, price: Decimal, list_price: Decimal | None, is_sale: bool) -> bool:
    if watch.rule == LinkWatch.Rule.EXPLICIT_SALE:
        return is_sale or bool(list_price and price < list_price)
    if watch.rule == LinkWatch.Rule.TARGET:
        return watch.target_price is not None and price <= watch.target_price
    reference = watch.last_notified_price or watch.baseline_price
    return price <= reference * (Decimal("1") - watch.threshold_percent / Decimal("100"))


def check_watch(watch: LinkWatch, *, previewer=None, now=None) -> bool:
    from apps.link_imports.extractors import extract_product
    previewer = previewer or extract_product
    now = now or timezone.now()
    watch.last_checked_at = now
    try:
        preview = previewer(watch.url)
        if preview.get("price") is None:
            raise LinkFetchError("The current price was not present on the page.")
        observed_currency = str(preview.get("currency") or watch.currency).upper()
        if observed_currency != watch.currency.upper():
            raise LinkFetchError("The website returned a different currency, so the prices were not compared.")
        price = Decimal(preview["price"])
        list_price = Decimal(preview["list_price"]) if preview.get("list_price") else None
        PriceObservation.objects.create(
            household=watch.household, watch=watch, observed_at=now, price=price,
            list_price=list_price, is_sale=bool(preview.get("is_sale")),
            created_by=watch.updated_by or watch.created_by, updated_by=watch.updated_by or watch.created_by,
        )
        qualifies = _qualifies(watch, price, list_price, bool(preview.get("is_sale")))
        new_alert = qualifies and (watch.last_notified_price is None or price < watch.last_notified_price)
        previous = watch.current_price
        watch.current_price = price
        watch.lowest_price = min(watch.lowest_price, price)
        watch.last_succeeded_at = now
        watch.consecutive_failures = 0
        watch.last_error = ""
        if new_alert:
            watch.last_notified_price = price
            notify_person(
                watch.owner_person, title=f"Price drop: {watch.title}",
                message=f"{watch.retailer or 'The shop'} dropped from ${previous} to ${price} {watch.currency}.",
                source_node=watch.source_node, action_url="/corners/%s?tab=lists" % watch.owner_person_id,
                category="wish_price_alerts",
            )
        watch.save()
        return new_alert
    except (LinkFetchError, ValueError, ArithmeticError, LookupError, TypeError) as exc:
        watch.consecutive_failures += 1
        watch.last_error = str(exc)[:255]
        watch.save(update_fields=["last_checked_at", "consecutive_failures", "last_error", "updated_at"])
        if watch.consecutive_failures == 3:
            notify_person(
                watch.owner_person, title=f"Price check unavailable: {watch.title}",
                message="HomeStack could not read this shop for three checks. The saved item is unchanged.",
                source_node=watch.source_node,
                action_url=f"/corners/{watch.owner_person_id}?tab=lists",
                category="wish_price_alerts",
            )
        return False
