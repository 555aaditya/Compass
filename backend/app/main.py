import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import REPO_ROOT, get_settings
from app.core.logging import setup_logging
from app.workers.pipeline import recover_interrupted
from app.workers.scheduler import build_scheduler

log = logging.getLogger(__name__)


def migrate() -> None:
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "migrations"))
    Path(REPO_ROOT / "data").mkdir(exist_ok=True)
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    s = get_settings()
    migrate()
    log.info("recovered %s interrupted runs", recover_interrupted())
    sch = build_scheduler(s) if s.scheduler_enabled else None
    if sch:
        sch.start()
    yield
    if sch:
        sch.shutdown(wait=False)  # graceful: let in-flight runs finish their transaction


def create_app() -> FastAPI:
    app = FastAPI(title="Compass", version="1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                       allow_methods=["*"], allow_headers=["*"])
    app.include_router(router)
    dist = REPO_ROOT / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="ui")
    return app


app = create_app()
