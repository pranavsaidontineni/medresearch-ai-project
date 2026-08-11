from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import get_settings
from app.core.rate_limit import rate_limit_middleware
from app.core.security_headers import security_headers_middleware
from app.api.routes import auth, papers, library, workspaces
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["GET", "POST", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])
app.middleware("http")(security_headers_middleware)
app.middleware("http")(rate_limit_middleware)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(papers.router, prefix="/api/v1")
app.include_router(library.router, prefix="/api/v1")
app.include_router(workspaces.router, prefix="/api/v1")


@app.get("/health")
async def health():
    db_status = "ok"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "unavailable"
    return {"status": "ok" if db_status == "ok" else "degraded", "service": settings.app_name, "database": db_status}
