from fastapi import APIRouter

from app.schemas.shipping import (
    ShippingBuyRequest,
    ShippingBuyResponse,
    ShippingRatesRequest,
    ShippingRatesResponse,
    AddressVerificationRequest,
    AddressVerificationResponse,
)
from app.services.shipping import (
    buy_shipping_label, 
    create_shipping_rates,
    verify_address,
)


router = APIRouter(tags=["shipping"])


@router.post("/verify-address", response_model=AddressVerificationResponse)
def verify_address_endpoint(payload: AddressVerificationRequest) -> AddressVerificationResponse:
    """Verify and normalize a shipping address."""
    return verify_address(payload)


@router.post("/rates", response_model=ShippingRatesResponse)
def create_shipping_rates_endpoint(payload: ShippingRatesRequest) -> ShippingRatesResponse:
    shipment_id, rates = create_shipping_rates(payload)
    return ShippingRatesResponse(shipment_id=shipment_id, rates=rates)


@router.post("/buy", response_model=ShippingBuyResponse)
def buy_shipping_label_endpoint(payload: ShippingBuyRequest) -> ShippingBuyResponse:
    result = buy_shipping_label(payload)
    return ShippingBuyResponse(**result)
