"""API privada de indicadores; el consumidor comparte origen y autorización Cloud Run."""
import datetime as dt
import os
from pathlib import Path as FilePath
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import AwareDatetime

from .repository import BigQueryRepository, DataUnavailable
from .settings import Settings
from .monitoring import MonitoringRepository

START = dt.datetime(2024, 1, 1, 5, tzinfo=dt.timezone.utc)
END = START + dt.timedelta(days=1)


def create_app(repository=None, settings=None, static_dir=None):
    config = settings or Settings.from_env()
    app = FastAPI(title="Lumina · Indicadores de movilidad", version="0.1.0")
    repo = repository or MonitoringRepository(config)

    @app.exception_handler(DataUnavailable)
    async def unavailable(request, error):
        return JSONResponse(status_code=503, content={"detail": str(error)})

    @app.get("/health")
    def health():
        return {"status": "ok", "project": config.project, "proyecto": config.project,
                "dataset": config.dataset, "ultima_ingesta": None, "simulation": True}

    @app.get("/kpis")
    def dashboard_kpis():
        return repo.dashboard_kpis()

    @app.get("/batch/ultimo")
    def dashboard_batch():
        return repo.dashboard_batch()

    @app.get("/latencia")
    def dashboard_latency():
        return repo.dashboard_latency()

    @app.get("/zonas")
    def dashboard_zones():
        return repo.dashboard_zones()

    @app.get("/eventos/por-minuto")
    def dashboard_minutes(min: Annotated[int, Query(ge=1, le=60)] = 15):
        return repo.dashboard_minutes(min)

    @app.get("/eventos/ultimo")
    def dashboard_latest():
        return repo.dashboard_latest()

    @app.get("/rechazos")
    def dashboard_rejections(limit: Annotated[int, Query(ge=1, le=50)] = 5):
        return repo.dashboard_rejections(limit)

    @app.get("/api/zones")
    def zones():
        return {"zones": repo.zones()}

    @app.get("/api/metrics")
    def metrics(
        zone: Annotated[str, Query(pattern=r"^DL-\d{3}$")] = "DL-132",
        start: AwareDatetime = START,
        end: AwareDatetime = END,
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ):
        if not 1 <= int(zone[3:]) <= 263:
            raise HTTPException(422, "Zona fuera del catálogo")
        if start >= end or end - start > dt.timedelta(days=31):
            raise HTTPException(422, "El periodo debe ser positivo y no superar 31 días")
        return repo.metrics(zone, start.astimezone(dt.timezone.utc), end.astimezone(dt.timezone.utc), limit)

    @app.get("/api/quality")
    def quality():
        return repo.quality()

    @app.get("/api/events/{event_id}")
    def event(event_id: Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,128}$")]):
        result = repo.event(event_id)
        if result["variants"] > 1:
            raise HTTPException(409, "El identificador tiene contenidos conflictivos y se excluye de Gold")
        if result["event"] is None:
            raise HTTPException(404, "Evento todavía no disponible")
        return {**result, "observed_at": dt.datetime.now(dt.timezone.utc)}

    configured_static = static_dir or os.getenv("LUMINA_STATIC_DIR")
    location = FilePath(configured_static) if configured_static else FilePath(__file__).resolve().parents[1] / "static"
    if location.is_dir():
        app.mount("/", StaticFiles(directory=location, html=True), name="consumer")
    return app


app = create_app()
