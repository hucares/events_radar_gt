# NYC Events Radar

Aggregates NYC event listings into a single searchable interface.

## Structure

```
scrapers/   Python package – pulls events from various sources
api/        FastAPI backend – serves event data via REST
web/        Vite + React + TypeScript frontend
```

## Quick Start

### API

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn api.main:app --reload
```

### Web

```bash
cd web
npm install
npm run dev
```

### Scrapers

```bash
cd scrapers
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and fill in values.
