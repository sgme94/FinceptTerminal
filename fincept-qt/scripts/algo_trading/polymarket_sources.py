import hashlib
import json
from pathlib import Path
from typing import Callable

import requests


ALLOWED_APIS = {
    "gamma": "https://gamma-api.polymarket.com",
    "clob": "https://clob.polymarket.com",
    "data": "https://data-api.polymarket.com",
}


def load_fixture(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_source_payload(payload: dict, allowed_api: str) -> dict:
    if payload.get("source_api") != allowed_api:
        raise ValueError("source_api is required and must be official Polymarket API")
    if not payload.get("fetched_at"):
        raise ValueError("fetched_at is required")
    if "data" not in payload:
        raise ValueError("data is required")
    return payload


def _payload_hash(data) -> str:
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class PolymarketRestSource:
    def __init__(self, now: Callable[[], str] | None = None, timeout: float = 15.0):
        self.session = requests.Session()
        self.now = now
        self.timeout = timeout

    def fetch_gamma_markets(self, *, limit: int, sort_by: str) -> dict:
        data = self._get_json(
            f"{ALLOWED_APIS['gamma']}/markets",
            params={
                "active": "true",
                "closed": "false",
                "limit": limit,
                "order": sort_by,
            },
        )
        return self._wrap(ALLOWED_APIS["gamma"], data)

    def fetch_clob_order_book(self, token_id: str) -> dict:
        data = self._get_json(
            f"{ALLOWED_APIS['clob']}/book",
            params={"token_id": token_id},
        )
        return self._wrap(ALLOWED_APIS["clob"], data)

    def _get_json(self, url: str, params: dict) -> dict | list:
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _wrap(self, source_api: str, data: dict | list) -> dict:
        payload = {
            "source_api": source_api,
            "fetched_at": self._now(),
            "source_payload_hash": _payload_hash(data),
            "data": data,
        }
        return validate_source_payload(payload, allowed_api=source_api)

    def _now(self) -> str:
        if self.now:
            return self.now()
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
