from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    clothing_id: int
    reviewer_id: int
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    review_id: int
    clothing_id: int
    reviewer_id: int
    reviewer_name: Optional[str] = None
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReviewSummary(BaseModel):
    clothing_id: int
    average_rating: float
    total_reviews: int
    rating_breakdown: dict


class ReviewList(BaseModel):
    reviews: List[ReviewResponse]
    total: int
    average_rating: float
    rating_breakdown: dict