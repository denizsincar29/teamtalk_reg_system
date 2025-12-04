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

from app.config import APP_HOST, APP_PORT, FORWARDED_ALLOW_IPS, PROXY_HEADERS, ROOT_PATH
from app.logging_config import get_logger
from app.manager import tt_manager
from app.routes import router
from app.admin_routes import router as admin_router
from app.scheduler import task_scheduler

# Set up logging
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events."""
    # Startup
    logger.info("Starting TeamTalk Registration System...")
    await tt_manager.start()
    logger.info("TeamTalk manager started")
    
    # Initialize scheduler with manager and start it
    task_scheduler.set_manager(tt_manager)
    await task_scheduler.start()
    logger.info("Task scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down TeamTalk Registration System...")
    await task_scheduler.stop()
    tt_manager.stop()
    logger.info("Shutdown complete")


app = FastAPI(title="TeamTalk Registration System", lifespan=lifespan, root_path=ROOT_PATH)

# Mount static files
static_dir = Path(__file__).parent / "app" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routes
app.include_router(router)
app.include_router(admin_router)


if __name__ == "__main__":
    import uvicorn
    multiprocessing.set_start_method("spawn", force=True)
    uvicorn.run(
        app,
        host=APP_HOST,
        port=APP_PORT,
        proxy_headers=PROXY_HEADERS,
        forwarded_allow_ips=FORWARDED_ALLOW_IPS,
        root_path=ROOT_PATH
    )