"""Command-line tools for maintainers.

Usage:
    flask --app run refresh-data              # refresh every registered indicator
    flask --app run refresh-data cpi_headline # refresh one indicator
"""

import click
from flask import Flask
from flask.cli import with_appcontext

from .services.data_service import refresh_indicator
from .services.dataset_registry import INDICATORS
from .services.opendosm_client import client_from_config


def register_commands(app: Flask) -> None:
    app.cli.add_command(refresh_data_command)
    app.cli.add_command(evaluate_alerts_command)


@click.command("refresh-data")
@click.argument("codes", nargs=-1)
@with_appcontext
def refresh_data_command(codes: tuple[str, ...]) -> None:
    """Fetch OpenDOSM data for the given indicators (default: all)."""
    from flask import current_app

    selected = list(codes) or list(INDICATORS)
    unknown = [code for code in selected if code not in INDICATORS]
    if unknown:
        raise click.BadParameter(f"Unknown indicator(s): {', '.join(unknown)}")

    client = client_from_config(current_app.config)
    fetch_cache: dict = {}  # indicators from the same dataset share one request
    failures = 0
    for code in selected:
        outcome = refresh_indicator(code, client, fetch_cache=fetch_cache)
        status = "OK" if outcome.ok else "FAILED"
        click.echo(f"{status:7} {code}: {outcome.message} (observations processed: {outcome.observations})")
        if not outcome.ok:
            failures += 1

    if failures:
        raise SystemExit(1)


@click.command("evaluate-alerts")
@with_appcontext
def evaluate_alerts_command() -> None:
    """Create due inflation alerts from the stored data. Safe to run repeatedly.

    Schedule this after `refresh-data` (for example with Windows Task Scheduler
    or cron). Running it twice never creates duplicate notifications.
    """
    from .services.alert_service import evaluate_all

    report = evaluate_all()
    click.echo(f"Created {report.created} notification(s).")
    for line in report.skipped:
        click.echo(f"Skipped: {line}")
    if report.skipped:
        raise SystemExit(1)
