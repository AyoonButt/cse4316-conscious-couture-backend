from fastapi import APIRouter

from app.config import settings
from app.schemas.shipping import (
    ShippingBuyRequest,
    ShippingBuyResponse,
    ShippingRatesRequest,
    ShippingRatesResponse,
    ShippingConfigResponse,
    LabelStatusResponse,
    AddressVerificationRequest,
    AddressVerificationResponse,
)
from app.services.shipping import (
    buy_shipping_label, 
    create_shipping_rates,
    get_label_status,
    verify_address,
)


router = APIRouter(tags=["shipping"])


@router.get("/config", response_model=ShippingConfigResponse)
def get_shipping_config() -> ShippingConfigResponse:
    """Return the current shipping configuration flags (single source of truth)."""
    return ShippingConfigResponse(
        mock_rates=settings.MOCK_SHIPPING_RATES,
        mock_labels=settings.MOCK_SHIPPING_LABELS,
        carrier_id=settings.SHIPPING_DEFAULT_CARRIER_ID,
        carrier_name=settings.SHIPPING_DEFAULT_CARRIER,
    )


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


@router.get("/label-status/{sale_id}", response_model=LabelStatusResponse)
def get_label_status_endpoint(sale_id: int) -> LabelStatusResponse:
    """Get current shipping label / tracking status for a sale."""
    result = get_label_status(sale_id)
    return LabelStatusResponse(**result)
