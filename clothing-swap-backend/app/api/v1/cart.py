from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
from decimal import Decimal
from datetime import datetime

from ...database import get_db
from ...models.cart import CartItem
from ...models.clothing import ClothingItem
from ...models.sale import Sale
from ...models.user import User
from ...schemas.cart import (
    CartAddRequest,
    CartItemResponse,
    CartResponse,
    CartValidationResponse,
    CartValidationItem,
    CheckoutResponse,
    CheckoutItemResult,
    PurchaseCompleteRequest,
)
from ...services.payment import create_payment
from .users import get_current_user

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────

def _build_cart_item_response(cart_item: CartItem) -> CartItemResponse:
    """Convert a CartItem + its related ClothingItem into a response."""
    ci = cart_item.clothing
    return CartItemResponse(
        cart_item_id=cart_item.cart_item_id,
        clothing_id=ci.clothing_id,
        name=ci.description or f"{ci.clothing_type} by {ci.brand or 'Unknown'}",
        owner_name=(ci.owner.display_name or ci.owner.username) if ci.owner else None,
        size=ci.size,
        price=float(ci.sell_price) if ci.sell_price else 0,
        brand=ci.brand,
        image=ci.primary_image_url,
        clothing_type=ci.clothing_type,
        condition=ci.condition,
        available=(ci.status == "available"),
        added_at=cart_item.added_at,
    )


# ── GET  /cart/ ──────────────────────────────────────────────────────────

