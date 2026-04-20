# app/api/v1/stripe_connect.py
"""
Stripe Connect endpoints for seller onboarding, account management,
and Express dashboard access.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

import stripe

from app.config import settings
from app.database import get_db
from app.models.user import User
from .users import get_current_user

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/stripe-connect", tags=["stripe-connect"])


# ── Schemas ──────────────────────────────────────────────────────────────

class OnboardingRequest(BaseModel):
    refresh_url: str = Field(..., description="URL Stripe redirects to if the link expires")
    return_url: str = Field(..., description="URL Stripe redirects to after onboarding")


class OnboardingResponse(BaseModel):
    account_id: str
    onboarding_url: str


class AccountStatusResponse(BaseModel):
    stripe_account_id: Optional[str]
    charges_enabled: bool = False
    payouts_enabled: bool = False
    details_submitted: bool = False
    onboarding_complete: bool = False


class DashboardLinkResponse(BaseModel):
    url: str


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/onboarding", response_model=OnboardingResponse)
def create_onboarding_link(
    payload: OnboardingRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """
    Create or reuse a Stripe Express connected account for the seller,
    then return an Account Link URL for onboarding.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    account_id = user.stripe_account_id

    # Create a new Express account if the user doesn't have one
    if not account_id:
        try:
            account = stripe.Account.create(
                type="express",
                email=user.email,
                metadata={"platform_user_id": str(user.user_id)},
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
            )
            account_id = account.id
            user.stripe_account_id = account_id
            db.add(user)
            db.commit()
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Stripe account creation failed: {getattr(e, 'user_message', str(e))}",
            )

    # Generate an Account Link for onboarding / re-onboarding
    try:
        link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=payload.refresh_url,
            return_url=payload.return_url,
            type="account_onboarding",
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Stripe onboarding link failed: {getattr(e, 'user_message', str(e))}",
        )

    return OnboardingResponse(account_id=account_id, onboarding_url=link.url)


@router.get("/account-status", response_model=AccountStatusResponse)
def get_account_status(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """
    Check the seller's Stripe Connect account status.
    Returns whether onboarding is complete and payouts are enabled.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.stripe_account_id:
        return AccountStatusResponse(stripe_account_id=None)

    try:
        account = stripe.Account.retrieve(user.stripe_account_id)
    except stripe.error.StripeError:
        return AccountStatusResponse(stripe_account_id=user.stripe_account_id)

    return AccountStatusResponse(
        stripe_account_id=account.id,
        charges_enabled=account.charges_enabled,
        payouts_enabled=account.payouts_enabled,
        details_submitted=account.details_submitted,
        onboarding_complete=account.charges_enabled and account.payouts_enabled,
    )


@router.post("/dashboard-link", response_model=DashboardLinkResponse)
def create_dashboard_link(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """
    Generate a Stripe Express Dashboard login link.
    Sellers use this to view analytics, payments, balances, disputes, etc.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.stripe_account_id:
        raise HTTPException(
            status_code=400,
            detail="No Stripe account found. Please complete seller onboarding first.",
        )

    try:
        login_link = stripe.Account.create_login_link(user.stripe_account_id)
    except stripe.error.InvalidRequestError as e:
        # Account may not have completed onboarding yet
        raise HTTPException(
            status_code=400,
            detail="Stripe account onboarding is not complete. Please finish onboarding first.",
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Stripe error: {getattr(e, 'user_message', str(e))}",
        )

    return DashboardLinkResponse(url=login_link.url)


@router.get("/seller-orders")
def get_seller_orders(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by order status"),
):
    """
    Get all orders where the current user is the seller.
    Used by the seller dashboard to view incoming orders.
    """
    from app.models.order import Order

    query = db.query(Order).filter(Order.seller_user_id == user_id)
    if status:
        query = query.filter(Order.order_status == status)

    orders = query.order_by(Order.created_at.desc()).limit(50).all()
    return {"orders": [o.to_dict() for o in orders]}


@router.get("/seller-balance")
def get_seller_balance(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """
    Get the seller's pending and available balance from their orders.
    """
    from app.models.order import Order
    from sqlalchemy import func
    from decimal import Decimal

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Pending: delivered but not yet paid out
    pending = (
        db.query(func.coalesce(func.sum(Order.seller_net), 0))
        .filter(
            Order.seller_user_id == user_id,
            Order.order_status == "delivered",
            Order.transfer_id.is_(None),
        )
        .scalar()
    )

    # Paid out: completed with transfer
    paid_out = (
        db.query(func.coalesce(func.sum(Order.seller_net), 0))
        .filter(
            Order.seller_user_id == user_id,
            Order.order_status == "completed",
            Order.transfer_id.isnot(None),
        )
        .scalar()
    )

    # In transit: payment succeeded, awaiting delivery
    in_transit = (
        db.query(func.coalesce(func.sum(Order.seller_net), 0))
        .filter(
            Order.seller_user_id == user_id,
            Order.order_status.in_(["payment_succeeded", "shipped"]),
        )
        .scalar()
    )

    return {
        "pending_payout": float(pending or 0),
        "total_paid_out": float(paid_out or 0),
        "in_transit": float(in_transit or 0),
        "stripe_account_id": user.stripe_account_id,
    }
