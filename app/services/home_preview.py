"""The live product preview on the home page: the latest stored CPI values as a small chart.

The preview is built from the same stored data the dashboard uses, so it shows the real product
rather than an illustration. Nothing here is typed in by hand. If no data is stored, the preview says so.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from markupsafe import Markup

from .dashboard_service import load_points, summarise
from .data_service import get_snapshot
from .dataset_registry import INDICATORS, format_period

PREVIEW_CODE = "cpi_headline"
PREVIEW_MONTHS = 24
WIDTH = 480
HEIGHT = 170
PAD_LEFT = 40
PAD_RIGHT = 56
PAD_TOP = 12
PAD_BOTTOM = 26


@dataclass(frozen=True)
class Preview:
    available: bool
    name: str
    latest_text: str
    change_text: str
    period_text: str
    retrieved_text: str
    status_text: str
    chart: Markup | None
    message: str


def _svg(values: list[tuple[str, Decimal]], unit: str) -> Markup:
    """A simple line chart as inline SVG. Only numbers and formatted dates go into the markup."""
    lows = min(v for _, v in values)
    highs = max(v for _, v in values)
    span = float(highs - lows) or 1.0
    plot_w = WIDTH - PAD_LEFT - PAD_RIGHT
    plot_h = HEIGHT - PAD_TOP - PAD_BOTTOM
    count = len(values)

    def xy(index: int, value: Decimal) -> tuple[float, float]:
        x = PAD_LEFT + (plot_w * index / max(count - 1, 1))
        y = PAD_TOP + plot_h * (1 - float(value - lows) / span)
        return round(x, 1), round(y, 1)

    points = [xy(i, v) for i, (_, v) in enumerate(values)]
    path = "M " + " L ".join(f"{x} {y}" for x, y in points)
    last_x, last_y = points[-1]
    first_label, last_label = values[0][0], values[-1][0]
    top_label = f"{float(highs):.1f}"
    bottom_label = f"{float(lows):.1f}"
    return Markup(
        f'<svg class="preview-chart" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="Line chart of the last {count} stored values, from {first_label} to {last_label}. '
        f'Values range from {bottom_label} to {top_label} {unit}.">'
        f'<line class="preview-guide" x1="{PAD_LEFT}" y1="{PAD_TOP}" x2="{WIDTH - PAD_RIGHT}" y2="{PAD_TOP}"/>'
        f'<line class="preview-guide" x1="{PAD_LEFT}" y1="{PAD_TOP + plot_h}" x2="{WIDTH - PAD_RIGHT}" y2="{PAD_TOP + plot_h}"/>'
        f'<text x="0" y="{PAD_TOP + 4}">{top_label}</text>'
        f'<text x="0" y="{PAD_TOP + plot_h + 4}">{bottom_label}</text>'
        f'<text x="{PAD_LEFT}" y="{HEIGHT - 4}">{first_label}</text>'
        f'<text x="{WIDTH - PAD_RIGHT}" y="{HEIGHT - 4}" text-anchor="end">{last_label}</text>'
        f'<path class="preview-line" d="{path}"/>'
        f'<circle class="preview-end" cx="{last_x}" cy="{last_y}" r="4"/>'
        "</svg>"
    )


def home_preview() -> Preview:
    spec = INDICATORS[PREVIEW_CODE]
    snapshot = get_snapshot(PREVIEW_CODE)
    all_points = load_points(spec)
    observed = [p for p in all_points if p.value is not None][-PREVIEW_MONTHS:]
    if not observed:
        return Preview(
            available=False,
            name=spec.name,
            latest_text="No data yet",
            change_text="",
            period_text="",
            retrieved_text="Not yet",
            status_text="Unavailable",
            chart=None,
            message="Run the data refresh to load the latest figures.",
        )

    summary = summarise(all_points, spec)
    change = (
        f"{summary.yoy_change_pct:+.1f}% over 12 months"
        if summary.yoy_change_pct is not None
        else "12-month change not yet available"
    )
    series = [(format_period(p.period, spec.frequency), p.value) for p in observed]
    return Preview(
        available=True,
        name=spec.name,
        latest_text=f"{snapshot.latest_value:.1f}",
        change_text=change,
        period_text=format_period(snapshot.latest_period, spec.frequency),
        retrieved_text=snapshot.retrieved_at.strftime("%Y-%m-%d %H:%M") + " UTC" if snapshot.retrieved_at else "Not yet",
        status_text={"fresh": "Current", "stale": "Stale"}.get(snapshot.status, "Unavailable"),
        chart=_svg(series, spec.unit),
        message=snapshot.status_message,
    )
