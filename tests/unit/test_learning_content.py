"""Content checks for the Learn & understand topics."""

from app.services.calculator_service import FORMULA_TEXT
from app.services.learning_content import TOPICS, TOPICS_BY_SLUG


def test_topic_slugs_are_unique_and_url_safe():
    slugs = [topic.slug for topic in TOPICS]
    assert len(slugs) == len(set(slugs))
    for slug in slugs:
        assert slug == slug.lower()
        assert " " not in slug


def test_every_topic_has_explanation_and_illustrative_example():
    for topic in TOPICS:
        assert topic.title and topic.summary and topic.intro
        assert topic.sections
        assert all(section.paragraphs for section in topic.sections)
        assert "invented" in topic.illustrative_text.lower(), topic.slug


def test_every_topic_links_to_an_https_source():
    for topic in TOPICS:
        assert topic.sources
        for label, url in topic.sources:
            assert label
            assert url.startswith("https://"), topic.slug


def test_purchasing_power_formula_is_the_calculator_constant():
    assert TOPICS_BY_SLUG["purchasing-power"].formula == FORMULA_TEXT


def test_inflation_formula_matches_the_dashboard_definition():
    formula = TOPICS_BY_SLUG["inflation"].formula
    assert "CPI 12 months earlier" in formula
    assert "× 100" in formula
