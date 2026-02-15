"""CLI entrypoint for event scrapers."""

import typer

app = typer.Typer(help="NYC Events Radar scrapers")


@app.command()
def run(source: str = typer.Argument(help="Scraper source to run")):
    """Run a specific event scraper."""
    typer.echo(f"Running scraper: {source}")


if __name__ == "__main__":
    app()
