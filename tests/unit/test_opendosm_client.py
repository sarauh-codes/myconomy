"""Unit tests for the provider client. Network, sleeping, and time are all injected."""

import pytest
import requests

from app.services.opendosm_client import (
    ClientRequestError,
    MalformedResponse,
    OpenDOSMClient,
    RateLimited,
    UpstreamUnavailable,
)
from tests.helpers import FakeResponse, FakeSession, envelope


class Recorder:
    def __init__(self):
        self.sleeps: list[float] = []
        self.now = 1000.0

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def clock(self) -> float:
        return self.now


def make_client(session, recorder=None, *, max_retries=2, min_interval=0.0):
    recorder = recorder or Recorder()
    client = OpenDOSMClient(
        "https://example.test/opendosm/",
        connect_timeout=3,
        read_timeout=7,
        max_retries=max_retries,
        min_request_interval=min_interval,
        session=session,
        sleep=recorder.sleep,
        clock=recorder.clock,
    )
    return client, recorder


def test_request_uses_verified_parameters_and_timeouts():
    session = FakeSession(FakeResponse(200, envelope([])))
    client, _ = make_client(session)
    client.fetch_series("cpi_headline", filter_expression="overall@division")

    call = session.calls[0]
    assert call["url"] == "https://example.test/opendosm/"
    assert call["params"] == {
        "id": "cpi_headline",
        "limit": 10000,
        "meta": "true",
        "filter": "overall@division",
        "sort": "-date",
    }
    assert call["timeout"] == (3, 7)


def test_successful_response_is_returned():
    body = envelope([{"date": "2026-09-01", "index": 137.6, "division": "overall"}])
    client, _ = make_client(FakeSession(FakeResponse(200, body)))
    assert client.fetch_series("cpi_headline")["data"][0]["index"] == 137.6


def test_timeout_is_retried_then_succeeds():
    session = FakeSession(requests.Timeout("slow"), FakeResponse(200, envelope([])))
    client, recorder = make_client(session)
    client.fetch_series("cpi_headline")
    assert len(session.calls) == 2
    assert recorder.sleeps == [1]  # first backoff step


def test_connection_error_exhausts_retries():
    session = FakeSession(
        requests.ConnectionError("down"), requests.ConnectionError("down"), requests.ConnectionError("down")
    )
    client, recorder = make_client(session, max_retries=2)
    with pytest.raises(UpstreamUnavailable):
        client.fetch_series("cpi_headline")
    assert len(session.calls) == 3
    assert recorder.sleeps == [1, 2]  # exponential backoff


def test_server_error_is_retried_then_reported():
    session = FakeSession(FakeResponse(503), FakeResponse(500), FakeResponse(502))
    client, _ = make_client(session, max_retries=2)
    with pytest.raises(UpstreamUnavailable, match="server error"):
        client.fetch_series("cpi_headline")
    assert len(session.calls) == 3


def test_rate_limit_waits_then_retries_and_succeeds():
    session = FakeSession(FakeResponse(429), FakeResponse(200, envelope([])))
    client, recorder = make_client(session)
    client.fetch_series("cpi_headline")
    assert recorder.sleeps == [60]
    assert len(session.calls) == 2


def test_persistent_rate_limit_raises_rate_limited():
    session = FakeSession(FakeResponse(429), FakeResponse(429), FakeResponse(429))
    client, _ = make_client(session, max_retries=2)
    with pytest.raises(RateLimited):
        client.fetch_series("cpi_headline")


def test_client_error_is_not_retried():
    session = FakeSession(FakeResponse(404, {"status": 404, "errors": ["missing"]}))
    client, recorder = make_client(session)
    with pytest.raises(ClientRequestError, match="404"):
        client.fetch_series("nope")
    assert len(session.calls) == 1
    assert recorder.sleeps == []


def test_invalid_json_is_malformed_and_not_retried():
    session = FakeSession(FakeResponse(200, invalid_json=True))
    client, _ = make_client(session)
    with pytest.raises(MalformedResponse, match="invalid JSON"):
        client.fetch_series("cpi_headline")
    assert len(session.calls) == 1


@pytest.mark.parametrize("body", [[], {"data": []}, {"meta": {}, "data": None}, "text"])
def test_unexpected_envelope_shape_is_malformed(body):
    client, _ = make_client(FakeSession(FakeResponse(200, body)))
    with pytest.raises(MalformedResponse, match="unexpected response shape"):
        client.fetch_series("cpi_headline")


def test_requests_are_spaced_by_minimum_interval():
    session = FakeSession(FakeResponse(200, envelope([])), FakeResponse(200, envelope([])))
    client, recorder = make_client(session, min_interval=15)
    client.fetch_series("cpi_headline")
    client.fetch_series("cpi_headline")
    # The second call must wait out the rest of the 15-second window.
    assert recorder.sleeps == [15]
