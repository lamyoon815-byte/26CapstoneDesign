from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title="PERSONGAL API")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def home():
    return RedirectResponse("/site/persongal_home.html")


app.mount(
    "/site",
    StaticFiles(directory=str(ROOT / "site")),
    name="site",
)