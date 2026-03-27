from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from decimal import Decimal
import math

from ...database import get_db
from ...models.clothing import ClothingItem
from ...models.user import User
from ...models.brand import BrandSustainability
from ...models.impact import ClothingEnvironmentalImpact
from ...models.material import MaterialReference
from ...schemas.clothing import (
    ClothingItemCreate,
    ClothingItemUpdate,
    ClothingItemResponse,
    ClothingItemList,
    ClothingItemAvailabilityResponse,
    AvailabilityItemResponse,
    BatchAvailabilityRequest,
)
from ...services.payment import create_payment
from ...schemas.sustainability import SustainabilityMetricsResponse, SwapImpactResponse
from .users import get_current_user

router = APIRouter()

# Optional auth — returns user_id or None (for endpoints that behave differently when logged in)
security = HTTPBearer(auto_error=False)

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Return user_id if a valid token is present, otherwise None."""
    if not credentials:
        return None
    from jose import jwt, JWTError
    try:
        payload = jwt.decode(credentials.credentials, "secret", algorithms=["HS256"])
        return payload.get("user_id")
    except (JWTError, Exception):
        return None


# ── GET /clothing/ ──────────────────────────────────────────────────────

def _get_unavailable_reason(status: Optional[str]) -> Optional[str]:
    """Map backend status values to user-safe cart validation reasons."""
    if status == "available":
        return None

    reason_by_status = {
        "reserved": "This item is currently reserved.",
        "pending_sale": "This item is currently reserved.",
        "sold": "This item has been sold.",
        "swapped": "This item has already been swapped.",
        "deleted": "This item is no longer available.",
    }

    return reason_by_status.get(status, "This item is currently unavailable.")


@router.get("/", response_model=ClothingItemList)
async def get_clothing_items(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    clothing_type: Optional[str] = Query(None, description="Filter by clothing type"),
    brand: Optional[str] = Query(None, description="Filter by brand name"),
    size: Optional[str] = Query(None, description="Filter by size"),
    condition: Optional[str] = Query(None, description="Filter by condition"),
    status: Optional[str] = Query("available", description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in description and brand"),
    category: Optional[str] = Query(None, description="Filter by category (Men, Women, etc.)"),
):
    """Get all clothing items with pagination and filtering."""

    query = db.query(ClothingItem)

    if status:
        query = query.filter(ClothingItem.status == status)
    if clothing_type:
        query = query.filter(ClothingItem.clothing_type == clothing_type)
    if brand:
        query = query.filter(ClothingItem.brand.ilike(f"%{brand}%"))
    if size:
        query = query.filter(ClothingItem.size == size)
    if condition:
        query = query.filter(ClothingItem.condition == condition)
    if search:
        search_filter = or_(
            ClothingItem.description.ilike(f"%{search}%"),
            ClothingItem.brand.ilike(f"%{search}%"),
            ClothingItem.clothing_type.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)

    total = query.count()
    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page).all()
    total_pages = math.ceil(total / per_page)

    return ClothingItemList(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.post("/availability", response_model=List[AvailabilityItemResponse])
async def get_batch_availability(
    request: BatchAvailabilityRequest,
    db: Session = Depends(get_db),
):
    """Validate availability for multiple clothing items in one request."""

    requested_ids = request.clothing_ids
    items = db.query(ClothingItem).filter(ClothingItem.clothing_id.in_(requested_ids)).all()
    item_by_id = {item.clothing_id: item for item in items}

    response_items: List[AvailabilityItemResponse] = []

    for clothing_id in requested_ids:
        item = item_by_id.get(clothing_id)

        if not item:
            response_items.append(
                AvailabilityItemResponse(
                    clothing_id=clothing_id,
                    status="not_found",
                    updated_at=None,
                    available=False,
                    unavailable_reason="This item no longer exists.",
                )
            )
            continue

        status = item.status
        response_items.append(
            AvailabilityItemResponse(
                clothing_id=item.clothing_id,
                available=bool(item.available),
                status=status,
                unavailable_reason=item.unavailable_reason or _get_unavailable_reason(status),
                updated_at=item.updated_at,
            )
        )

    return response_items


# @router.get("/{clothing_id}", response_model=ClothingItemAvailabilityResponse)
# ── GET /clothing/my-items ──────────────────────────────────────────────

@router.get("/my-items")
async def get_my_items(
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """
    Get all clothing items owned by the current authenticated user.
    Used by SwapModal to show only items the user can offer.
    """
    query = db.query(ClothingItem).filter(ClothingItem.owner_user_id == user_id)

    if status:
        query = query.filter(ClothingItem.status == status)

    items = query.order_by(ClothingItem.created_at.desc()).all()

    return {
        "items": [
            {
                "clothing_id": item.clothing_id,
                "description": item.description,
                "clothing_type": item.clothing_type,
                "brand": item.brand,
                "size": item.size,
                "condition": item.condition,
                "status": item.status,
                "sell_price": float(item.sell_price) if item.sell_price else None,
                "primary_image_url": item.primary_image_url,
                "material_composition": item.material_composition,
                "owner_user_id": item.owner_user_id,
            }
            for item in items
        ],
        "count": len(items),
    }


# ── GET /clothing/owner-info/{clothing_id} ──────────────────────────────

@router.get("/owner-info/{clothing_id}")
async def get_item_owner_info(clothing_id: int, db: Session = Depends(get_db)):
    """
    Get the owner's public info for a clothing item.
    Returns owner name, swap count, and user_id.
    """
    clothing = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()
    if not clothing:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    owner = db.query(User).filter(User.user_id == clothing.owner_user_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    return {
        "owner_user_id": owner.user_id,
        "display_name": owner.display_name or owner.username,
        "total_swaps": owner.total_swaps or 0,
        "total_sales": owner.total_sales or 0,
        "joined_date": owner.joined_date.isoformat() if owner.joined_date else None,
    }


# ── GET /clothing/{clothing_id} ─────────────────────────────────────────

@router.get("/{clothing_id}", response_model=ClothingItemResponse)
async def get_clothing_item(clothing_id: int, db: Session = Depends(get_db)):
    """Get a specific clothing item by ID."""

    clothing_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()

    if not clothing_item:
        raise HTTPException(status_code=404, detail="Clothing item not found")
    
    return ClothingItemResponse.from_orm(clothing_item)


# ── POST /clothing/ ──────────────────────────────────────────────────────

@router.post("/", response_model=ClothingItemResponse)
async def create_clothing_item(
    clothing_data: ClothingItemCreate,
    db: Session = Depends(get_db),
    user_id = Depends(get_current_user)
):
    # Look up brand_id if brand is provided
    brand_id = None
    if clothing_data.brand:
        brand = db.query(BrandSustainability).filter(
            BrandSustainability.brand_name.ilike(clothing_data.brand)
        ).first()
        if brand:
            brand_id = brand.brand_id

    # Create the clothing item — owner is always the authenticated user
    db_clothing_item = ClothingItem(
        owner_user_id=user_id,
        clothing_type=clothing_data.clothing_type,
        brand=clothing_data.brand,
        brand_id=brand_id,
        description=clothing_data.description,
        size=clothing_data.size,
        color=clothing_data.color,
        condition=clothing_data.condition,
        material_composition=clothing_data.material_composition,
        weight_grams=clothing_data.weight_grams,
        primary_image_url=clothing_data.primary_image_url,
        additional_images=clothing_data.additional_images or [],
        sell_price=clothing_data.sell_price,
        status="available"
    )

    db.add(db_clothing_item)
    db.commit()
    db.refresh(db_clothing_item)

    return db_clothing_item


# ── PUT /clothing/{clothing_id} ──────────────────────────────────────────

@router.put("/{clothing_id}", response_model=ClothingItemResponse)
async def update_clothing_item(
    clothing_id: int,
    clothing_data: ClothingItemUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Update a clothing item. Only the owner can update their own items."""

    clothing_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()

    if not clothing_item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    # ── OWNERSHIP CHECK ──
    if clothing_item.owner_user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only edit items you own"
        )

    update_data = clothing_data.dict(exclude_unset=True)

    # Handle brand_id lookup if brand is updated
    if "brand" in update_data and update_data["brand"]:
        brand = db.query(BrandSustainability).filter(
            BrandSustainability.brand_name.ilike(update_data["brand"])
        ).first()
        if brand:
            update_data["brand_id"] = brand.brand_id

    for field, value in update_data.items():
        setattr(clothing_item, field, value)

    db.commit()
    db.refresh(clothing_item)

    return clothing_item