@router.get("/", response_model=CartResponse)
def get_cart(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Return the authenticated user's cart with full item details."""
    cart_items = (
        db.query(CartItem)
        .filter(CartItem.user_id == user_id)
        .order_by(CartItem.added_at.desc())
        .all()
    )

    items = [_build_cart_item_response(ci) for ci in cart_items]
    total = sum(i.price for i in items)

    return CartResponse(items=items, count=len(items), total=round(total, 2))


# ── POST /cart/add ───────────────────────────────────────────────────────

@router.post("/add", response_model=CartItemResponse)
def add_to_cart(
    payload: CartAddRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Add a clothing item to the user's cart."""

    # 1) Item must exist
    clothing = (
        db.query(ClothingItem)
        .filter(ClothingItem.clothing_id == payload.clothing_id)
        .first()
    )
    if not clothing:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    # 2) Item must be available
    if clothing.status != "available":
        raise HTTPException(
            status_code=400,
            detail=f"Item is no longer available (status: {clothing.status})",
        )

    # 3) Cannot add your own item
    if clothing.owner_user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot add your own item to cart")

    # 4) Must have a sell price
    if not clothing.sell_price or float(clothing.sell_price) <= 0:
        raise HTTPException(status_code=400, detail="Item is not listed for sale")

    # 5) Insert (unique constraint handles duplicates)
    cart_item = CartItem(user_id=user_id, clothing_id=payload.clothing_id)
    try:
        db.add(cart_item)
        db.commit()
        db.refresh(cart_item)
    except IntegrityError:
        db.rollback()
        # Already in cart — just return existing entry
        cart_item = (
            db.query(CartItem)
            .filter(
                CartItem.user_id == user_id,
                CartItem.clothing_id == payload.clothing_id,
            )
            .first()
        )

    return _build_cart_item_response(cart_item)


# ── DELETE /cart/{clothing_id} ───────────────────────────────────────────

@router.delete("/{clothing_id}")
def remove_from_cart(
    clothing_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Remove a specific item from the user's cart."""
    deleted = (
        db.query(CartItem)
        .filter(CartItem.user_id == user_id, CartItem.clothing_id == clothing_id)
        .delete()
    )
    db.commit()

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Item not in cart")

    return {"message": "Removed from cart"}


# ── DELETE /cart/clear ───────────────────────────────────────────────────

@router.delete("/clear")
def clear_cart(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Remove all items from the user's cart."""
    count = db.query(CartItem).filter(CartItem.user_id == user_id).delete()
    db.commit()
    return {"message": f"Cart cleared ({count} items removed)"}


# ── POST /cart/validate ──────────────────────────────────────────────────

@router.post("/validate", response_model=CartValidationResponse)
def validate_cart(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """
    Re-check every cart item is still available.
    Call this when the user opens the checkout page.
    """
    cart_items = (
        db.query(CartItem)
        .filter(CartItem.user_id == user_id)
        .all()
    )

    results: List[CartValidationItem] = []
    unavailable = 0

    for ci in cart_items:
        clothing = ci.clothing
        is_available = clothing.status == "available"
        reason = None if is_available else f"Item status is '{clothing.status}'"

        if not is_available:
            unavailable += 1

        results.append(
            CartValidationItem(
                clothing_id=clothing.clothing_id,
                name=clothing.description or clothing.clothing_type,
                available=is_available,
                reason=reason,
            )
        )

    return CartValidationResponse(
        valid=(unavailable == 0),
        items=results,
        unavailable_count=unavailable,
    )


# ── POST /cart/checkout ──────────────────────────────────────────────────

@router.post("/checkout", response_model=CheckoutResponse)
def checkout_cart(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """
    Initiates purchase for all items in the cart:
    1. Validates all items are still available
    2. Creates a Sale record per item
    3. Creates a Stripe PaymentIntent per Sale
    4. Returns client_secrets for frontend to confirm payment

    All-or-nothing: if any item is unavailable, the whole checkout fails.
    """

    cart_items = (
        db.query(CartItem)
        .filter(CartItem.user_id == user_id)
        .all()
    )

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # ── validate all items ──
    for ci in cart_items:
        clothing = ci.clothing
        if clothing.status != "available":
            raise HTTPException(
                status_code=409,
                detail=f"'{clothing.description or clothing.clothing_type}' is no longer available. Please remove it from your cart.",
            )
        if clothing.owner_user_id == user_id:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot purchase your own item (ID {clothing.clothing_id})",
            )

    # ── create sales + payments ──
    checkout_results: List[CheckoutItemResult] = []
    total = Decimal("0")

    for ci in cart_items:
        clothing = ci.clothing
        price = Decimal(str(clothing.sell_price)) if clothing.sell_price else Decimal("0")

        if price <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Item '{clothing.description}' has no valid price",
            )

        # Create Sale record
        sale = Sale(
            seller_id=clothing.owner_user_id,
            buyer_id=user_id,
            clothing_id=clothing.clothing_id,
            sale_price=price,
            original_price=price,
            currency="USD",
            status="pending",
        )
        db.add(sale)
        db.flush()  # Get sale_id without committing

        # Create Stripe PaymentIntent via existing service
        payment, client_secret = create_payment(
            db,
            sale_id=sale.sale_id,
            amount=price,
            currency="usd",
        )

        total += price

        checkout_results.append(
            CheckoutItemResult(
                clothing_id=clothing.clothing_id,
                sale_id=sale.sale_id,
                payment_id=payment.id,
                client_secret=client_secret,
                amount=str(price),
                status=payment.status,
            )
        )

    db.commit()

    return CheckoutResponse(
        items=checkout_results,
        total_amount=str(total),
    )


# ── POST /cart/complete ──────────────────────────────────────────────────

@router.post("/complete")
def complete_purchase(
    payload: PurchaseCompleteRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """
    Called after Stripe confirms payment succeeded.
    For each sale_id:
      1. Mark Sale as payment_received
      2. Mark ClothingItem as sold
      3. Remove item from ALL users' carts (not just the buyer)
      4. Update buyer/seller stats
    """
    completed_items = []

    for sale_id in payload.sale_ids:
        sale = db.query(Sale).filter(Sale.sale_id == sale_id).first()
        if not sale:
            continue  # Skip invalid IDs gracefully
        if sale.buyer_id != user_id:
            continue  # Only the buyer can complete their own purchase

        # Update sale status
        if sale.status == "pending":
            sale.status = "payment_received"
            sale.payment_date = datetime.utcnow()

        # Mark clothing item as sold
        clothing = sale.clothing
        if clothing and clothing.status == "available":
            clothing.status = "sold"

        # Remove this item from ALL users' carts
        db.query(CartItem).filter(
            CartItem.clothing_id == sale.clothing_id
        ).delete()

        # Update user stats
        buyer = db.query(User).filter(User.user_id == sale.buyer_id).first()
        seller = db.query(User).filter(User.user_id == sale.seller_id).first()

        if buyer:
            buyer.total_purchases = (buyer.total_purchases or 0) + 1
        if seller:
            seller.total_sales = (seller.total_sales or 0) + 1

        completed_items.append(sale.clothing_id)

    db.commit()

    return {
        "message": f"Purchase completed for {len(completed_items)} item(s)",
        "completed_clothing_ids": completed_items,
    }