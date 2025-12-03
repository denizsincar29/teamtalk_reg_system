"""TeamTalk Registration System - FastAPI Web Application.

This application provides a web interface for registering users on a TeamTalk server.
It runs the pytalk-ex library in a separate process to avoid blocking the main thread.
"""

import multiprocessing
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import APP_HOST, APP_PORT
from app.manager import tt_manager
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events."""
    # Startup
    await tt_manager.start()
    yield
    # Shutdown
    tt_manager.stop()


app = FastAPI(title="TeamTalk Registration System", lifespan=lifespan)

# Mount static files
static_dir = Path(__file__).parent / "app" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routes
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    multiprocessing.set_start_method("spawn", force=True)
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)


