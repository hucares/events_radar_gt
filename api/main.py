"""NYC Events Radar API."""

from fastapi import FastAPI

app = FastAPI(title="NYC Events Radar", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}
