from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy import or_, and_

from ...database import get_db
from ...models.swap import Swap
from ...models.clothing import ClothingItem
from ...models.user import User
from .users import get_current_user
from ...services.email import (
    send_swap_request_email,
    send_swap_accepted_email,
    send_swap_declined_email,
    send_swap_cancelled_email,
)
from ...models.notification import Notification

router = APIRouter()


def _notify(db: Session, user_id: int, ntype: str, title: str, message: str, swap_id: int = None):
    """Persist a notification record for a user."""
    notif = Notification(user_id=user_id, type=ntype, title=title, message=message, swap_id=swap_id)
    db.add(notif)
    # caller is responsible for db.commit()


# ── Schemas ──────────────────────────────────────────────────────────────

class SwapCreateRequest(BaseModel):
    """Request to initiate a swap. The requester offers their item for the target item."""
    my_clothing_id: int = Field(..., description="ID of the item the requester is offering (must own)")
    target_clothing_id: int = Field(..., description="ID of the item the requester wants")
    message: Optional[str] = Field(None, description="Optional message to the other user")


class SwapActionRequest(BaseModel):
    """Accept or reject a swap request."""
    action: str = Field(..., description="'accept' or 'reject'")


class SwapItemDetail(BaseModel):
    clothing_id: int
    name: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None
    brand: Optional[str] = None
    image: Optional[str] = None
    owner_user_id: int
    owner_name: Optional[str] = None

    class Config:
        from_attributes = True


class SwapResponse(BaseModel):
    swap_id: int
    status: str
    swap_type: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_date: Optional[str] = None

    user1_id: int
    user2_id: int
    user1_name: Optional[str] = None
    user2_name: Optional[str] = None

    user1_item: Optional[SwapItemDetail] = None
    user2_item: Optional[SwapItemDetail] = None

    class Config:
        from_attributes = True


# ── Helpers ──────────────────────────────────────────────────────────────

def _build_item_detail(clothing: ClothingItem, db: Session) -> SwapItemDetail:
    owner = db.query(User).filter(User.user_id == clothing.owner_user_id).first()
    return SwapItemDetail(
        clothing_id=clothing.clothing_id,
        name=clothing.description or f"{clothing.clothing_type} by {clothing.brand or 'Unknown'}",
        size=clothing.size,
        condition=clothing.condition,
        brand=clothing.brand,
        image=clothing.primary_image_url,
        owner_user_id=clothing.owner_user_id,
        owner_name=owner.display_name if owner else None,
    )


def _build_swap_response(swap: Swap, db: Session) -> SwapResponse:
    user1 = db.query(User).filter(User.user_id == swap.user1_id).first()
    user2 = db.query(User).filter(User.user_id == swap.user2_id).first()
    item1 = db.query(ClothingItem).filter(ClothingItem.clothing_id == swap.user1_clothing_id).first()
    item2 = db.query(ClothingItem).filter(ClothingItem.clothing_id == swap.user2_clothing_id).first()

    return SwapResponse(
        swap_id=swap.swap_id,
        status=swap.status,
        swap_type=swap.swap_type or "direct",
        created_at=swap.created_at,
        updated_at=swap.updated_at,
        completed_date=swap.completed_date.isoformat() if swap.completed_date else None,
        user1_id=swap.user1_id,
        user2_id=swap.user2_id,
        user1_name=user1.display_name if user1 else None,
        user2_name=user2.display_name if user2 else None,
        user1_item=_build_item_detail(item1, db) if item1 else None,
        user2_item=_build_item_detail(item2, db) if item2 else None,
    )


# ── GET /swaps/ ──────────────────────────────────────────────────────────

