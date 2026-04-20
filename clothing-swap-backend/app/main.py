import logging
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.routes.auth import router

from .config import settings
from .database import init_db
from .api.v1 import auth, users, clothing, materials, brands, swaps, impact, stats, payment, shipping, sales, checkout, orders, reviews, cart, stripe_connect
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.database import get_db
from .models.material import MaterialReference
from datetime import datetime

load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    init_db()
    db: Session = next(get_db())
    db.query(MaterialReference).delete()
    db.commit()
    cotton = MaterialReference(
        material_name="cotton",
        co2_per_kg=35,
        water_liters_per_kg=13500,
        energy_mj_per_kg=25,
        last_updated=datetime.utcnow()
    )
    polyester = MaterialReference(
        material_name="polyester",
        co2_per_kg=40,
        water_liters_per_kg=600,
        energy_mj_per_kg=35,
        last_updated=datetime.utcnow()
    )
    nylon = MaterialReference(
        material_name="nylon",
        co2_per_kg=11,
        water_liters_per_kg=150,
        energy_mj_per_kg=16,
        last_updated=datetime.utcnow()
    )
    linen = MaterialReference(
        material_name="linen",
        co2_per_kg=5,
        water_liters_per_kg=2000,
        energy_mj_per_kg=10,
        last_updated=datetime.utcnow()
    )
    wool = MaterialReference(
        material_name="wool",
        co2_per_kg=15,
        water_liters_per_kg=10000,
        energy_mj_per_kg=25,
        last_updated=datetime.utcnow()
    )
    silk = MaterialReference(
        material_name="silk",
        co2_per_kg=15,
        water_liters_per_kg=1000,
        energy_mj_per_kg=25,
        last_updated=datetime.utcnow()
    )
    denim = MaterialReference(
        material_name="denim",
        co2_per_kg=12,
        water_liters_per_kg=1000,
        energy_mj_per_kg=17,
        last_updated=datetime.utcnow()
    )
    rayon = MaterialReference(
        material_name="rayon",
        co2_per_kg=7,
        water_liters_per_kg=250,
        energy_mj_per_kg=25,
        last_updated=datetime.utcnow()
    )
    spandex = MaterialReference(
        material_name="spandex",
        co2_per_kg=15,
        water_liters_per_kg=150,
        energy_mj_per_kg=17,
        last_updated=datetime.utcnow()
    )
    acrylic = MaterialReference(
        material_name="acrylic",
        co2_per_kg=12,
        water_liters_per_kg=210,
        energy_mj_per_kg=20,
        last_updated=datetime.utcnow()
    )
    viscose = MaterialReference(
        material_name="viscose",
        co2_per_kg=12,
        water_liters_per_kg=1500,
        energy_mj_per_kg=17,
        last_updated=datetime.utcnow()
    )
    modal = MaterialReference(
        material_name="modal",
        co2_per_kg=10,
        water_liters_per_kg=5000,
        energy_mj_per_kg=15,
        last_updated=datetime.utcnow()
    )
    organic_cotton = MaterialReference(
        material_name="organic_cotton",
        co2_per_kg=7,
        water_liters_per_kg=2500,
        energy_mj_per_kg=10,
        last_updated=datetime.utcnow()
    )
    recycled_polyester = MaterialReference(
        material_name="recycled_polyester",
        co2_per_kg=4,
        water_liters_per_kg=50,
        energy_mj_per_kg=14,
        last_updated=datetime.utcnow()
    )
    db.add(cotton)
    db.add(polyester)
    db.add(nylon)
    db.add(linen)
    db.add(wool)
    db.add(silk)
    db.add(denim)
    db.add(rayon)
    db.add(spandex)
    db.add(acrylic)
    db.add(viscose)
    db.add(modal)
    db.add(organic_cotton)
    db.add(recycled_polyester)



    db.commit()
    db.close()

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
    allow_origins=settings.ALLOWED_ORIGINS,
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


app.include_router(router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(clothing.router, prefix="/api/v1/clothing", tags=["clothing"])
app.include_router(materials.router, prefix="/api/v1/materials", tags=["materials"])
app.include_router(brands.router, prefix="/api/v1/brands", tags=["brands"])
app.include_router(swaps.router, prefix="/api/v1/swaps", tags=["swaps"])
app.include_router(impact.router, prefix="/api/v1/impact", tags=["impact"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["stats"])
app.include_router(sales.router, prefix="/api/v1/sales", tags=["sales"])
app.include_router(payment.router, prefix="/api/v1/payment", tags=["payment"])
app.include_router(shipping.router, prefix="/api/v1/shipping", tags=["shipping"])
app.include_router(checkout.router, prefix="/api/v1", tags=["checkout"])
app.include_router(orders.router, prefix="/api/v1", tags=["orders"])
app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["reviews"])
app.include_router(cart.router, prefix="/api/v1/cart", tags=["cart"])
app.include_router(stripe_connect.router, prefix="/api/v1", tags=["stripe-connect"])



if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )