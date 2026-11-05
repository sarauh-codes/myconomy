"""Plain-language explanations for the Learn & understand section.

Each topic separates three kinds of content, which the page labels differently:
- Explanation: general text about what the measure means.
- Illustrative example: invented numbers, labelled as such. Never official.
- Official example: computed at request time from stored OpenDOSM data.

The formula is imported from the calculator, so the explanation and the
calculation cannot drift apart (requirement FR-08 and test LEARN-03).
Review this content whenever calculation logic or source definitions change.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..services.calculator_service import FORMULA_TEXT
from ..services.dataset_registry import DATASET_DOC_URL


@dataclass(frozen=True)
class Section:
    heading: str
    paragraphs: tuple[str, ...]


@dataclass(frozen=True)
class Topic:
    slug: str
    title: str
    summary: str
    intro: str
    sections: tuple[Section, ...]
    illustrative_title: str
    illustrative_text: str
    official_example_key: str  # which live example to show, see routes/learn.py
    formula: str | None = None
    sources: tuple[tuple[str, str], ...] = field(
        default_factory=lambda: (("OpenDOSM documentation", DATASET_DOC_URL),)
    )


TOPICS: tuple[Topic, ...] = (
    Topic(
        slug="cpi",
        title="What the Consumer Price Index measures",
        summary="The CPI tracks how the average price of a typical basket of goods and services changes over time.",
        intro=(
            "The Consumer Price Index (CPI) is one of the most widely used measures of prices. "
            "Statisticians choose a basket of goods and services that households commonly buy, "
            "record its prices each month, and express the total as an index number."
        ),
        sections=(
            Section(
                "Reading an index number",
                (
                    "A CPI value such as 137.6 is not a price in ringgit. It is a number on a scale "
                    "that is set relative to a base period.",
                    "What matters is the change between two months. If the index goes from 100 to 110, "
                    "average prices in the basket rose by 10 per cent.",
                ),
            ),
            Section(
                "Comparing months",
                (
                    "Compare two index values from the same series to see how prices changed. "
                    "Do not read a single index value as a price.",
                    "The headline CPI covers all items in the basket. Division-level series "
                    "cover groups such as food or housing.",
                ),
            ),
            Section(
                "What CPI does not measure",
                (
                    "CPI describes an average basket. It does not show what any one person pays, "
                    "because spending patterns differ between households and regions.",
                    "CPI also says nothing about incomes, savings, or taxes. Pair it with those figures when you study living costs.",
                ),
            ),
        ),
        illustrative_title="Illustrative example: an index going from 100 to 110",
        illustrative_text=(
            "The numbers here are invented for explanation. An index moves from 100 to 110. "
            "Average prices in the basket have risen by 10 per cent."
        ),
        official_example_key="cpi_latest",
    ),
    Topic(
        slug="inflation",
        title="Inflation: how fast prices are rising",
        summary="Inflation is the rate at which prices rise. It is measured as a change in the CPI over time.",
        intro=(
            "Inflation is about change, not level. The CPI tells you how expensive the basket is "
            "compared with an earlier month. Inflation tells you how quickly that gap is growing."
        ),
        sections=(
            Section(
                "Calculating 12-month inflation",
                (
                    "This site shows 12-month inflation as the change in CPI over the past year. "
                    "It is calculated as (latest CPI − CPI 12 months earlier) ÷ CPI 12 months earlier × 100.",
                    "The dashboard uses the same calculation, and it only shows a result when both months are stored.",
                ),
            ),
            Section(
                "Rising prices and slower inflation",
                (
                    "Inflation can slow down while prices are still higher than before. "
                    "If prices rise 2 per cent this year after rising 5 per cent last year, "
                    "the price level is still higher, but the rate of increase has fallen.",
                    "Prices falling is called deflation. It is a different situation from prices rising more slowly.",
                ),
            ),
            Section(
                "Why it matters",
                (
                    "Inflation affects what your money can buy, and it affects how wages, "
                    "savings, and loans change over time.",
                ),
            ),
        ),
        illustrative_title="Illustrative example: a 12-month increase of 3 per cent",
        illustrative_text=(
            "The numbers here are invented for explanation. A basket costs RM 100 a year ago and RM 103 now. "
            "(RM 103 − RM 100) ÷ RM 100 × 100 = 3 per cent."
        ),
        official_example_key="inflation_latest",
        formula="12-month inflation = (CPI now − CPI 12 months earlier) ÷ CPI 12 months earlier × 100",
    ),
    Topic(
        slug="purchasing-power",
        title="Purchasing power: what money can buy",
        summary="Purchasing power is how much goods and services a sum of money can buy. Rising prices reduce it.",
        intro=(
            "If prices rise, the same amount of money buys less. Purchasing power compares an amount "
            "from one month with the amount that would buy the same basket in another month."
        ),
        sections=(
            Section(
                "The formula",
                (
                    "The purchasing power calculator uses the CPI ratio between two months. "
                    f"The formula is: {FORMULA_TEXT}.",
                    "A larger target CPI than the starting CPI gives a larger equivalent amount. "
                    "A smaller target CPI gives a smaller one.",
                ),
            ),
            Section(
                "What the result means",
                (
                    "The result is an estimate based on the average basket. It shows what the same "
                    "purchasing power would cost in the other month, using national prices.",
                    "It is not a measure of your personal costs, and it is not financial advice.",
                ),
            ),
        ),
        illustrative_title="Illustrative example: RM 100 and a 10 per cent rise",
        illustrative_text=(
            "The numbers here are invented for explanation. RM 100 buys a basket in January. "
            "If the same basket costs 10 per cent more by December, RM 110 is needed to buy it."
        ),
        official_example_key="purchasing_power_example",
        formula=FORMULA_TEXT,
    ),
)

TOPICS_BY_SLUG: dict[str, Topic] = {topic.slug: topic for topic in TOPICS}