@router.get("/")
def get_my_swaps(
    status: Optional[str] = Query(None, description="Filter by status: pending, accepted, completed, rejected, cancelled"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Get all swaps involving the current user."""
    query = db.query(Swap).filter(
        (Swap.user1_id == user_id) | (Swap.user2_id == user_id)
    )

    if status:
        query = query.filter(Swap.status == status)

    swaps = query.order_by(Swap.created_at.desc()).all()
    return [_build_swap_response(s, db) for s in swaps]


# ── GET /swaps/{swap_id} ────────────────────────────────────────────────

@router.get("/{swap_id}")
def get_swap(
    swap_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Get a specific swap. Must be a participant."""
    swap = db.query(Swap).filter(Swap.swap_id == swap_id).first()
    if not swap:
        raise HTTPException(status_code=404, detail="Swap not found")

    if swap.user1_id != user_id and swap.user2_id != user_id:
        raise HTTPException(status_code=403, detail="You are not a participant in this swap")

    return _build_swap_response(swap, db)


# ── POST /swaps/ ─────────────────────────────────────────────────────────

@router.post("/")
def create_swap(
    payload: SwapCreateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):

    """
    Create a swap request.

    Ownership rules enforced:
    1. Requester must own my_clothing_id
    2. Requester must NOT own target_clothing_id
    3. Both items must be different
    4. Both items must be available
    5. The two items cannot belong to the same person
    """

    # ── 1. Items must be different ──
    if payload.my_clothing_id == payload.target_clothing_id:
        raise HTTPException(status_code=400, detail="Cannot swap an item with itself")

    # ── 2. Fetch both items ──
    my_item = db.query(ClothingItem).filter(
        ClothingItem.clothing_id == payload.my_clothing_id
    ).first()
    if not my_item:
        raise HTTPException(status_code=404, detail="Your item not found")

    target_item = db.query(ClothingItem).filter(
        ClothingItem.clothing_id == payload.target_clothing_id
    ).first()
    if not target_item:
        raise HTTPException(status_code=404, detail="Target item not found")

    # ── 3. Requester must own their offered item ──
    if my_item.owner_user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only offer items you own"
        )

    # ── 4. Requester must NOT own the target item ──
    if target_item.owner_user_id == user_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot request a swap for your own item"
        )

    # ── 5. Both items must be available ──
    if my_item.status != "available":
        raise HTTPException(
            status_code=400,
            detail=f"Your item is not available (status: {my_item.status})"
        )
    if target_item.status != "available":
        raise HTTPException(
            status_code=400,
            detail=f"Target item is not available (status: {target_item.status})"
        )

    # ── 6. Check for duplicate pending swap ── in both directions
    existing = db.query(Swap).filter(or_(and_(
        Swap.user1_clothing_id == payload.my_clothing_id,
        Swap.user2_clothing_id == payload.target_clothing_id,
        ),
        and_(
        Swap.user1_clothing_id == payload.target_clothing_id,
        Swap.user2_clothing_id == payload.my_clothing_id,
        )
        ),
        Swap.status == "pending",
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="You already have a pending swap request for these items"
        )

    # ── 7. Create swap record ──
    swap = Swap(
        user1_id=user_id,
        user2_id=target_item.owner_user_id,
        user1_clothing_id=payload.my_clothing_id,
        user2_clothing_id=payload.target_clothing_id,
        swap_type="direct",
        status="pending",
    )

    db.add(swap)

    # DB notification for User B (item owner — they have a new incoming request)
    item_label = target_item.description or target_item.clothing_type
    requester_temp = db.query(User).filter(User.user_id == user_id).first()
    _notify(db, target_item.owner_user_id, 'swap_received',
            'New Swap Request',
            f"{requester_temp.display_name if requester_temp else 'Someone'} wants to swap for your item \"{item_label}\".",
            swap_id=None)  # swap_id set after commit below

    db.commit()
    db.refresh(swap)

    # Back-fill swap_id now that we have it
    last_notif = db.query(Notification).filter(
        Notification.user_id == target_item.owner_user_id,
        Notification.type == 'swap_received',
        Notification.swap_id == None,
    ).order_by(Notification.notification_id.desc()).first()
    if last_notif:
        last_notif.swap_id = swap.swap_id
        db.commit()

    # Email the target user (User B) that they have a new swap request
    target_user = db.query(User).filter(User.user_id == target_item.owner_user_id).first()
    requester = db.query(User).filter(User.user_id == user_id).first()
    if target_user and (target_user.email_notifications if hasattr(target_user, 'email_notifications') else True):
        send_swap_request_email(
            to_email=target_user.email,
            requester_name=requester.display_name if requester else 'Someone',
            item_name=target_item.description or f'{target_item.clothing_type}',
        )

    return _build_swap_response(swap, db)


# ── PUT /swaps/{swap_id} ────────────────────────────────────────────────

