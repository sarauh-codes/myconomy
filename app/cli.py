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
    failures = 0
    for code in selected:
        outcome = refresh_indicator(code, client)
        status = "OK" if outcome.ok else "FAILED"
        click.echo(f"{status:7} {code}: {outcome.message} (observations processed: {outcome.observations})")
        if not outcome.ok:
            failures += 1

    if failures:
        raise SystemExit(1)
