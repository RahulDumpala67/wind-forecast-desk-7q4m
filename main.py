from pathlib import Path

from fastapi.staticfiles import StaticFiles

from backend.main import app

web_build = Path(__file__).parent / "frontend" / "dist"
if web_build.is_dir():
    app.mount("/", StaticFiles(directory=str(web_build), html=True), name="web")

