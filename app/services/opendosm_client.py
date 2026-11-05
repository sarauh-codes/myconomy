"""HTTP client for the OpenDOSM API.

This is the only module that talks to the network. Everything else works with
the dictionaries it returns.

Behaviour, based on the verified provider documentation:
- Requests carry explicit connect and read timeouts.
- Responses are requested with `meta=true`, which returns {"meta": ..., "data": [...]}.
- The published limit is 4 requests per minute. Requests are spaced out
  by at least `min_request_interval` seconds.
- 429 (rate limited) waits for a full minute before retrying.
- Timeouts, connection errors, and 5xx responses are retried with exponential backoff.
- Other 4xx responses are client errors and are never retried.
- Invalid JSON is reported as a malformed response.

Limitation: the spacing is enforced per process. Several worker processes
would each have their own spacing, so the scheduled job should run as a single process.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)

RATE_LIMIT_WAIT_SECONDS = 60


class OpenDOSMError(Exception):
    """Base class for provider errors. Messages are safe to store and display."""


class UpstreamUnavailable(OpenDOSMError):
    """Timeouts, connection failures, or server errors that did not clear after retries."""


class RateLimited(OpenDOSMError):
    """HTTP 429 that did not clear after the allowed retry."""


class ClientRequestError(OpenDOSMError):
    """HTTP 4xx other than 429. Retrying will not help."""


class MalformedResponse(OpenDOSMError):
    """The response body is not valid JSON or does not have the expected envelope."""


class OpenDOSMClient:
    def __init__(
        self,
        base_url: str,
        *,
        connect_timeout: float = 5.0,
        read_timeout: float = 15.0,
        max_retries: int = 2,
        min_request_interval: float = 15.0,
        session: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.base_url = base_url
        self.timeout = (connect_timeout, read_timeout)
        self.max_retries = max_retries
        self.min_request_interval = min_request_interval
        self._session = session or requests.Session()
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: float | None = None

    def fetch_series(
        self,
        dataset_id: str,
        *,
        filter_expression: str | None = None,
        sort: str | None = "-date",
        limit: int = 10000,
    ) -> dict[str, Any]:
        """Return the parsed envelope {"meta": {...}, "data": [...]} for one dataset."""
        params: dict[str, Any] = {"id": dataset_id, "limit": limit, "meta": "true"}
        if filter_expression:
            params["filter"] = filter_expression
        if sort:
            params["sort"] = sort
        return self._get_json(params)

    # Internal helpers

    def _get_json(self, params: dict[str, Any]) -> dict[str, Any]:
        attempt = 0
        while True:
            self._respect_rate_limit()
            try:
                response = self._session.get(self.base_url, params=params, timeout=self.timeout)
            except (requests.Timeout, requests.ConnectionError) as exc:
                logger.warning("OpenDOSM request failed (%s) for dataset %s", type(exc).__name__, params.get("id"))
                if attempt >= self.max_retries:
                    raise UpstreamUnavailable("The statistics service did not respond in time.") from exc
                self._sleep(2**attempt)
                attempt += 1
                continue

            status = response.status_code
            if status == 200:
                return self._parse_envelope(response)

            if status == 429:
                logger.warning("OpenDOSM rate limit hit for dataset %s", params.get("id"))
                if attempt >= self.max_retries:
                    raise RateLimited("The statistics service is rate limiting requests. Try again later.")
                self._sleep(RATE_LIMIT_WAIT_SECONDS)
                attempt += 1
                continue

            if 500 <= status < 600:
                logger.warning("OpenDOSM server error %s for dataset %s", status, params.get("id"))
                if attempt >= self.max_retries:
                    raise UpstreamUnavailable("The statistics service returned a server error.")
                self._sleep(2**attempt)
                attempt += 1
                continue

            if 400 <= status < 500:
                logger.warning("OpenDOSM rejected request with status %s for dataset %s", status, params.get("id"))
                raise ClientRequestError(f"The statistics service rejected the request (status {status}).")

            raise UpstreamUnavailable(f"Unexpected status from the statistics service ({status}).")

    def _respect_rate_limit(self) -> None:
        now = self._clock()
        if self._last_request_at is not None:
            elapsed = now - self._last_request_at
            wait = self.min_request_interval - elapsed
            if wait > 0:
                self._sleep(wait)
        self._last_request_at = self._clock()

    @staticmethod
    def _parse_envelope(response: Any) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError as exc:
            raise MalformedResponse("The statistics service returned invalid JSON.") from exc

        if not isinstance(body, dict) or not isinstance(body.get("meta"), dict) or not isinstance(body.get("data"), list):
            raise MalformedResponse("The statistics service returned an unexpected response shape.")
        return body


def client_from_config(config: Any) -> OpenDOSMClient:
    """Build a client from Flask app.config settings."""
    return OpenDOSMClient(
        config["OPENDOSM_BASE_URL"],
        connect_timeout=config["OPENDOSM_CONNECT_TIMEOUT"],
        read_timeout=config["OPENDOSM_READ_TIMEOUT"],
        max_retries=config["OPENDOSM_MAX_RETRIES"],
        min_request_interval=config["OPENDOSM_MIN_REQUEST_INTERVAL"],
    )
