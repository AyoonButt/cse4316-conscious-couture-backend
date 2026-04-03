from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from fastapi import HTTPException
from app.config import settings
from app.schemas.shipping import (
    RateResponse, 
    ShippingBuyRequest, 
    ShippingRatesRequest,
    AddressInput,
    AddressVerificationRequest,
    AddressVerificationResponse,
)
from shipengine import ShipEngine

DEFAULT_CARRIER = settings.SHIPPING_DEFAULT_CARRIER
DEFAULT_CARRIER_ID = settings.SHIPPING_DEFAULT_CARRIER_ID
MOCK_UPS_RATES = [
    {"id": "mock-ups-ground", "service": "UPS Ground", "rate": "8.99", "delivery_days": 5},
]


def _get_shipengine_client() -> ShipEngine:
    if not settings.SHIPENGINE_API_KEY:
        raise HTTPException(status_code=500, detail="ShipEngine API key is not configured")
    return ShipEngine(settings.SHIPENGINE_API_KEY)


def _require_api_key() -> None:
    if not settings.SHIPENGINE_API_KEY:
        raise HTTPException(status_code=500, detail="ShipEngine API key is not configured")


def _mock_shipment_id() -> str:
    return f"mock-shipment-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def _build_mock_rates() -> List[RateResponse]:
    return [
        RateResponse(
            id=mock_rate["id"],
            carrier=DEFAULT_CARRIER,
            carrier_id=DEFAULT_CARRIER_ID,
            service=mock_rate["service"],
            rate=mock_rate["rate"],
            currency="USD",
            delivery_days=mock_rate["delivery_days"],
            delivery_date=None,
        )
        for mock_rate in MOCK_UPS_RATES
    ]


def verify_address(address: AddressVerificationRequest) -> AddressVerificationResponse:
    """Verify and normalize a shipping address using ShipEngine."""
    _require_api_key()
    shipengine_client = _get_shipengine_client()

    if (address.country or "US").upper() != "US":
        return AddressVerificationResponse(
            valid=False,
            errors=["Shipping is currently limited to the US"],
        )
    
    try:
        address_dict = {
            "address_line1": address.street1,
            "city_locality": address.city,
            "state_province": address.state,
            "postal_code": address.zip,
            "country_code": address.country,
        }
        
        if address.street2:
            address_dict["address_line2"] = address.street2
        
        # ShipEngine's validate_addresses returns a list of validation results
        results = shipengine_client.validate_addresses([address_dict])
        
        if results and len(results) > 0:
            result = results[0]  # Get first result since we only sent one address
            status = result.get('status', '').lower()
            
            # Check if address was verified or matched
            if status in ['verified', 'valid']:
                matched = result.get('matched_address', {})
                normalized = AddressInput(
                    street1=matched.get('address_line1', address.street1),
                    street2=matched.get('address_line2') or None,
                    city=matched.get('city_locality', address.city),
                    state=matched.get('state_province', address.state),
                    zip=matched.get('postal_code', address.zip),
                    country=matched.get('country_code', address.country),
                )
                return AddressVerificationResponse(valid=True, normalized_address=normalized)
            else:
                # Address could not be verified
                errors = []
                if result.get('messages'):
                    errors = [msg.get('message', str(msg)) for msg in result['messages']]
                if not errors:
                    errors = [f'Address validation status: {status}']
                return AddressVerificationResponse(valid=False, errors=errors)
        else:
            return AddressVerificationResponse(valid=False, errors=['No validation result returned'])
            
    except Exception as exc:
        return AddressVerificationResponse(
            valid=False, 
            errors=[f"Address verification error: {str(exc)}"]
        )


def _rate_to_response(rate: dict) -> RateResponse:
    return RateResponse(
        id=rate.get("id"),
        carrier=DEFAULT_CARRIER,
        carrier_id=DEFAULT_CARRIER_ID,
        service=rate.get("service"),
        rate=rate.get("rate"),
        currency=rate.get("currency"),
        delivery_days=rate.get("delivery_days"),
        delivery_date=rate.get("delivery_date"),
    )


def create_shipping_rates(payload: ShippingRatesRequest) -> Tuple[str, List[RateResponse]]:
    to_country = (payload.to_address.country or "US").upper()
    from_country = (payload.from_address.country or "US").upper()
    if to_country != "US" or from_country != "US":
        raise HTTPException(status_code=400, detail="Shipping is currently limited to the US")

    if settings.MOCK_SHIPPING_RATES:
        return _mock_shipment_id(), _build_mock_rates()

    _require_api_key()
    shipengine_client = _get_shipengine_client()

    try:
        # Get rates from ShipEngine
        rates_result = shipengine_client.get_rates_from_shipment({
            "validate_address": "no_validation",
            "ship_to": {
                "name": payload.to_address.name,
                "phone": payload.to_address.phone,
                "address_line1": payload.to_address.street1,
                "address_line2": payload.to_address.street2,
                "city_locality": payload.to_address.city,
                "state_province": payload.to_address.state,
                "postal_code": payload.to_address.zip,
                "country_code": payload.to_address.country,
            },
            "ship_from": {
                "name": payload.from_address.name,
                "phone": payload.from_address.phone,
                "address_line1": payload.from_address.street1,
                "address_line2": payload.from_address.street2,
                "city_locality": payload.from_address.city,
                "state_province": payload.from_address.state,
                "postal_code": payload.from_address.zip,
                "country_code": payload.from_address.country,
            },
            "packages": [{
                "weight": {
                    "value": payload.parcel.weight,
                    "unit": "pound"
                },
                "dimensions": {
                    "length": payload.parcel.length or 0,
                    "width": payload.parcel.width or 0,
                    "height": payload.parcel.height or 0,
                    "unit": "inch"
                }
            }],
            "rate_options": {
                "carrier_ids": [DEFAULT_CARRIER_ID],
            },
        })
        
        if not rates_result or not rates_result.get('rates'):
            raise HTTPException(status_code=502, detail="No shipping rates available")
        
        all_rates = [
            _rate_to_response(rate)
            for rate in rates_result['rates']
        ]

        rates = all_rates

        # Sort by cheapest rate first
        rates.sort(key=lambda r: float(r.rate) if r.rate else float("inf"))

        shipment_id = rates_result.get('shipment_id', 'unknown')
        return shipment_id, rates[:1]
        
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ShipEngine error: {str(exc)}")


def buy_shipping_label(payload: ShippingBuyRequest) -> Tuple[str, str | None, str | None]:
    if settings.MOCK_SHIPPING_LABELS:
        mock_tracking = f"1ZMOCK{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        mock_label_url = f"https://mock.shipping.local/labels/{payload.shipment_id}.pdf"
        return payload.shipment_id, mock_tracking, mock_label_url

    _require_api_key()
    shipengine_client = _get_shipengine_client()
    if not payload.rate_id:
        raise HTTPException(status_code=400, detail="rate_id is required when mock labels are disabled")

    try:
        # Purchase label using ShipEngine only when mocking is disabled.
        label_result = shipengine_client.create_label_from_rate_id({
            "shipment_id": payload.shipment_id,
            "rate_id": payload.rate_id,
        })
        
        if not label_result:
            raise HTTPException(status_code=502, detail="Failed to purchase shipping label")
        
        tracking_code = label_result.get('tracking_number')
        label_url = label_result.get('label_download', {}).get('href') if label_result.get('label_download') else None
        
        return payload.shipment_id, tracking_code, label_url
        
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ShipEngine error: {str(exc)}")
