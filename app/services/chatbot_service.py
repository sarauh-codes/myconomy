"""Economic chatbot: answers supported questions from verified stored data.

Rules (requirements FR-06):
- Numbers come only from the stored data layer. Each figure carries its
  reference period and source. The chatbot never invents a figure.
- If the data is missing, the answer says so.
- Concept questions are answered from the reviewed learning content, not generated text.
- Questions outside the supported topics get a scope message, not a guess.
- Requests for personal financial advice are declined.
- Personal records are never read or sent anywhere. This module does not import them.
- The user's text is treated as data, never as instructions. Nothing it says can change
  the rules above, because the answers are assembled from stored values and fixed text.

Intent detection is deliberately simple keyword matching. It is easy to test and
to explain. Anything it does not recognise gets the scope message.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal

from .dashboard_service import load_points, summarise
from .data_service import get_snapshot
from .dataset_registry import INDICATORS, format_period
from .learning_content import TOPICS

logger = logging.getLogger(__name__)

MAX_QUESTION_LENGTH = 300

ADVICE_WORDS = (
    "should i invest",
    "invest in",
    "buy shares",
    "buy stock",
    "sell shares",
    "stock",
    "crypto",
    "bitcoin",
    "tax",
    "loan",
    "mortgage",
    "financial advice",
    "what should i do with my money",
)

INDICATOR_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("unemployment_rate", ("unemployment", "jobless", "unemployed")),
    ("gdp_real_level", ("gdp level", "size of the economy", "real gdp level", "output level")),
    ("gdp_growth_yoy", ("gdp", "economic growth", "growth", "gross domestic product")),
    ("cpi_headline", ("cpi", "consumer price", "inflation", "prices", "cost of living")),
]

CHANGE_WORDS = ("change", "rate", "inflation", "12-month", "12 month", "year on year", "year-on-year", "growth", "increase", "rising", "rise")
CONCEPT_WORDS = ("what is", "what are", "explain", "define", "meaning of", "what does", "how does")
# Asking for a current value is a data question, even if it names a concept ("what is the latest inflation rate").
DATA_WORDS = ("latest", "current", "now", "today", "this month", "last month", "figure", "value", "number", "rate", "how much")
CONCEPT_TOPICS = {
    "cpi": ("cpi", "consumer price index"),
    "inflation": ("inflation",),
    "purchasing-power": ("purchasing power",),
}


@dataclass(frozen=True)
class Source:
    label: str
    url: str


@dataclass(frozen=True)
class ChatAnswer:
    kind: str  # data | change | concept | refusal | scope | unavailable | too_long | empty
    text: str
    sources: tuple[Source, ...] = ()
    links: tuple[tuple[str, str], ...] = field(default_factory=tuple)


def normalise_question(raw: str | None) -> str:
    text = (raw or "").strip()
    # Drop control characters; keep ordinary punctuation so the question reads naturally.
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    return re.sub(r"\s+", " ", text)


def answer(raw_question: str | None) -> ChatAnswer:
    question = normalise_question(raw_question)
    if not question:
        return ChatAnswer(kind="empty", text="Type a question about Malaysian economic statistics.")
    if len(question) > MAX_QUESTION_LENGTH:
        return ChatAnswer(
            kind="too_long",
            text=f"Please keep questions under {MAX_QUESTION_LENGTH} characters.",
        )

    lowered = question.lower()
    if any(word in lowered for word in ADVICE_WORDS):
        return ChatAnswer(
            kind="refusal",
            text=(
                "I can't give personal financial advice. I can explain the economic figures on this site, "
                "such as inflation or unemployment, with their sources."
            ),
            links=(("Learn about inflation", "/learn/inflation"),),
        )

    concept = _concept_answer(lowered)
    if concept is not None:
        return concept

    code = _detect_indicator(lowered)
    if code is None:
        return _scope_answer()

    spec = INDICATORS[code]
    if any(word in lowered for word in CHANGE_WORDS) and spec.shows_changes:
        return _change_answer(code)
    return _latest_answer(code)


def _detect_indicator(lowered: str) -> str | None:
    for code, words in INDICATOR_KEYWORDS:
        if any(word in lowered for word in words):
            return code
    return None


def _concept_answer(lowered: str) -> ChatAnswer | None:
    if not any(word in lowered for word in CONCEPT_WORDS):
        return None
    if any(word in lowered for word in DATA_WORDS):
        return None
    for slug, words in CONCEPT_TOPICS.items():
        if any(word in lowered for word in words):
            topic = next(t for t in TOPICS if t.slug == slug)
            text = f"{topic.summary} {topic.intro}"
            return ChatAnswer(
                kind="concept",
                text=text,
                sources=(Source("OpenDOSM documentation", "https://developer.data.gov.my/static-api/opendosm"),),
                links=((f"Read the full explanation: {topic.title}", f"/learn/{topic.slug}"),),
            )
    return None


def _latest_answer(code: str) -> ChatAnswer:
    spec = INDICATORS[code]
    snapshot = get_snapshot(code)
    if snapshot.latest_value is None:
        return ChatAnswer(
            kind="unavailable",
            text=f"I don't have stored data for {spec.name} yet. {snapshot.status_message}",
            links=(("Data status", "/data-status"),),
        )

    period = format_period(snapshot.latest_period, spec.frequency)
    if spec.value_kind == "rate":
        value_text = f"{snapshot.latest_value:.1f}%"
        if "labour force" in spec.unit:
            value_text += " of the labour force"
    else:
        value_text = f"{snapshot.latest_value:,.1f} ({spec.unit})"
    text = f"The latest {spec.name} is {value_text} for {period}. {snapshot.status_message}"
    return ChatAnswer(
        kind="data",
        text=text,
        sources=(Source(f"{spec.provider}: {spec.name}", spec.source_url),),
        links=((f"See the dashboard for {spec.name}", f"/dashboard?indicator={spec.code}"),),
    )


def _change_answer(code: str) -> ChatAnswer:
    spec = INDICATORS[code]
    points = load_points(spec)
    summary = summarise(points, spec)
    if summary.latest_period is None:
        return _latest_answer(code)
    period = format_period(summary.latest_period, spec.frequency)
    if summary.yoy_change_pct is None:
        return ChatAnswer(
            kind="unavailable",
            text=(
                f"I can't calculate the 12-month change for {spec.name} to {period}, "
                f"because the value for {format_period(summary.yoy_period, spec.frequency)} is not stored."
            ),
            sources=(Source(f"{spec.provider}: {spec.name}", spec.source_url),),
        )
    change: Decimal = summary.yoy_change_pct
    text = (
        f"The 12-month change in {spec.name} to {period} is {change:+.1f}%, compared with "
        f"{format_period(summary.yoy_period, spec.frequency)}. This is calculated from stored values. "
        f"{get_snapshot(code).status_message}"
    )
    return ChatAnswer(
        kind="change",
        text=text,
        sources=(Source(f"{spec.provider}: {spec.name}", spec.source_url),),
        links=(("How the 12-month change is calculated", "/learn/inflation"),),
    )


def _scope_answer() -> ChatAnswer:
    topics = ", ".join(
        [
            "inflation or CPI",
            "unemployment",
            "GDP growth or GDP level",
            "purchasing power",
        ]
    )
    return ChatAnswer(
        kind="scope",
        text=(
            "I can answer questions about Malaysian economic statistics on this site: "
            f"{topics}. Try asking, for example, \"What is the latest inflation rate?\" or "
            "\"What is unemployment?\""
        ),
        links=(("Explore the indicators", "/explore"),),
    )

