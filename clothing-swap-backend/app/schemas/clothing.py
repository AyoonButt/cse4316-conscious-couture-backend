from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field


class ClothingItemBase(BaseModel):
    clothing_type: str = Field(..., description="Type of clothing (t-shirt, jeans, etc.)")
    brand: Optional[str] = Field(None, description="Brand name")
    description: Optional[str] = Field(None, description="Description of the clothing item")
    size: str = Field(..., description="Size of the clothing item")
    color: Optional[str] = Field(None, description="Primary color")
    condition: str = Field(..., description="Condition (excellent, good, fair, poor)")
    material_composition: Dict[str, float] = Field(..., description="Material composition as percentage")
    weight_grams: Optional[int] = Field(None, description="Weight in grams")
    primary_image_url: Optional[str] = Field(None, description="URL of primary image")
    additional_images: Optional[List[str]] = Field(default_factory=list, description="List of additional image URLs")


class ClothingItemCreate(ClothingItemBase):
    owner_user_id: int = Field(..., description="ID of the user who owns this item")


class ClothingItemUpdate(BaseModel):
    clothing_type: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    condition: Optional[str] = None
    material_composition: Optional[Dict[str, float]] = None
    weight_grams: Optional[int] = None
    primary_image_url: Optional[str] = None
    additional_images: Optional[List[str]] = None
    status: Optional[str] = None


class ClothingItemResponse(ClothingItemBase):
    clothing_id: int
    owner_user_id: int
    brand_id: Optional[int] = None
    composition_verified: bool = False
    composition_verification_count: int = 0
    weight_estimated: bool = True
    status: str = "available"
    times_swapped: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClothingItemList(BaseModel):
    items: List[ClothingItemResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class ClothingItemFilter(BaseModel):
    clothing_type: Optional[str] = None
    brand: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None
    status: Optional[str] = "available"
    owner_user_id: Optional[int] = None
    search: Optional[str] = None
    min_times_swapped: Optional[int] = None
    max_times_swapped: Optional[int] = None