# NYC Events Radar

Aggregates NYC events from multiple sources into a searchable, filterable table.

## Structure

```
scrapers/   Python package — event scrapers (httpx, BeautifulSoup, Pydantic, Typer)
api/        FastAPI backend (aiosqlite, uvicorn)
web/        Vite + React + TypeScript frontend (TanStack Table, Tailwind CSS)
```

## Quick Start

### API

```bash
cd api
pip install -e .
uvicorn api.main:app --reload
```

### Scrapers

```bash
cd scrapers
pip install -e .
scrape <source>
```

### Web

```bash
cd web
npm install
npm run dev
```

## Shared Schema

The canonical event model lives in `scrapers/models.py` and is shared across all components.

## Configuration

Copy `.env.example` to `.env` and fill in values:

```bash
cp .env.example .env
```
