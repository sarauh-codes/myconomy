"""Optional live check against the real OpenDOSM API.

Skipped by default so the suite never depends on the network. Run with:
    set RUN_LIVE_TESTS=1 && pytest tests/live

This makes a single request, which stays well inside the 4-per-minute limit.
"""

import os

import pytest

from app.services.dataset_registry import INDICATORS
from app.services.opendosm_client import OpenDOSMClient
from app.services.series_parser import parse_meta, parse_observations

pytestmark = pytest.mark.live

requires_live = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_TESTS") != "1",
    reason="Set RUN_LIVE_TESTS=1 to run live OpenDOSM checks.",
)


@requires_live
def test_cpi_headline_live_response_validates():
    spec = INDICATORS["cpi_headline"]
    client = OpenDOSMClient("https://api.data.gov.my/opendosm/", min_request_interval=0)

    envelope = client.fetch_series(spec.dataset_id, filter_expression=spec.filter_expression)
    observations = parse_observations(envelope, spec)
    meta = parse_meta(envelope)

    assert len(observations) > 500  # the headline series runs from 1980
    assert observations[0].reference_period.year == 1980
    assert meta.update_frequency == "MONTHLY"
    assert meta.data_as_of
