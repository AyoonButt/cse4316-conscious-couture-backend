from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func

from ...database import get_db
from ...models.review import Review
from ...models.clothing import ClothingItem
from ...models.user import User
from ...schemas.review import (
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    ReviewList,
)

router = APIRouter()


def _build_review_response(review: Review, db: Session) -> dict:
    """Build a ReviewResponse dict with the reviewer's display name."""
    user = db.query(User).filter(User.user_id == review.reviewer_id).first()
    return {
        "review_id": review.review_id,
        "clothing_id": review.clothing_id,
        "reviewer_id": review.reviewer_id,
        "reviewer_name": user.display_name if user else "Anonymous",
        "rating": review.rating,
        "title": review.title,
        "comment": review.comment,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
    }


def _get_rating_breakdown(db: Session, clothing_id: int) -> dict:
    """Get count of reviews for each star level."""
    rows = (
        db.query(Review.rating, sql_func.count(Review.review_id))
        .filter(Review.clothing_id == clothing_id)
        .group_by(Review.rating)
        .all()
    )
    breakdown = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for rating_val, count in rows:
        breakdown[str(rating_val)] = count
    return breakdown


# ── GET reviews for a clothing item ──────────────────────────────────────────

@router.get("/clothing/{clothing_id}", response_model=ReviewList)
async def get_reviews_for_item(
    clothing_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort: str = Query("newest", regex="^(newest|oldest|highest|lowest)$"),
    db: Session = Depends(get_db),
):
    """Get all reviews for a specific clothing item."""
    # Verify item exists
    item = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    # Base query
    query = db.query(Review).filter(Review.clothing_id == clothing_id)

    # Sorting
    if sort == "newest":
        query = query.order_by(Review.created_at.desc())
    elif sort == "oldest":
        query = query.order_by(Review.created_at.asc())
    elif sort == "highest":
        query = query.order_by(Review.rating.desc(), Review.created_at.desc())
    elif sort == "lowest":
        query = query.order_by(Review.rating.asc(), Review.created_at.desc())

    total = query.count()

    # Average rating
    avg_result = (
        db.query(sql_func.avg(Review.rating))
        .filter(Review.clothing_id == clothing_id)
        .scalar()
    )
    average_rating = round(float(avg_result), 2) if avg_result else 0.0

    # Pagination
    offset = (page - 1) * per_page
    reviews = query.offset(offset).limit(per_page).all()

    # Build response
    review_responses = [_build_review_response(r, db) for r in reviews]
    breakdown = _get_rating_breakdown(db, clothing_id)

    return {
        "reviews": review_responses,
        "total": total,
        "average_rating": average_rating,
        "rating_breakdown": breakdown,
    }


# ── GET summary (lightweight, no review text) ────────────────────────────────

@router.get("/clothing/{clothing_id}/summary")
async def get_review_summary(
    clothing_id: int,
    db: Session = Depends(get_db),
):
    """Get just the average rating + count for a clothing item (lightweight)."""
    item = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    total = db.query(Review).filter(Review.clothing_id == clothing_id).count()
    avg_result = (
        db.query(sql_func.avg(Review.rating))
        .filter(Review.clothing_id == clothing_id)
        .scalar()
    )

    return {
        "clothing_id": clothing_id,
        "average_rating": round(float(avg_result), 2) if avg_result else 0.0,
        "total_reviews": total,
        "rating_breakdown": _get_rating_breakdown(db, clothing_id),
    }


# ── POST create a review ─────────────────────────────────────────────────────

@router.post("/", response_model=ReviewResponse, status_code=201)
async def create_review(
    review_data: ReviewCreate,
    db: Session = Depends(get_db),
):
    """Create a new review for a clothing item."""
    # Verify clothing item exists
    item = db.query(ClothingItem).filter(
        ClothingItem.clothing_id == review_data.clothing_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    # Verify reviewer exists
    reviewer = db.query(User).filter(User.user_id == review_data.reviewer_id).first()
    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer user not found")

    # Prevent reviewing your own item
    if item.owner_user_id == review_data.reviewer_id:
        raise HTTPException(status_code=400, detail="You cannot review your own item")

    # Prevent duplicate reviews
    existing = (
        db.query(Review)
        .filter(
            Review.clothing_id == review_data.clothing_id,
            Review.reviewer_id == review_data.reviewer_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="You have already reviewed this item. Use PUT to update your review.",
        )

    new_review = Review(
        clothing_id=review_data.clothing_id,
        reviewer_id=review_data.reviewer_id,
        rating=review_data.rating,
        title=review_data.title,
        comment=review_data.comment,
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return _build_review_response(new_review, db)


# ── PUT update a review ──────────────────────────────────────────────────────

@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    review_data: ReviewUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing review."""
    review = db.query(Review).filter(Review.review_id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review_data.rating is not None:
        review.rating = review_data.rating
    if review_data.title is not None:
        review.title = review_data.title
    if review_data.comment is not None:
        review.comment = review_data.comment

    db.commit()
    db.refresh(review)
    return _build_review_response(review, db)


# ── DELETE a review ───────────────────────────────────────────────────────────

@router.delete("/{review_id}")
async def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
):
    """Delete a review."""
    review = db.query(Review).filter(Review.review_id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    db.delete(review)
    db.commit()
    return {"message": f"Review {review_id} deleted successfully"}


# ── GET reviews written by a specific user ────────────────────────────────────

@router.get("/user/{user_id}")
async def get_reviews_by_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    """Get all reviews written by a specific user."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reviews = (
        db.query(Review)
        .filter(Review.reviewer_id == user_id)
        .order_by(Review.created_at.desc())
        .all()
    )

    return [_build_review_response(r, db) for r in reviews]