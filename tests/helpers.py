"""Test doubles and sample payloads. No network access anywhere in the test suite."""

from __future__ import annotations

from typing import Any


def envelope(rows: list[dict[str, Any]], *, data_as_of: str = "2026-09") -> dict[str, Any]:
    """A response shaped like the verified OpenDOSM meta=true envelope."""
    return {
        "meta": {
            "catalogue_id": "cpi_headline",
            "data_as_of": data_as_of,
            "last_updated": "2026-10-19 13:12",
            "next_update": "2026-11-19 12:30",
            "data_source": ["DOSM"],
            "update_frequency": "MONTHLY",
            "total": len(rows),
            "filter": "overall@division",
        },
        "data": rows,
    }


def cpi_row(date: str, index: Any, division: str = "overall") -> dict[str, Any]:
    return {"date": date, "index": index, "division": division}


class FakeResponse:
    def __init__(self, status_code: int = 200, body: Any = None, *, invalid_json: bool = False):
        self.status_code = status_code
        self._body = body
        self._invalid_json = invalid_json

    def json(self) -> Any:
        if self._invalid_json:
            raise ValueError("No JSON object could be decoded")
        return self._body


class FakeSession:
    """Replays queued responses or exceptions and records every call."""

    def __init__(self, *items: Any):
        self.items = list(items)
        self.calls: list[dict[str, Any]] = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        if not self.items:
            raise AssertionError("FakeSession ran out of queued responses")
        item = self.items.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class StubClient:
    """Stands in for OpenDOSMClient at the service layer. Queued items are returned or raised."""

    def __init__(self, *items: Any):
        self.items = list(items)
        self.requested: list[str] = []

    def fetch_series(self, dataset_id, *, filter_expression=None, sort="-date", limit=10000):
        self.requested.append(dataset_id)
        item = self.items.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item
