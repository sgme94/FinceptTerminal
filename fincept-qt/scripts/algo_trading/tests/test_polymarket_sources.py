import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from polymarket_sources import (
    PolymarketRestSource,
    load_fixture,
    validate_source_payload,
)


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_fixture_requires_source_metadata():
    payload = load_fixture(FIXTURE_DIR / "polymarket_gamma_markets.json")

    assert payload["source_api"] == GAMMA_API
    assert payload["fetched_at"]
    assert isinstance(payload["data"], list)
    assert validate_source_payload(payload, allowed_api=GAMMA_API) is payload


def test_unlabeled_market_data_is_rejected():
    with pytest.raises(ValueError, match="source_api"):
        validate_source_payload({"data": []}, allowed_api=GAMMA_API)


def test_wrong_source_api_is_rejected():
    payload = {
        "source_api": CLOB_API,
        "fetched_at": "2026-04-30T00:00:00Z",
        "data": [],
    }

    with pytest.raises(ValueError, match="source_api"):
        validate_source_payload(payload, allowed_api=GAMMA_API)


def test_payload_without_fetched_at_is_rejected():
    with pytest.raises(ValueError, match="fetched_at"):
        validate_source_payload({"source_api": GAMMA_API, "data": []}, allowed_api=GAMMA_API)


def test_payload_without_data_is_rejected():
    with pytest.raises(ValueError, match="data"):
        validate_source_payload(
            {"source_api": GAMMA_API, "fetched_at": "2026-04-30T00:00:00Z"},
            allowed_api=GAMMA_API,
        )


def test_rest_source_wraps_gamma_markets_with_metadata(monkeypatch):
    calls = []
    source = PolymarketRestSource(now=lambda: "2026-04-30T00:00:00Z")

    def fake_get(url, params=None, timeout=None):
        calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse([{"id": "market-1"}])

    monkeypatch.setattr(source.session, "get", fake_get)

    payload = source.fetch_gamma_markets(limit=10, sort_by="volume")

    assert calls[0]["url"] == f"{GAMMA_API}/markets"
    assert calls[0]["params"]["active"] == "true"
    assert calls[0]["params"]["closed"] == "false"
    assert calls[0]["params"]["limit"] == 10
    assert calls[0]["params"]["order"] == "volume"
    assert payload["source_api"] == GAMMA_API
    assert payload["fetched_at"] == "2026-04-30T00:00:00Z"
    assert payload["source_payload_hash"]
    assert payload["data"] == [{"id": "market-1"}]


def test_rest_source_wraps_clob_order_book_with_metadata(monkeypatch):
    calls = []
    source = PolymarketRestSource(now=lambda: "2026-04-30T00:00:00Z")

    def fake_get(url, params=None, timeout=None):
        calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse({"asset_id": "yes-token-1", "bids": [], "asks": []})

    monkeypatch.setattr(source.session, "get", fake_get)

    payload = source.fetch_clob_order_book("yes-token-1")

    assert calls[0]["url"] == f"{CLOB_API}/book"
    assert calls[0]["params"]["token_id"] == "yes-token-1"
    assert payload["source_api"] == CLOB_API
    assert payload["fetched_at"] == "2026-04-30T00:00:00Z"
    assert payload["source_payload_hash"]
    assert payload["data"]["asset_id"] == "yes-token-1"
