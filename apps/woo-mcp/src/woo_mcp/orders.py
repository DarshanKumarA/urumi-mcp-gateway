"""Store-local day windows and allowlisted REST order normalization."""

import re
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from .models import OrderDateWindow, OrderDetail, OrderSummary

SUMMARY_FIELDS = "id,status,date_created_gmt,currency,total,payment_method"
DETAIL_FIELDS = SUMMARY_FIELDS + ",line_items,shipping_lines,shipping_total,total_tax"


def resolve_date_window(value, timezone, *, now=None):
    if value is None:
        return None
    zone = ZoneInfo(timezone)
    if value == "today":
        instant = now if now is not None else datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("An aware clock is required.")
        day = instant.astimezone(zone).date()
    else:
        day = date.fromisoformat(value)
    start = datetime.combine(day, time.min, zone).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time.min, zone).astimezone(UTC)
    # Ensure the accepted strict-second lower bound is representable too.
    start - timedelta(seconds=1)
    return OrderDateWindow(date=day.isoformat(), timezone=timezone,
                           start_inclusive=start, end_exclusive=end)


def date_parameters(window):
    return {"dates_are_gmt": "true",
            "after": (window.start_inclusive - timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
            "before": window.end_exclusive.isoformat().replace("+00:00", "Z")}


def normalize_order(data, *, detail=False):
    if not isinstance(data, dict):
        raise ValueError()
    # Woo date_created_gmt has no suffix but is explicitly UTC, not host local time.
    raw_date = data["date_created_gmt"]
    if not isinstance(raw_date, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}", raw_date):
        raise ValueError()
    result = {key: data[key] for key in ("id", "status", "currency", "total", "payment_method")}
    result["created_at"] = datetime.fromisoformat(raw_date).replace(tzinfo=UTC)
    if not detail:
        return OrderSummary.model_validate(result)
    if not isinstance(data["line_items"], list) or not isinstance(data["shipping_lines"], list):
        raise ValueError()
    lines = []
    for item in data["line_items"]:
        line = {key: item[key] for key in ("product_id", "name", "sku", "quantity", "subtotal", "total")}
        variation = item["variation_id"]
        if type(variation) is not int or variation < 0:
            raise ValueError()
        line["variation_id"] = variation or None
        # Woo price is a JSON number (net line total / quantity). JSON is parsed
        # as Decimal upstream; no binary float or newly inferred catalog price.
        price = item["price"]
        if type(price) not in (int, Decimal) or not Decimal(price).is_finite():
            raise ValueError()
        if abs(Decimal(price).adjusted()) > 38 or abs(Decimal(price).as_tuple().exponent) > 38:
            raise ValueError()
        line["unit_price"] = format(Decimal(price), "f")
        lines.append(line)
    result.update(line_items=lines,
                  shipping_lines=[{key: item[key] for key in ("method_id", "method_title", "total")}
                                  for item in data["shipping_lines"]],
                  shipping_total=data["shipping_total"], tax_total=data["total_tax"])
    return OrderDetail.model_validate(result)
