import logging
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from .config import settings
from .database import init_db
from .api.v1 import auth, users, clothing, materials, brands, swaps, impact, stats

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    init_db()
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API for tracking environmental impact of clothing swaps and sustainable fashion choices",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(clothing.router, prefix="/api/v1/clothing", tags=["clothing"])
app.include_router(materials.router, prefix="/api/v1/materials", tags=["materials"])
app.include_router(brands.router, prefix="/api/v1/brands", tags=["brands"])
app.include_router(swaps.router, prefix="/api/v1/swaps", tags=["swaps"])
app.include_router(impact.router, prefix="/api/v1/impact", tags=["impact"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["stats"])


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )