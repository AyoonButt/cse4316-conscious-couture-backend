from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from ...database import get_db
from ...models.sale import Sale
from ...models.clothing import ClothingItem
from ...models.user import User
from ...schemas.sale import (
    SaleCreate,
    SaleUpdate,
    SaleStatusUpdate,
    SaleCancelRequest,
    SaleResponse,
    SaleList,
)

router = APIRouter()


@router.get("/", response_model=SaleList)
async def get_sales(
    seller_id: Optional[int] = None,
    buyer_id: Optional[int] = None,
    clothing_id: Optional[int] = None,
    status: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all sales with optional filters"""
    query = db.query(Sale)

    if seller_id:
        query = query.filter(Sale.seller_id == seller_id)
    if buyer_id:
        query = query.filter(Sale.buyer_id == buyer_id)
    if clothing_id:
        query = query.filter(Sale.clothing_id == clothing_id)
    if status:
        query = query.filter(Sale.status == status)
    if min_price is not None:
        query = query.filter(Sale.sale_price >= min_price)
    if max_price is not None:
        query = query.filter(Sale.sale_price <= max_price)

    total = query.count()
    total_pages = (total + per_page - 1) // per_page

    sales = query.order_by(Sale.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return SaleList(
        items=[SaleResponse.model_validate(sale) for sale in sales],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(sale_id: int, db: Session = Depends(get_db)):
    """Get sale details by ID"""
    sale = db.query(Sale).filter(Sale.sale_id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return SaleResponse.model_validate(sale)


@router.post("/", response_model=SaleResponse)
async def create_sale(sale_data: SaleCreate, db: Session = Depends(get_db)):
    """Create a new sale (buyer initiates purchase)"""
    # Validate seller exists
    seller = db.query(User).filter(User.user_id == sale_data.seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")

    # Validate buyer exists
    buyer = db.query(User).filter(User.user_id == sale_data.buyer_id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")

    # Validate clothing item exists and belongs to seller
    clothing = db.query(ClothingItem).filter(ClothingItem.clothing_id == sale_data.clothing_id).first()
    if not clothing:
        raise HTTPException(status_code=404, detail="Clothing item not found")
    if clothing.owner_user_id != sale_data.seller_id:
        raise HTTPException(status_code=400, detail="Clothing item does not belong to seller")
    if clothing.status != 'available':
        raise HTTPException(status_code=400, detail="Clothing item is not available for sale")

    # Validate seller and buyer are different
    if sale_data.seller_id == sale_data.buyer_id:
        raise HTTPException(status_code=400, detail="Seller and buyer cannot be the same user")

    # Create the sale
    sale = Sale(
        seller_id=sale_data.seller_id,
        buyer_id=sale_data.buyer_id,
        clothing_id=sale_data.clothing_id,
        sale_price=sale_data.sale_price,
        original_price=float(clothing.sell_price) if clothing.sell_price else None,
        shipping_address=sale_data.shipping_address,
        buyer_notes=sale_data.buyer_notes,
        status='pending'
    )

    # Mark clothing as pending sale
    clothing.status = 'pending_sale'

    db.add(sale)
    db.commit()
    db.refresh(sale)

    return SaleResponse.model_validate(sale)


@router.put("/{sale_id}", response_model=SaleResponse)
async def update_sale(sale_id: int, sale_data: SaleUpdate, db: Session = Depends(get_db)):
    """Update sale details"""
    sale = db.query(Sale).filter(Sale.sale_id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    update_data = sale_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sale, field, value)

    db.commit()
    db.refresh(sale)

    return SaleResponse.model_validate(sale)


@router.post("/{sale_id}/status", response_model=SaleResponse)
async def update_sale_status(sale_id: int, status_update: SaleStatusUpdate, db: Session = Depends(get_db)):
    """Update sale status"""
    sale = db.query(Sale).filter(Sale.sale_id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    valid_statuses = ['pending', 'payment_received', 'shipped', 'delivered', 'completed', 'cancelled', 'refunded']
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    from datetime import datetime
    from sqlalchemy.sql import func

    # Update status and related timestamps
    old_status = sale.status
    sale.status = status_update.status

    if status_update.status == 'payment_received' and not sale.payment_date:
        sale.payment_date = datetime.utcnow()
    elif status_update.status == 'shipped' and not sale.shipped_date:
        sale.shipped_date = datetime.utcnow()
    elif status_update.status == 'completed':
        sale.completed_date = datetime.utcnow().date()
        # Transfer ownership and update user stats
        if sale.clothing:
            sale.clothing.owner_user_id = sale.buyer_id
            sale.clothing.status = 'sold'
        # Update seller and buyer stats
        seller = db.query(User).filter(User.user_id == sale.seller_id).first()
        buyer = db.query(User).filter(User.user_id == sale.buyer_id).first()
        if seller:
            seller.total_sales = (seller.total_sales or 0) + 1
        if buyer:
            buyer.total_purchases = (buyer.total_purchases or 0) + 1
    elif status_update.status == 'cancelled':
        sale.cancelled_date = datetime.utcnow()
        # Restore item availability
        if sale.clothing:
            sale.clothing.status = 'available'

    db.commit()
    db.refresh(sale)

    return SaleResponse.model_validate(sale)


@router.post("/{sale_id}/cancel", response_model=SaleResponse)
async def cancel_sale(sale_id: int, cancel_request: SaleCancelRequest, db: Session = Depends(get_db)):
    """Cancel a sale"""
    sale = db.query(Sale).filter(Sale.sale_id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    if sale.status in ['completed', 'cancelled', 'refunded']:
        raise HTTPException(status_code=400, detail=f"Cannot cancel a sale with status '{sale.status}'")

    from datetime import datetime

    sale.status = 'cancelled'
    sale.cancelled_date = datetime.utcnow()
    sale.cancellation_reason = cancel_request.reason

    # Restore item availability
    if sale.clothing:
        sale.clothing.status = 'available'

    db.commit()
    db.refresh(sale)

    return SaleResponse.model_validate(sale)


@router.get("/user/{user_id}/as-seller", response_model=SaleList)
async def get_user_sales_as_seller(
    user_id: int,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get sales where user is the seller"""
    query = db.query(Sale).filter(Sale.seller_id == user_id)

    if status:
        query = query.filter(Sale.status == status)

    total = query.count()
    total_pages = (total + per_page - 1) // per_page

    sales = query.order_by(Sale.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return SaleList(
        items=[SaleResponse.model_validate(sale) for sale in sales],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/user/{user_id}/as-buyer", response_model=SaleList)
async def get_user_sales_as_buyer(
    user_id: int,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get sales where user is the buyer"""
    query = db.query(Sale).filter(Sale.buyer_id == user_id)

    if status:
        query = query.filter(Sale.status == status)

    total = query.count()
    total_pages = (total + per_page - 1) // per_page

    sales = query.order_by(Sale.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return SaleList(
        items=[SaleResponse.model_validate(sale) for sale in sales],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )
