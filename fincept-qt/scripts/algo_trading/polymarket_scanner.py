from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from polymarket_models import MarketCandidate


@dataclass
class SkippedMarket:
    market_id: str
    reason: str
    detail: str = ""


@dataclass
class ScanResult:
    candidates: list[MarketCandidate]
    skipped: list[SkippedMarket]


def scan_markets(markets: list[dict], config: dict, fetched_at: str) -> ScanResult:
    candidates: list[MarketCandidate] = []
    skipped: list[SkippedMarket] = []

    for market in markets:
        market_id = str(market.get("id") or "")
        skip_reason = _market_skip_reason(market, config, fetched_at)
        if skip_reason:
            skipped.append(SkippedMarket(market_id=market_id, reason=skip_reason))
            continue

        outcomes = _decode_list(market.get("outcomes"))
        prices = _decode_list(market.get("outcomePrices"))
        token_ids = _decode_list(market.get("clobTokenIds"))

        for index, outcome in enumerate(outcomes):
            token_id = str(token_ids[index]) if index < len(token_ids) else ""
            if not token_id:
                skipped.append(SkippedMarket(market_id=market_id, reason="missing_token"))
                continue

            price = _float_at(prices, index)
            if price is None or price < float(config.get("min_price", 0.0)) or price > float(config.get("max_price", 1.0)):
                skipped.append(SkippedMarket(market_id=market_id, reason="price_out_of_range"))
                continue

            candidates.append(
                MarketCandidate(
                    market_id=market_id,
                    condition_id=str(market.get("conditionId") or market.get("condition_id") or ""),
                    question=str(market.get("question") or ""),
                    outcome=str(outcome),
                    asset_id=token_id,
                    price=price,
                    volume=float(market.get("volume") or 0.0),
                    liquidity=float(market.get("liquidity") or 0.0),
                    end_date=str(market.get("endDate") or market.get("end_date") or ""),
                    fetched_at=fetched_at,
                    category=str(market.get("category") or ""),
                    tags=[str(tag) for tag in _decode_list(market.get("tags"))],
                    hours_to_expiry=_hours_to_expiry(market, fetched_at),
                )
            )

    return ScanResult(candidates=_sort_candidates(candidates, config), skipped=skipped)


def _market_skip_reason(market: dict, config: dict, fetched_at: str) -> str | None:
    if not market.get("active", False) or market.get("closed", False):
        return "closed"
    if float(market.get("volume") or 0.0) < float(config.get("min_volume", 0.0)):
        return "low_volume"
    if float(market.get("liquidity") or 0.0) < float(config.get("min_liquidity", 0.0)):
        return "low_liquidity"

    excluded_categories = {str(category).lower() for category in config.get("excluded_categories", [])}
    category = str(market.get("category") or "").lower()
    if category and category in excluded_categories:
        return "excluded_category"

    excluded_tags = {str(tag).lower() for tag in config.get("excluded_tags", [])}
    tags = {str(tag).lower() for tag in _decode_list(market.get("tags"))}
    if tags.intersection(excluded_tags):
        return "excluded_tag"

    hours = _hours_to_expiry(market, fetched_at)
    if hours is not None and hours < float(config.get("min_time_to_expiry_hours", 0.0)):
        return "near_expiry"

    return None


def _sort_candidates(candidates: list[MarketCandidate], config: dict) -> list[MarketCandidate]:
    sort_by = str(config.get("sort_by", "volume"))
    if sort_by == "liquidity":
        return sorted(candidates, key=lambda c: c.liquidity, reverse=True)
    if sort_by == "price":
        return sorted(candidates, key=lambda c: c.price)
    return sorted(candidates, key=lambda c: c.volume, reverse=True)


def _decode_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        return decoded if isinstance(decoded, list) else []
    return []


def _float_at(values: list, index: int) -> float | None:
    if index >= len(values):
        return None
    try:
        return float(values[index])
    except (TypeError, ValueError):
        return None


def _hours_to_expiry(market: dict, fetched_at: str) -> float | None:
    end_date = market.get("endDate") or market.get("end_date")
    if not end_date:
        return None
    end_dt = _parse_utc(str(end_date))
    fetched_dt = _parse_utc(fetched_at)
    if end_dt is None or fetched_dt is None:
        return None
    return (end_dt - fetched_dt).total_seconds() / 3600.0


def _parse_utc(value: str) -> datetime | None:
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
