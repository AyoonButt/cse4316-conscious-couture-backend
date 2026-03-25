from fastapi import APIRouter, Depends, HTTPException, Query
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

router = APIRouter()


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
    
    # Apply filters
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
    
    # Category filtering would require additional logic based on frontend categories
    # For now, we'll implement basic filtering
    
    # Count total items
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page).all()
    
    # Calculate total pages
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


@router.get("/{clothing_id}", response_model=ClothingItemAvailabilityResponse)
async def get_clothing_item(clothing_id: int, db: Session = Depends(get_db)):
    """Get a specific clothing item by ID."""
    
    clothing_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()
    
    if not clothing_item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    item_payload = ClothingItemResponse.model_validate(clothing_item).model_dump()
    status = item_payload.get("status")
    return ClothingItemAvailabilityResponse(
        **item_payload,
        available=bool(clothing_item.available),
        unavailable_reason=clothing_item.unavailable_reason or _get_unavailable_reason(status),
    )


@router.post("/", response_model=ClothingItemResponse)
async def create_clothing_item(
    clothing_data: ClothingItemCreate,
    db: Session = Depends(get_db)
):
    """Create a new clothing item."""
    
    # Verify the owner user exists
    user = db.query(User).filter(User.user_id == clothing_data.owner_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Owner user not found")
    
    # Look up brand_id if brand is provided
    brand_id = None
    if clothing_data.brand:
        brand = db.query(BrandSustainability).filter(
            BrandSustainability.brand_name.ilike(clothing_data.brand)
        ).first()
        if brand:
            brand_id = brand.brand_id
    
    # Create the clothing item
    db_clothing_item = ClothingItem(
        owner_user_id=clothing_data.owner_user_id,
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


@router.put("/{clothing_id}", response_model=ClothingItemResponse)
async def update_clothing_item(
    clothing_id: int,
    clothing_data: ClothingItemUpdate,
    db: Session = Depends(get_db)
):
    """Update a clothing item."""
    
    clothing_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()
    
    if not clothing_item:
        raise HTTPException(status_code=404, detail="Clothing item not found")
    
    # Update fields if provided
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


@router.delete("/{clothing_id}")
async def delete_clothing_item(clothing_id: int, db: Session = Depends(get_db)):
    """Delete a clothing item."""
    
    clothing_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()
    
    if not clothing_item:
        raise HTTPException(status_code=404, detail="Clothing item not found")
    
    db.delete(clothing_item)
    db.commit()
    
    return {"message": "Clothing item deleted successfully"}


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


@router.post("/{clothing_id}/purchase")
async def purchase_clothing_item(
    clothing_id: int,
    buyer_user_id: int,
    amount: Decimal,
    db: Session = Depends(get_db)
):
    """
    Initiate a payment for purchasing a clothing item.
    
    Returns payment details needed for Stripe payment processing on frontend.
    """
    
    # 1) Find clothing item
    clothing_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()
    if not clothing_item:
        raise HTTPException(status_code=404, detail="Clothing item not found")
    
    # 2) Verify item is available for purchase
    if clothing_item.status != "available":
        raise HTTPException(status_code=400, detail=f"Item is not available (status: {clothing_item.status})")
    
    # 3) Verify buyer exists
    buyer = db.query(User).filter(User.user_id == buyer_user_id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer user not found")
    
    # 4) Prevent buying own item
    if clothing_item.owner_user_id == buyer_user_id:
        raise HTTPException(status_code=400, detail="Cannot purchase your own items")
    
    # 5) Validate amount is positive
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    # 6) Create payment for clothing purchase
    # Note: We use clothing_id as the transaction identifier in payment metadata
    try:
        payment, client_secret = create_payment(
            db,
            transaction_id=clothing_id,
            amount=amount,
            currency="usd",
        )
    except HTTPException as e:
        raise e
    
    # 7) Return payment details for frontend
    return {
        "clothing_id": clothing_id,
        "buyer_user_id": buyer_user_id,
        "payment_id": payment.id,
        "payment_status": payment.status,
        "client_secret": client_secret,
        "amount": str(amount),
        "currency": "usd"
    }
@router.get("/{clothing_id}/sustainability", response_model=SustainabilityMetricsResponse)
async def get_clothing_sustainability_metrics(clothing_id: int, db: Session = Depends(get_db)):
    """Get comprehensive sustainability metrics for a specific clothing item."""
    
    # Get the clothing item with related data
    clothing_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()
    
    if not clothing_item:
        raise HTTPException(status_code=404, detail="Clothing item not found")
    
    # Get environmental impact data
    impact_data = db.query(ClothingEnvironmentalImpact).filter(
        ClothingEnvironmentalImpact.clothing_id == clothing_id
    ).first()
    
    # Get brand sustainability data
    brand_data = None
    if clothing_item.brand_id:
        brand_data = db.query(BrandSustainability).filter(
            BrandSustainability.brand_id == clothing_item.brand_id
        ).first()
    
    # If no impact data exists, calculate it from material composition
    if not impact_data:
        impact_data = calculate_impact_from_materials(clothing_item, db)
    
    # Build item summary
    item_summary = {
        "name": clothing_item.description or f"{clothing_item.clothing_type} by {clothing_item.brand or 'Unknown'}",
        "type": clothing_item.clothing_type,
        "brand": clothing_item.brand,
        "size": clothing_item.size,
        "condition": clothing_item.condition,
        "material_composition": clothing_item.material_composition
    }
    
    # Calculate equivalents using existing method or custom calculation
    equivalents_data = {}
    if impact_data:
        equivalents_data = impact_data.get_equivalents() if hasattr(impact_data, 'get_equivalents') else calculate_equivalents(impact_data)
    
    # Build new garment impact
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
    
    # Build reuse platform impact
    reuse_impact = {
        "co2_kg": float(impact_data.reuse_total_co2) if impact_data and impact_data.reuse_total_co2 else 0.08,
        "breakdown": {
            "collection": float(impact_data.reuse_collection_co2) if impact_data and impact_data.reuse_collection_co2 else 0.05,
            "sorting": float(impact_data.reuse_sorting_co2) if impact_data and impact_data.reuse_sorting_co2 else 0.02,
            "transport": float(impact_data.reuse_transport_co2) if impact_data and impact_data.reuse_transport_co2 else 0.01,
            "platform_overhead": float(impact_data.reuse_platform_co2) if impact_data and impact_data.reuse_platform_co2 else 0.01
        }
    }
    
    # Calculate net avoided impact
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
    
    # Calculate equivalents
    equivalents = {
        "km_not_driven": net_co2 * 5.26,  # Average car emits 0.19 kg CO2/km
        "trees_planted": net_co2 / 21,    # Tree absorbs ~21 kg CO2/year
        "days_drinking_water": net_water / 2,  # 2L per day average
        "smartphone_charges": int(net_energy * 125)  # ~8Wh per smartphone charge
    }
    
    # Build brand context
    brand_context = {
        "brand_name": clothing_item.brand,
        "transparency_score": brand_data.transparency_index_score if brand_data else None,
        "sustainability_rating": brand_data.overall_rating if brand_data else None,
        "certifications": [],  # Could be expanded with certification data
        "impact_commitments": {
            "publishes_supplier_list": brand_data.publishes_supplier_list if brand_data else None,
            "discloses_ghg_emissions": brand_data.discloses_ghg_emissions if brand_data else None,
            "discloses_water_usage": brand_data.discloses_water_usage if brand_data else None,
            "has_climate_targets": brand_data.has_climate_targets if brand_data else None
        } if brand_data else {}
    }
    
    # Calculation metadata
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
    
    # Default impact values for common garments (t-shirt example)
    total_co2 = 15.5
    total_water = 2700.0
    total_energy = 42.3
    
    # Try to get more accurate data based on material composition
    if clothing_item.material_composition:
        weighted_co2 = 0
        weighted_water = 0
        weighted_energy = 0
        
        for material_name, percentage in clothing_item.material_composition.items():
            # Look up material data
            material = db.query(MaterialReference).filter(
                MaterialReference.material_name.ilike(f"%{material_name}%")
            ).first()
            
            if material and percentage > 0:
                weight_factor = percentage / 100
                weighted_co2 += float(material.co2_per_kg or 10) * weight_factor
                weighted_water += float(material.water_liters_per_kg or 2000) * weight_factor
                weighted_energy += float(material.energy_mj_per_kg or 50) * weight_factor
        
        # Use calculated values if we found material data
        if weighted_co2 > 0:
            # Assume typical garment weight of 200g
            garment_weight_kg = (clothing_item.weight_grams or 200) / 1000
            total_co2 = weighted_co2 * garment_weight_kg
            total_water = weighted_water * garment_weight_kg
            total_energy = (weighted_energy * garment_weight_kg) / 3.6  # Convert MJ to kWh
    
    # Create temporary impact object for calculations
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
    """Calculate real-world equivalents for environmental impact."""
    if not impact_data or not impact_data.net_avoided_co2:
        return {
            "km_not_driven": 0,
            "trees_planted": 0,
            "days_drinking_water": 0,
            "smartphone_charges": 0
        }
    
    co2_kg = float(impact_data.net_avoided_co2)
    water_liters = float(impact_data.net_avoided_water) if impact_data.net_avoided_water else 0
    energy_kwh = float(impact_data.net_avoided_energy_kwh) if impact_data.net_avoided_energy_kwh else 0
    
    return {
        "km_not_driven": co2_kg * 5.26,
        "trees_planted": co2_kg / 21,
        "days_drinking_water": water_liters / 2,
        "smartphone_charges": int(energy_kwh * 125)
    }


@router.get("/swap-impact/{clothing_id_1}/{clothing_id_2}", response_model=SwapImpactResponse)
async def get_swap_impact_analysis(
    clothing_id_1: int, 
    clothing_id_2: int,
    transport_distance_km: Optional[float] = Query(None, description="Transport distance in kilometers"),
    transport_method: Optional[str] = Query("car", description="Transport method (car, bike, walking, etc.)"),
    db: Session = Depends(get_db)
):
    """Get comprehensive environmental impact analysis for swapping two clothing items."""
    
    # Validate that the two items are different
    if clothing_id_1 == clothing_id_2:
        raise HTTPException(status_code=400, detail="Cannot analyze swap impact for the same item")
    
    # Get both clothing items
    item1 = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id_1).first()
    item2 = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id_2).first()
    
    if not item1:
        raise HTTPException(status_code=404, detail=f"Clothing item {clothing_id_1} not found")
    if not item2:
        raise HTTPException(status_code=404, detail=f"Clothing item {clothing_id_2} not found")
    
    # Check if items are available for swap
    if item1.status not in ['available', 'listed']:
        raise HTTPException(status_code=400, detail=f"Item {clothing_id_1} is not available for swap")
    if item2.status not in ['available', 'listed']:
        raise HTTPException(status_code=400, detail=f"Item {clothing_id_2} is not available for swap")
    
    # Get environmental impact data for both items
    impact1 = get_or_calculate_impact(item1, db)
    impact2 = get_or_calculate_impact(item2, db)
    
    # Get brand sustainability data
    brand1_data = get_brand_sustainability(item1, db)
    brand2_data = get_brand_sustainability(item2, db)
    
    # Calculate swap impact analysis
    swap_analysis = calculate_swap_impact(
        item1, item2, impact1, impact2, brand1_data, brand2_data,
        transport_distance_km, transport_method
    )
    
    return swap_analysis


def get_or_calculate_impact(clothing_item, db):
    """Get environmental impact data or calculate if missing."""
    impact_data = db.query(ClothingEnvironmentalImpact).filter(
        ClothingEnvironmentalImpact.clothing_id == clothing_item.clothing_id
    ).first()
    
    if not impact_data:
        impact_data = calculate_impact_from_materials(clothing_item, db)
    
    return impact_data


def get_brand_sustainability(clothing_item, db):
    """Get brand sustainability data if available."""
    if not clothing_item.brand_id:
        return None
    
    return db.query(BrandSustainability).filter(
        BrandSustainability.brand_id == clothing_item.brand_id
    ).first()


def calculate_swap_impact(item1, item2, impact1, impact2, brand1_data, brand2_data, 
                         transport_distance_km, transport_method):
    """Calculate comprehensive swap impact analysis with 0-10 scoring."""
    
    # Build item summaries
    item1_summary = build_item_summary(item1)
    item2_summary = build_item_summary(item2)
    
    # Calculate environmental costs
    item1_cost = calculate_item_environmental_cost(impact1)
    item2_cost = calculate_item_environmental_cost(impact2)
    
    # Calculate condition factors
    condition1_factor = get_condition_factor(item1.condition)
    condition2_factor = get_condition_factor(item2.condition)
    
    # Build brand contexts
    brand1_context = build_brand_context(item1, brand1_data) if brand1_data else None
    brand2_context = build_brand_context(item2, brand2_data) if brand2_data else None
    
    # Calculate transport impact
    transport_impact = calculate_transport_impact(transport_distance_km, transport_method)
    
    # Calculate impact comparison (from perspective of user1 getting item2)
    impact_comparison = calculate_impact_comparison(item1_cost, item2_cost, item1_summary, item2_summary)
    
    # Calculate swap score
    swap_score = calculate_swap_score(
        item1_cost, item2_cost, condition1_factor, condition2_factor,
        brand1_data, brand2_data, transport_impact
    )
    
    # Calculate equivalents for the net change
    net_co2_change = impact_comparison["net_environmental_change_co2"]
    equivalents = calculate_swap_equivalents(abs(net_co2_change))
    
    # Generate recommendations
    recommendations = generate_swap_recommendations(swap_score, transport_impact, item1, item2)
    
    # Build participant impacts
    item1_impact = {
        "clothing_id": item1.clothing_id,
        "item_summary": item1_summary,
        "environmental_cost": item1_cost,
        "condition_factor": condition1_factor,
        "brand_sustainability": brand1_context
    }
    
    item2_impact = {
        "clothing_id": item2.clothing_id,
        "item_summary": item2_summary,
        "environmental_cost": item2_cost,
        "condition_factor": condition2_factor,
        "brand_sustainability": brand2_context
    }
    
    return {
        "item1_summary": item1_summary,
        "item2_summary": item2_summary,
        "item1_impact": item1_impact,
        "item2_impact": item2_impact,
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
    """Build basic item summary."""
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
    """Calculate total environmental cost of an item."""
    if not impact_data:
        return {
            "co2_kg": 5.0,  # Default estimate
            "water_liters": 2000,
            "energy_kwh": 25
        }
    
    return {
        "co2_kg": float(impact_data.new_total_co2) if impact_data.new_total_co2 else 5.0,
        "water_liters": float(impact_data.new_total_water) if impact_data.new_total_water else 2000,
        "energy_kwh": float(impact_data.new_total_energy_kwh) if impact_data.new_total_energy_kwh else 25
    }


def get_condition_factor(condition):
    """Get condition factor for scoring (better condition = higher factor)."""
    condition_factors = {
        "new_with_tags": 1.2,
        "excellent": 1.1,
        "very_good": 1.0,
        "good": 0.95,
        "fair": 0.9,
        "poor": 0.8
    }
    return condition_factors.get(condition, 1.0)


def build_brand_context(item, brand_data):
    """Build brand sustainability context."""
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
    """Calculate transportation impact."""
    if not distance_km:
        return None
    
    # CO2 emissions per km by transport method (kg CO2-eq per km)
    transport_emissions = {
        "walking": 0.0,
        "bike": 0.0,
        "car": 0.21,
        "public_transport": 0.05,
        "bus": 0.08,
        "train": 0.04,
        "motorcycle": 0.11
    }
    
    emission_factor = transport_emissions.get(method, 0.15)
    co2_emissions = distance_km * emission_factor
    
    # Calculate penalty (more aggressive for high-emission transport)
    penalty_applied = min(2.0, co2_emissions * 0.5)
    
    return {
        "distance_km": distance_km,
        "transport_method": method,
        "co2_emissions": co2_emissions,
        "penalty_applied": penalty_applied
    }


def calculate_impact_comparison(item1_cost, item2_cost, item1_summary, item2_summary):
    """Calculate environmental impact comparison."""
    # Calculate net change from user1's perspective (getting item2, giving item1)
    net_co2 = item2_cost["co2_kg"] - item1_cost["co2_kg"]
    net_water = item2_cost["water_liters"] - item1_cost["water_liters"]
    net_energy = item2_cost["energy_kwh"] - item1_cost["energy_kwh"]
    
    # Generate descriptions
    item1_gets_desc = f"{item2_summary['type']} with {item2_cost['co2_kg']:.1f} kg CO2 footprint"
    item2_gets_desc = f"{item1_summary['type']} with {item1_cost['co2_kg']:.1f} kg CO2 footprint"
    
    if net_co2 < 0:
        impact_desc = f"Environmental benefit: {abs(net_co2):.1f} kg CO2 saved"
    elif net_co2 > 0:
        impact_desc = f"Environmental cost: {net_co2:.1f} kg CO2 added"
    else:
        impact_desc = "Neutral environmental impact"
    
    return {
        "item1_gets_description": item1_gets_desc,
        "item2_gets_description": item2_gets_desc,
        "net_environmental_change_co2": net_co2,
        "net_environmental_change_water": net_water,
        "net_environmental_change_energy": net_energy,
        "impact_description": impact_desc
    }


def calculate_swap_score(item1_cost, item2_cost, condition1_factor, condition2_factor,
                        brand1_data, brand2_data, transport_impact):
    """Calculate swap score from 0.00 to 10.00."""
    
    # Base score calculation (comparison of environmental costs)
    co2_delta = item1_cost["co2_kg"] - item2_cost["co2_kg"]  # Positive = user1 benefits
    max_impact = max(item1_cost["co2_kg"], item2_cost["co2_kg"], 10.0)  # Avoid division by zero
    
    # Base score: 5.0 = neutral, higher when getting lower impact item
    base_score = 5.0 + (co2_delta / max_impact) * 5.0
    base_score = max(0.0, min(10.0, base_score))
    
    # Transport penalty
    transport_penalty = transport_impact["penalty_applied"] if transport_impact else 0.0
    
    # Condition bonus (average of both items)
    avg_condition_factor = (condition1_factor + condition2_factor) / 2
    condition_bonus = (avg_condition_factor - 1.0) * 0.5
    
    # Brand sustainability bonus
    brand_bonus = 0.0
    if brand1_data and brand1_data.transparency_index_score:
        brand_bonus += (brand1_data.transparency_index_score / 100) * 0.25
    if brand2_data and brand2_data.transparency_index_score:
        brand_bonus += (brand2_data.transparency_index_score / 100) * 0.25
    
    # Final score
    final_score = base_score - transport_penalty + condition_bonus + brand_bonus
    final_score = max(0.0, min(10.0, final_score))
    
    # Grade description
    grade_description = get_score_description(final_score)
    
    # Environmental benefit check
    environmental_benefit = co2_delta > (transport_impact["co2_emissions"] if transport_impact else 0)
    
    return {
        "score": round(final_score, 2),
        "grade_description": grade_description,
        "breakdown": {
            "base_score": round(base_score, 2),
            "transport_penalty": round(-transport_penalty, 2),
            "condition_bonus": round(condition_bonus, 2),
            "brand_bonus": round(brand_bonus, 2),
            "final_score": round(final_score, 2)
        },
        "environmental_benefit": environmental_benefit
    }


def get_score_description(score):
    """Get description for score."""
    if score >= 9.0:
        return "Outstanding - Major environmental benefit"
    elif score >= 7.0:
        return "Excellent - Significant positive impact"
    elif score >= 5.0:
        return "Good - Moderate environmental benefit"
    elif score >= 3.0:
        return "Fair - Slight environmental cost"
    elif score >= 1.0:
        return "Poor - Notable environmental cost"
    else:
        return "Very Poor - Significant environmental harm"


def calculate_swap_equivalents(net_co2_change):
    """Calculate real-world equivalents for the net CO2 change."""
    if net_co2_change <= 0:
        return {
            "km_not_driven": 0,
            "trees_planted": 0,
            "days_drinking_water": 0,
            "smartphone_charges": 0
        }
    
    return {
        "km_not_driven": net_co2_change * 5.26,
        "trees_planted": net_co2_change / 21,
        "days_drinking_water": 0,  # Not applicable for swap comparison
        "smartphone_charges": 0    # Not applicable for swap comparison
    }


def generate_swap_recommendations(swap_score, transport_impact, item1, item2):
    """Generate recommendations for improving the swap."""
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
