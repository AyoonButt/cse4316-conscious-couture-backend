# app/api/v1/orders.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.order import (
    OrderResponse,
    BuyerNotificationsResponse,
    BuyerNotificationItem,
    MarkDeliveredRequest,
    MarkDeliveredResponse,
    ReleaseSellerFundsRequest,
    ReleaseSellerFundsResponse,
    MarkShippedRequest,
    MarkShippedResponse,
    CancelOrderRequest,
    CancelOrderResponse,
)
from app.services.order import (
    get_order_by_id,
    get_buyer_notifications,
    mark_order_delivered,
    release_seller_funds,
    mark_order_shipped,
    cancel_order,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    # TODO: Add authentication and verify user has access to this order
):
    """
    Get order details by ID.
    Returns full order information including status and timestamps.
    """
    order = get_order_by_id(db, order_id)
    
    return OrderResponse(
        order_id=order.order_id,
        buyer_user_id=order.buyer_user_id,
        seller_user_id=order.seller_user_id,
        clothing_id=order.clothing_id,
        seller_stripe_account_id=order.seller_stripe_account_id,
        payment_intent_id=order.payment_intent_id,
        transfer_id=order.transfer_id,
        order_status=order.order_status,
        amount_total=order.amount_total,
        seller_net=order.seller_net,
        platform_fee=order.platform_fee,
        currency=order.currency,
        shipping_address=order.shipping_address,
        tracking_number=order.tracking_number,
        shipping_carrier=order.shipping_carrier,
        shipping_label_url=order.shipping_label_url,
        created_at=order.created_at,
        updated_at=order.updated_at,
        payment_succeeded_at=order.payment_succeeded_at,
        shipped_at=order.shipped_at,
        delivery_confirmed_at=order.delivery_confirmed_at,
        completed_at=order.completed_at,
        cancelled_at=order.cancelled_at,
        payout_released_at=order.payout_released_at,
        buyer_notes=order.buyer_notes,
        seller_notes=order.seller_notes,
    )


@router.get("/buyer/{buyer_user_id}/notifications", response_model=BuyerNotificationsResponse)
def get_buyer_notifications_endpoint(
    buyer_user_id: int,
    db: Session = Depends(get_db),
):
    """
    Header dropdown feed for buyer notifications.
    Currently returns shipment notifications with downloadable label URLs.
    """
    notifications = get_buyer_notifications(db, buyer_user_id=buyer_user_id)
    return BuyerNotificationsResponse(
        buyer_user_id=buyer_user_id,
        unread_count=len(notifications),
        notifications=[BuyerNotificationItem(**item) for item in notifications],
    )


@router.post("/{order_id}/mark-shipped", response_model=MarkShippedResponse)
def mark_shipped_endpoint(
    order_id: int,
    payload: MarkShippedRequest,
    seller_user_id: int = Query(..., description="Temporary until JWT auth is wired"),
    db: Session = Depends(get_db),
    # TODO: Add authentication to get seller_user_id
):
    """
    Mark an order as shipped.
    Can only be called by the seller after payment succeeds.
    
    Flow:
    1. Payment succeeds
    2. Seller prepares and ships item
    3. Seller calls this endpoint with tracking info
    4. Order status changes to 'shipped'
    """
    order = mark_order_shipped(
        db,
        order_id=order_id,
        seller_user_id=seller_user_id,
        tracking_number=payload.tracking_number,
        shipping_label_url=payload.shipping_label_url,
        seller_notes=payload.seller_notes,
    )

    return MarkShippedResponse(
        order_id=order.order_id,
        order_status=order.order_status,
        shipped_at=order.shipped_at,
        tracking_number=order.tracking_number,
        shipping_carrier=order.shipping_carrier,
        shipping_label_url=order.shipping_label_url,
        message="Order marked as shipped successfully",
    )


@router.post("/{order_id}/mark-delivered", response_model=MarkDeliveredResponse)
def mark_delivered_endpoint(
    order_id: int,
    payload: MarkDeliveredRequest,
    db: Session = Depends(get_db),
    # TODO: Add authentication to get buyer_user_id
):
    """
    Mark an order as delivered.
    Can only be called by the buyer after shipping.
    
    Flow:
    1. Item ships
    2. Buyer receives item
    3. Buyer confirms delivery via this endpoint
    4. Order status changes to 'delivered'
    5. Ready for seller payout
    """
    # TODO: Get buyer_user_id from authenticated user
    raise HTTPException(
        status_code=501,
        detail="Authentication required. Please add buyer_user_id from JWT token."
    )
    
    # Uncomment when authentication is added:
    # order = mark_order_delivered(
    #     db,
    #     order_id=order_id,
    #     buyer_user_id=buyer_user_id,
    # )
    # 
    # return MarkDeliveredResponse(
    #     order_id=order.order_id,
    #     order_status=order.order_status,
    #     delivery_confirmed_at=order.delivery_confirmed_at,
    #     message="Order marked as delivered successfully. Seller payout can now be processed.",
    # )


@router.post("/{order_id}/release-seller-funds", response_model=ReleaseSellerFundsResponse)
def release_seller_funds_endpoint(
    order_id: int,
    payload: ReleaseSellerFundsRequest,
    db: Session = Depends(get_db),
    # TODO: Add admin authentication or automatic trigger after delivery confirmation
):
    """
    Release funds to seller via Stripe Transfer.
    Should be called after delivery is confirmed.
    
    Flow:
    1. Delivery confirmed
    2. System (or admin) calls this endpoint
    3. Funds transferred to seller's Stripe Connect account
    4. Order status changes to 'completed'
    
    Note: This could be triggered automatically after delivery confirmation
    or after a holding period (e.g., 7 days) for buyer protection.
    """
    order = release_seller_funds(db, order_id=order_id)
    
    return ReleaseSellerFundsResponse(
        order_id=order.order_id,
        transfer_id=order.transfer_id,
        seller_net=order.seller_net,
        payout_released_at=order.payout_released_at,
        message="Seller funds released successfully",
    )


@router.post("/{order_id}/cancel", response_model=CancelOrderResponse)
def cancel_order_endpoint(
    order_id: int,
    payload: CancelOrderRequest,
    db: Session = Depends(get_db),
    # TODO: Add authentication to get user_id
):
    """
    Cancel an order and refund if payment was made.
    Can be called by buyer or seller before delivery.
    
    Flow:
    1. Buyer or seller decides to cancel
    2. Calls this endpoint with reason
    3. If payment was made, automatic refund is issued
    4. Order status changes to 'cancelled'
    5. Item returns to 'available' status
    """
    # TODO: Get user_id from authenticated user
    raise HTTPException(
        status_code=501,
        detail="Authentication required. Please add user_id from JWT token."
    )
    
    # Uncomment when authentication is added:
    # order, refund_id = cancel_order(
    #     db,
    #     order_id=order_id,
    #     user_id=user_id,
    #     cancellation_reason=payload.cancellation_reason,
    # )
    # 
    # message = "Order cancelled successfully"
    # if refund_id:
    #     message += f". Refund issued (ID: {refund_id})"
    # 
    # return CancelOrderResponse(
    #     order_id=order.order_id,
    #     order_status=order.order_status,
    #     cancelled_at=order.cancelled_at,
    #     refund_id=refund_id,
    #     message=message,
    # )
