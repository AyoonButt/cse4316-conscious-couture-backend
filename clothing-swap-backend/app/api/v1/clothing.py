from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
import math

from ...database import get_db
from ...models.clothing import ClothingItem
from ...models.user import User
from ...models.brand import BrandSustainability
from ...schemas.clothing import (
    ClothingItemCreate,
    ClothingItemUpdate,
    ClothingItemResponse,
    ClothingItemList,
)

router = APIRouter()


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


@router.get("/{clothing_id}", response_model=ClothingItemResponse)
async def get_clothing_item(clothing_id: int, db: Session = Depends(get_db)):
    """Get a specific clothing item by ID."""
    
    clothing_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()
    
    if not clothing_item:
        raise HTTPException(status_code=404, detail="Clothing item not found")
    
    return clothing_item


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