import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import alerts, events, health, incidents, ml, risk, statistics
from app.config import get_settings
from app.database.session import init_db
from app.websocket import websocket_router, ws_manager


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    try:
        ws_manager.set_event_loop(asyncio.get_running_loop())
    except RuntimeError:
        pass
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="LogShield AI Engine",
        description=(
            "Laptop 2 prototype: log ingestion, hybrid detection (rule engine + Isolation Forest ML), "
            "correlation, explainable risk, incident analyst triage, and real-time WebSocket telemetry fan-out."
        ),
        version="0.13.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router)
    application.include_router(events.router)
    application.include_router(incidents.router)
    application.include_router(alerts.router)
    application.include_router(statistics.router)
    application.include_router(ml.router)
    application.include_router(risk.router)
    application.include_router(websocket_router)

    @application.get("/")
    def root() -> dict[str, str | int]:
        current = get_settings()
        return {
            "service": "logshield-engine",
            "docs": "/docs",
            "health": "/api/health",
            "phase": current.implementation_phase,
        }

    return application


app = create_app()
