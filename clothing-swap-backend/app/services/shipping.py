from __future__ import annotations
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

# Initialize ShipEngine client
shipengine_client = ShipEngine(settings.SHIPENGINE_API_KEY)


def _require_api_key() -> None:
    if not settings.SHIPENGINE_API_KEY:
        raise HTTPException(status_code=500, detail="ShipEngine API key is not configured")


def verify_address(address: AddressVerificationRequest) -> AddressVerificationResponse:
    """Verify and normalize a shipping address using ShipEngine."""
    _require_api_key()
    
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
        carrier=rate.get("carrier"),
        service=rate.get("service"),
        rate=rate.get("rate"),
        currency=rate.get("currency"),
        delivery_days=rate.get("delivery_days"),
        delivery_date=rate.get("delivery_date"),
    )


def create_shipping_rates(payload: ShippingRatesRequest) -> Tuple[str, List[RateResponse]]:
    _require_api_key()

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
            }]
        })
        
        if not rates_result or not rates_result.get('rates'):
            raise HTTPException(status_code=502, detail="No shipping rates available")
        
        rates = [
            _rate_to_response(rate)
            for rate in rates_result['rates']
        ]
        
        shipment_id = rates_result.get('shipment_id', 'unknown')
        return shipment_id, rates
        
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ShipEngine error: {str(exc)}")


def buy_shipping_label(payload: ShippingBuyRequest) -> Tuple[str, str | None, str | None]:
    _require_api_key()

    try:
        # Purchase label using ShipEngine
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