# ── DELETE /clothing/{clothing_id} ───────────────────────────────────────

@router.delete("/{clothing_id}")
async def delete_clothing_item(
    clothing_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Delete a clothing item. Only the owner can delete their own items."""

    clothing_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()

    if not clothing_item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    # ── OWNERSHIP CHECK ──
    if clothing_item.owner_user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete items you own"
        )

    # Don't allow deletion of items involved in pending swaps or sales
    if clothing_item.status in ("pending_sale", "pending_swap"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete item with status '{clothing_item.status}'. Cancel the pending transaction first."
        )

    db.delete(clothing_item)
    db.commit()

    return {"message": "Clothing item deleted successfully"}


# ── Utility endpoints (no auth required) ─────────────────────────────────

@router.get("/categories/", response_model=List[str])
async def get_clothing_types(db: Session = Depends(get_db)):
    """Get all unique clothing types available."""
    clothing_types = db.query(ClothingItem.clothing_type).distinct().all()
    return [item[0] for item in clothing_types if item[0]]


@router.get("/brands/", response_model=List[str])
async def get_clothing_brands(db: Session = Depends(get_db)):
    """Get all unique brands available."""
    brands = db.query(ClothingItem.brand).distinct().all()
    return [item[0] for item in brands if item[0]]


@router.get("/sizes/", response_model=List[str])
async def get_clothing_sizes(db: Session = Depends(get_db)):
    """Get all unique sizes available."""
    sizes = db.query(ClothingItem.size).distinct().all()
    return [item[0] for item in sizes if item[0]]


# ── Purchase endpoint ────────────────────────────────────────────────────

@router.post("/{clothing_id}/purchase")
async def purchase_clothing_item(
    clothing_id: int,
    buyer_user_id: int,
    amount: Decimal,
    db: Session = Depends(get_db)
):
    """Initiate a payment for purchasing a clothing item."""

    clothing_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()
    if not clothing_item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    if clothing_item.status != "available":
        raise HTTPException(status_code=400, detail=f"Item is not available (status: {clothing_item.status})")

    buyer = db.query(User).filter(User.user_id == buyer_user_id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer user not found")

    # ── OWNERSHIP CHECK ──
    if clothing_item.owner_user_id == buyer_user_id:
        raise HTTPException(status_code=400, detail="Cannot purchase your own items")

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")

    try:
        payment, client_secret = create_payment(
            db,
            transaction_id=clothing_id,
            amount=amount,
            currency="usd",
        )
    except HTTPException as e:
        raise e

    return {
        "clothing_id": clothing_id,
        "buyer_user_id": buyer_user_id,
        "payment_id": payment.id,
        "payment_status": payment.status,
        "client_secret": client_secret,
        "amount": str(amount),
        "currency": "usd"
    }


# ── Sustainability endpoint ──────────────────────────────────────────────

@router.get("/{clothing_id}/sustainability", response_model=SustainabilityMetricsResponse)
async def get_clothing_sustainability_metrics(clothing_id: int, db: Session = Depends(get_db)):
    """Get comprehensive sustainability metrics for a specific clothing item."""

    clothing_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()

    if not clothing_item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    impact_data = db.query(ClothingEnvironmentalImpact).filter(
        ClothingEnvironmentalImpact.clothing_id == clothing_id
    ).first()

    brand_data = None
    if clothing_item.brand_id:
        brand_data = db.query(BrandSustainability).filter(
            BrandSustainability.brand_id == clothing_item.brand_id
        ).first()

    if not impact_data:
        impact_data = calculate_impact_from_materials(clothing_item, db)

    item_summary = {
        "name": clothing_item.description or f"{clothing_item.clothing_type} by {clothing_item.brand or 'Unknown'}",
        "type": clothing_item.clothing_type,
        "brand": clothing_item.brand,
        "size": clothing_item.size,
        "condition": clothing_item.condition,
        "material_composition": clothing_item.material_composition
    }

    equivalents_data = {}
    if impact_data:
        equivalents_data = impact_data.get_equivalents() if hasattr(impact_data, 'get_equivalents') else calculate_equivalents(impact_data)

    new_garment = {
        "co2_kg": float(impact_data.new_total_co2) if impact_data and impact_data.new_total_co2 else 15.5,
        "water_liters": float(impact_data.new_total_water) if impact_data and impact_data.new_total_water else 2700.0,
        "energy_kwh": float(impact_data.new_total_energy_kwh) if impact_data and impact_data.new_total_energy_kwh else 42.3,
        "breakdown": {
            "material_production": float(impact_data.new_material_co2) if impact_data and impact_data.new_material_co2 else 8.5,
            "manufacturing": float(impact_data.new_manufacturing_co2) if impact_data and impact_data.new_manufacturing_co2 else 3.2,
            "dyeing": float(impact_data.new_dyeing_co2) if impact_data and impact_data.new_dyeing_co2 else 2.1,
            "transport": float(impact_data.new_transport_co2) if impact_data and impact_data.new_transport_co2 else 1.2,
            "packaging": float(impact_data.new_packaging_co2) if impact_data and impact_data.new_packaging_co2 else 0.5
        }
    }

    reuse_impact = {
        "co2_kg": float(impact_data.reuse_total_co2) if impact_data and impact_data.reuse_total_co2 else 0.08,
        "breakdown": {
            "collection": float(impact_data.reuse_collection_co2) if impact_data and impact_data.reuse_collection_co2 else 0.05,
            "sorting": float(impact_data.reuse_sorting_co2) if impact_data and impact_data.reuse_sorting_co2 else 0.02,
            "transport": float(impact_data.reuse_transport_co2) if impact_data and impact_data.reuse_transport_co2 else 0.01,
            "platform_overhead": float(impact_data.reuse_platform_co2) if impact_data and impact_data.reuse_platform_co2 else 0.01
        }
    }

    net_co2 = new_garment["co2_kg"] - reuse_impact["co2_kg"]
    net_water = new_garment["water_liters"]
    net_energy = new_garment["energy_kwh"]
    percentage_reduction = (net_co2 / new_garment["co2_kg"]) * 100 if new_garment["co2_kg"] > 0 else 0

    avoided_impact = {
        "co2_kg": net_co2,
        "water_liters": net_water,
        "energy_kwh": net_energy,
        "percentage_reduction": percentage_reduction
    }

    equivalents = {
        "km_not_driven": net_co2 * 5.26,
        "trees_planted": net_co2 / 21,
        "days_drinking_water": net_water / 2,
        "smartphone_charges": int(net_energy * 125)
    }

    brand_context = {
        "brand_name": clothing_item.brand,
        "transparency_score": brand_data.transparency_index_score if brand_data else None,
        "sustainability_rating": brand_data.overall_rating if brand_data else None,
        "certifications": [],
        "impact_commitments": {
            "publishes_supplier_list": brand_data.publishes_supplier_list if brand_data else None,
            "discloses_ghg_emissions": brand_data.discloses_ghg_emissions if brand_data else None,
            "discloses_water_usage": brand_data.discloses_water_usage if brand_data else None,
            "has_climate_targets": brand_data.has_climate_targets if brand_data else None
        } if brand_data else {}
    }

    calculation_metadata = {
        "version": impact_data.calculation_version if impact_data else "1.0",
        "calculation_date": impact_data.calculation_date.isoformat() if impact_data and impact_data.calculation_date else None,
        "data_quality": impact_data.data_quality_score if impact_data else "estimated",
        "assumptions": {
            "wears": impact_data.assumed_wears if impact_data else 50,
            "washes": impact_data.assumed_washes if impact_data else 25
        }
    }

    return SustainabilityMetricsResponse(
        clothing_id=clothing_id,
        item_summary=item_summary,
        new_garment=new_garment,
        reuse_impact=reuse_impact,
        avoided_impact=avoided_impact,
        equivalents=equivalents,
        brand_context=brand_context,
        calculation_metadata=calculation_metadata
    )


def calculate_impact_from_materials(clothing_item: ClothingItem, db: Session) -> ClothingEnvironmentalImpact:
    """Calculate environmental impact from material composition when no stored data exists."""
    total_co2 = 15.5
    total_water = 2700.0
    total_energy = 42.3

    if clothing_item.material_composition:
        weighted_co2 = 0
        weighted_water = 0
        weighted_energy = 0

        for material_name, percentage in clothing_item.material_composition.items():
            material = db.query(MaterialReference).filter(
                MaterialReference.material_name.ilike(f"%{material_name}%")
            ).first()

            if material and percentage > 0:
                weight_factor = percentage / 100
                weighted_co2 += float(material.co2_per_kg or 10) * weight_factor
                weighted_water += float(material.water_liters_per_kg or 2000) * weight_factor
                weighted_energy += float(material.energy_mj_per_kg or 50) * weight_factor

        if weighted_co2 > 0:
            garment_weight_kg = (clothing_item.weight_grams or 200) / 1000
            total_co2 = weighted_co2 * garment_weight_kg
            total_water = weighted_water * garment_weight_kg
            total_energy = (weighted_energy * garment_weight_kg) / 3.6

    impact = ClothingEnvironmentalImpact()
    impact.clothing_id = clothing_item.clothing_id
    impact.new_total_co2 = total_co2
    impact.new_total_water = total_water
    impact.new_total_energy_kwh = total_energy
    impact.new_material_co2 = total_co2 * 0.55
    impact.new_manufacturing_co2 = total_co2 * 0.20
    impact.new_dyeing_co2 = total_co2 * 0.14
    impact.new_transport_co2 = total_co2 * 0.08
    impact.new_packaging_co2 = total_co2 * 0.03
    impact.reuse_total_co2 = 0.08
    impact.reuse_collection_co2 = 0.05
    impact.reuse_sorting_co2 = 0.02
    impact.reuse_transport_co2 = 0.01
    impact.reuse_platform_co2 = 0.01
    impact.net_avoided_co2 = total_co2 - 0.08
    impact.net_avoided_water = total_water
    impact.net_avoided_energy_kwh = total_energy
    impact.impact_reduction_percentage = ((total_co2 - 0.08) / total_co2) * 100
    impact.calculation_version = "1.0"
    impact.data_quality_score = "estimated"
    impact.assumed_wears = 50
    impact.assumed_washes = 25

    return impact


def calculate_equivalents(impact_data) -> dict:
    if not impact_data or not impact_data.net_avoided_co2:
        return {"km_not_driven": 0, "trees_planted": 0, "days_drinking_water": 0, "smartphone_charges": 0}

    co2_kg = float(impact_data.net_avoided_co2)
    water_liters = float(impact_data.net_avoided_water) if impact_data.net_avoided_water else 0
    energy_kwh = float(impact_data.net_avoided_energy_kwh) if impact_data.net_avoided_energy_kwh else 0

    return {
        "km_not_driven": co2_kg * 5.26,
        "trees_planted": co2_kg / 21,
        "days_drinking_water": water_liters / 2,
        "smartphone_charges": int(energy_kwh * 125)
    }


# ── Swap impact endpoint (kept from original) ───────────────────────────

@router.get("/swap-impact/{clothing_id_1}/{clothing_id_2}", response_model=SwapImpactResponse)
async def get_swap_impact_analysis(
    clothing_id_1: int,
    clothing_id_2: int,
    transport_distance_km: Optional[float] = Query(None),
    transport_method: Optional[str] = Query("car"),
    db: Session = Depends(get_db)
):
    """Get comprehensive environmental impact analysis for swapping two clothing items."""

    if clothing_id_1 == clothing_id_2:
        raise HTTPException(status_code=400, detail="Cannot analyze swap impact for the same item")

    item1 = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id_1).first()
    item2 = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id_2).first()

    if not item1:
        raise HTTPException(status_code=404, detail=f"Clothing item {clothing_id_1} not found")
    if not item2:
        raise HTTPException(status_code=404, detail=f"Clothing item {clothing_id_2} not found")

    # ── OWNERSHIP CHECK: items must belong to different people ──
    if item1.owner_user_id == item2.owner_user_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot swap two items that belong to the same person"
        )

    if item1.status not in ['available', 'listed']:
        raise HTTPException(status_code=400, detail=f"Item {clothing_id_1} is not available for swap")
    if item2.status not in ['available', 'listed']:
        raise HTTPException(status_code=400, detail=f"Item {clothing_id_2} is not available for swap")

    impact1 = get_or_calculate_impact(item1, db)
    impact2 = get_or_calculate_impact(item2, db)

    brand1_data = get_brand_sustainability(item1, db)
    brand2_data = get_brand_sustainability(item2, db)

    swap_analysis = calculate_swap_impact(
        item1, item2, impact1, impact2, brand1_data, brand2_data,
        transport_distance_km, transport_method
    )

    return swap_analysis


def get_or_calculate_impact(clothing_item, db):
    impact_data = db.query(ClothingEnvironmentalImpact).filter(
        ClothingEnvironmentalImpact.clothing_id == clothing_item.clothing_id
    ).first()
    if not impact_data:
        impact_data = calculate_impact_from_materials(clothing_item, db)
    return impact_data


def get_brand_sustainability(clothing_item, db):
    if not clothing_item.brand_id:
        return None
    return db.query(BrandSustainability).filter(
        BrandSustainability.brand_id == clothing_item.brand_id
    ).first()


def calculate_swap_impact(item1, item2, impact1, impact2, brand1_data, brand2_data,
                         transport_distance_km, transport_method):
    item1_summary = build_item_summary(item1)
    item2_summary = build_item_summary(item2)
    item1_cost = calculate_item_environmental_cost(impact1)
    item2_cost = calculate_item_environmental_cost(impact2)
    condition1_factor = get_condition_factor(item1.condition)
    condition2_factor = get_condition_factor(item2.condition)
    brand1_context = build_brand_context(item1, brand1_data) if brand1_data else None
    brand2_context = build_brand_context(item2, brand2_data) if brand2_data else None
    transport_impact = calculate_transport_impact(transport_distance_km, transport_method)
    impact_comparison = calculate_impact_comparison(item1_cost, item2_cost, item1_summary, item2_summary)
    swap_score = calculate_swap_score(
        item1_cost, item2_cost, condition1_factor, condition2_factor,
        brand1_data, brand2_data, transport_impact
    )
    net_co2_change = impact_comparison["net_environmental_change_co2"]
    equivalents = calculate_swap_equivalents(abs(net_co2_change))
    recommendations = generate_swap_recommendations(swap_score, transport_impact, item1, item2)

    return {
        "item1_summary": item1_summary,
        "item2_summary": item2_summary,
        "item1_impact": {
            "clothing_id": item1.clothing_id,
            "item_summary": item1_summary,
            "environmental_cost": item1_cost,
            "condition_factor": condition1_factor,
            "brand_sustainability": brand1_context
        },
        "item2_impact": {
            "clothing_id": item2.clothing_id,
            "item_summary": item2_summary,
            "environmental_cost": item2_cost,
            "condition_factor": condition2_factor,
            "brand_sustainability": brand2_context
        },
        "impact_comparison": impact_comparison,
        "transport_impact": transport_impact,
        "swap_score": swap_score,
        "equivalents": equivalents,
        "recommendations": recommendations,
        "calculation_metadata": {
            "version": "1.0",
            "data_quality": "calculated",
            "calculation_date": "2024-12-01",
            "methodology": "comparative_lifecycle_assessment"
        }
    }


def build_item_summary(item):
    return {
        "clothing_id": item.clothing_id,
        "name": item.description or f"{item.clothing_type} by {item.brand or 'Unknown'}",
        "type": item.clothing_type,
        "brand": item.brand,
        "size": item.size,
        "condition": item.condition,
        "material_composition": item.material_composition
    }


def calculate_item_environmental_cost(impact_data):
    if not impact_data:
        return {"co2_kg": 5.0, "water_liters": 2000, "energy_kwh": 25}
    return {
        "co2_kg": float(impact_data.new_total_co2) if impact_data.new_total_co2 else 5.0,
        "water_liters": float(impact_data.new_total_water) if impact_data.new_total_water else 2000,
        "energy_kwh": float(impact_data.new_total_energy_kwh) if impact_data.new_total_energy_kwh else 25
    }


def get_condition_factor(condition):
    factors = {"new_with_tags": 1.2, "excellent": 1.1, "very_good": 1.0, "good": 0.95, "fair": 0.9, "poor": 0.8}
    return factors.get(condition, 1.0)


def build_brand_context(item, brand_data):
    if not brand_data:
        return None
    return {
        "brand_name": item.brand,
        "transparency_score": brand_data.transparency_index_score,
        "sustainability_rating": brand_data.overall_rating,
        "certifications": [],
        "impact_commitments": {
            "carbon_neutral": brand_data.has_climate_targets,
            "renewable_energy": brand_data.discloses_ghg_emissions,
            "sustainable_materials": brand_data.publishes_supplier_list,
            "waste_reduction": brand_data.discloses_waste_data,
            "water_stewardship": brand_data.discloses_water_usage
        }
    }


def calculate_transport_impact(distance_km, method):
    if not distance_km:
        return None
    emissions = {"walking": 0.0, "bike": 0.0, "car": 0.21, "public_transport": 0.05, "bus": 0.08, "train": 0.04, "motorcycle": 0.11}
    factor = emissions.get(method, 0.15)
    co2 = distance_km * factor
    return {"distance_km": distance_km, "transport_method": method, "co2_emissions": co2, "penalty_applied": min(2.0, co2 * 0.5)}


def calculate_impact_comparison(item1_cost, item2_cost, item1_summary, item2_summary):
    net_co2 = item2_cost["co2_kg"] - item1_cost["co2_kg"]
    net_water = item2_cost["water_liters"] - item1_cost["water_liters"]
    net_energy = item2_cost["energy_kwh"] - item1_cost["energy_kwh"]

    if net_co2 < 0:
        desc = f"Environmental benefit: {abs(net_co2):.1f} kg CO2 saved"
    elif net_co2 > 0:
        desc = f"Environmental cost: {net_co2:.1f} kg CO2 added"
    else:
        desc = "Neutral environmental impact"

    return {
        "item1_gets_description": f"{item2_summary['type']} with {item2_cost['co2_kg']:.1f} kg CO2 footprint",
        "item2_gets_description": f"{item1_summary['type']} with {item1_cost['co2_kg']:.1f} kg CO2 footprint",
        "net_environmental_change_co2": net_co2,
        "net_environmental_change_water": net_water,
        "net_environmental_change_energy": net_energy,
        "impact_description": desc
    }


def calculate_swap_score(item1_cost, item2_cost, condition1_factor, condition2_factor, brand1_data, brand2_data, transport_impact):
    co2_delta = item1_cost["co2_kg"] - item2_cost["co2_kg"]
    max_impact = max(item1_cost["co2_kg"], item2_cost["co2_kg"], 10.0)
    base_score = 5.0 + (co2_delta / max_impact) * 5.0
    base_score = max(0.0, min(10.0, base_score))
    transport_penalty = transport_impact["penalty_applied"] if transport_impact else 0.0
    condition_bonus = ((condition1_factor + condition2_factor) / 2 - 1.0) * 0.5
    brand_bonus = 0.0
    if brand1_data and brand1_data.transparency_index_score:
        brand_bonus += (brand1_data.transparency_index_score / 100) * 0.25
    if brand2_data and brand2_data.transparency_index_score:
        brand_bonus += (brand2_data.transparency_index_score / 100) * 0.25
    final_score = max(0.0, min(10.0, base_score - transport_penalty + condition_bonus + brand_bonus))

    return {
        "score": round(final_score, 2),
        "grade_description": get_score_description(final_score),
        "breakdown": {
            "base_score": round(base_score, 2),
            "transport_penalty": round(-transport_penalty, 2),
            "condition_bonus": round(condition_bonus, 2),
            "brand_bonus": round(brand_bonus, 2),
            "final_score": round(final_score, 2)
        },
        "environmental_benefit": co2_delta > (transport_impact["co2_emissions"] if transport_impact else 0)
    }


def get_score_description(score):
    if score >= 9.0: return "Outstanding - Major environmental benefit"
    elif score >= 7.0: return "Excellent - Significant positive impact"
    elif score >= 5.0: return "Good - Moderate environmental benefit"
    elif score >= 3.0: return "Fair - Slight environmental cost"
    elif score >= 1.0: return "Poor - Notable environmental cost"
    else: return "Very Poor - Significant environmental harm"


def calculate_swap_equivalents(net_co2_change):
    if net_co2_change <= 0:
        return {"km_not_driven": 0, "trees_planted": 0, "days_drinking_water": 0, "smartphone_charges": 0}
    return {"km_not_driven": net_co2_change * 5.26, "trees_planted": net_co2_change / 21, "days_drinking_water": 0, "smartphone_charges": 0}


def generate_swap_recommendations(swap_score, transport_impact, item1, item2):
    recommendations = []
    score = swap_score["score"]
    if score < 5.0:
        recommendations.append("Consider if this swap aligns with your sustainability goals")
        recommendations.append("Look for items with lower environmental impact")
    if transport_impact and transport_impact["penalty_applied"] > 0.5:
        recommendations.append("Consider meeting closer to reduce transportation impact")
        recommendations.append("Try using public transport, biking, or walking for the exchange")
    if score >= 7.0:
        recommendations.append("Excellent choice! This swap provides significant environmental benefit")
    if not recommendations:
        recommendations.append("This is a moderately sustainable swap choice")
    return recommendations