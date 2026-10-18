"""Local FastAPI entry point for LEGO AI Agent."""

from fastapi import FastAPI

from lego import APP_NAME, __version__

app = FastAPI(title=APP_NAME, version=__version__)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Report that the local backend process is responding."""
    return {"status": "ok", "app": APP_NAME, "version": __version__}