@router.put("/{swap_id}")
def respond_to_swap(
    swap_id: int,
    payload: SwapActionRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """
    Accept or reject a swap request.

    Only the target user (user2 — the owner of the requested item) can accept/reject.
    """
    swap = db.query(Swap).filter(Swap.swap_id == swap_id).first()
    if not swap:
        raise HTTPException(status_code=404, detail="Swap not found")

    if swap.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Swap is no longer pending (status: {swap.status})"
        )

    # Only user2 (the one who received the request) can accept/reject
    if swap.user2_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the item owner can accept or reject this swap request"
        )

    if payload.action == "reject":
        swap.status = "rejected"

        # DB notification for User A (requester) — their request was declined
        declined_item_pre = db.query(ClothingItem).filter(ClothingItem.clothing_id == swap.user2_clothing_id).first()
        _notify(db, swap.user1_id, 'swap_declined',
                'Swap Request Declined',
                f'Your swap request for "{declined_item_pre.description if declined_item_pre else "the item"}" was declined.',
                swap_id=swap.swap_id)

        db.commit()
        db.refresh(swap)

        # Email User A (requester) that their request was declined
        requester = db.query(User).filter(User.user_id == swap.user1_id).first()
        declined_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == swap.user2_clothing_id).first()
        if requester and getattr(requester, 'email_notifications', True):
            send_swap_declined_email(
                to_email=requester.email,
                item_name=declined_item.description if declined_item else 'the item',
            )

        return _build_swap_response(swap, db)

    if payload.action == "accept":
        # Re-verify both items are still available
        item1 = db.query(ClothingItem).filter(
            ClothingItem.clothing_id == swap.user1_clothing_id
        ).first()
        item2 = db.query(ClothingItem).filter(
            ClothingItem.clothing_id == swap.user2_clothing_id
        ).first()

        if not item1 or item1.status != "available":
            swap.status = "cancelled"
            db.commit()
            raise HTTPException(
                status_code=409,
                detail="The requester's item is no longer available"
            )
        if not item2 or item2.status != "available":
            swap.status = "cancelled"
            db.commit()
            raise HTTPException(
                status_code=409,
                detail="Your item is no longer available"
            )

        # Re-verify ownership hasn't changed
        if item1.owner_user_id != swap.user1_id:
            swap.status = "cancelled"
            db.commit()
            raise HTTPException(status_code=409, detail="Item ownership has changed")
        if item2.owner_user_id != swap.user2_id:
            swap.status = "cancelled"
            db.commit()
            raise HTTPException(status_code=409, detail="Item ownership has changed")

        # Complete the swap — transfer ownership
        swap.status = "completed"
        swap.completed_date = datetime.utcnow().date()

        # Swap ownership
        item1.owner_user_id = swap.user2_id
        item2.owner_user_id = swap.user1_id

        # Update counters
        item1.times_swapped = (item1.times_swapped or 0) + 1
        item2.times_swapped = (item2.times_swapped or 0) + 1

        # Mark items as swapped — removes them from browse/category listings
        item1.status = "swapped"
        item1.available = False
        item2.status = "swapped"
        item2.available = False

        # Update user swap counts
        user1 = db.query(User).filter(User.user_id == swap.user1_id).first()
        user2 = db.query(User).filter(User.user_id == swap.user2_id).first()
        if user1:
            user1.total_swaps = (user1.total_swaps or 0) + 1
        if user2:
            user2.total_swaps = (user2.total_swaps or 0) + 1

        db.commit()
        db.refresh(swap)

        # DB notification for User A (requester) — swap was accepted
        _notify(db, swap.user1_id, 'swap_accepted',
                'Swap Accepted!',
                f'Your swap request for "{item2.description if item2 else "the item"}" was accepted. The items have been exchanged.',
                swap_id=swap.swap_id)
        db.commit()

        # Email User A (requester) that their swap was accepted
        if user1 and getattr(user1, 'email_notifications', True):
            send_swap_accepted_email(
                to_email=user1.email,
                owner_name=user2.display_name if user2 else 'The owner',
                item_name=item2.description if item2 else 'the item',
            )

        return _build_swap_response(swap, db)

    raise HTTPException(status_code=400, detail="Action must be 'accept' or 'reject'")


# ── DELETE /swaps/{swap_id} ──────────────────────────────────────────────

@router.delete("/{swap_id}")
def cancel_swap(
    swap_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """
    Cancel a pending swap request.
    Only the requester (user1) can cancel their own request.
    """
    swap = db.query(Swap).filter(Swap.swap_id == swap_id).first()
    if not swap:
        raise HTTPException(status_code=404, detail="Swap not found")

    if swap.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Can only cancel pending swaps (current status: {swap.status})"
        )

    if swap.user1_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the requester can cancel a swap request"
        )

    swap.status = "cancelled"

    # DB notification for User B (item owner) — request was cancelled
    cancelled_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == swap.user2_clothing_id).first()
    requester_name_q = db.query(User).filter(User.user_id == swap.user1_id).first()
    _notify(db, swap.user2_id, 'swap_cancelled',
            'Swap Request Cancelled',
            f'{requester_name_q.display_name if requester_name_q else "Someone"} cancelled their request for your item "{cancelled_item.description if cancelled_item else "your item"}".',
            swap_id=swap.swap_id)

    db.commit()

    # Email User B (item owner) that the request was cancelled
    target_user = db.query(User).filter(User.user_id == swap.user2_id).first()
    requester = db.query(User).filter(User.user_id == swap.user1_id).first()
    target_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == swap.user2_clothing_id).first()
    if target_user and getattr(target_user, 'email_notifications', True):
        send_swap_cancelled_email(
            to_email=target_user.email,
            requester_name=requester.display_name if requester else 'Someone',
            item_name=target_item.description if target_item else 'your item',
        )

    return {"message": "Swap request cancelled"}