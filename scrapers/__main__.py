"""CLI entry-point: python -m scrapers [run|list]."""

from __future__ import annotations

import asyncio

import typer

from scrapers.base import get_scrapers, run_all

app = typer.Typer(help="NYC Events Radar – scraper CLI")


@app.command()
def run(
    source: list[str] | None = typer.Option(
        None, "--source", "-s", help="Scraper name(s) to run. Omit for all."
    ),
) -> None:
    """Run scrapers and write JSON output."""
    registry = get_scrapers()
    if not registry:
        typer.echo("No scrapers registered. Add source scrapers to scrapers/.")
        raise typer.Exit(1)

    sources = source or None
    events = asyncio.run(run_all(sources))
    typer.echo(f"Scraped {len(events)} event(s).")


@app.command(name="list")
def list_scrapers() -> None:
    """List registered scrapers."""
    registry = get_scrapers()
    if not registry:
        typer.echo("No scrapers registered.")
        raise typer.Exit()
    for name in sorted(registry):
        typer.echo(f"  {name}")


if __name__ == "__main__":
    app()
