from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.competitors import router as competitors_router
from app.api.findings import router as findings_router
from app.api.health import router as health_router
from app.api.snapshots import router as snapshots_router
from app.api.sources import router as sources_router
from app.api.workspaces import router as workspaces_router
from app.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(workspaces_router, prefix="/api")
app.include_router(competitors_router, prefix="/api")
app.include_router(sources_router, prefix="/api")
app.include_router(findings_router, prefix="/api")
app.include_router(snapshots_router, prefix="/api")
