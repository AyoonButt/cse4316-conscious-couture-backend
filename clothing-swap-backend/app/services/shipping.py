from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict, Any
from fastapi import HTTPException
import requests
from app.config import settings
from app.schemas.shipping import (
    RateResponse, 
    ShippingBuyRequest, 
    ShippingRatesRequest,
    AddressInput,
    AddressVerificationRequest,
    AddressVerificationResponse,
)
from app.database import SessionLocal
from app.models.sale import Sale
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


def _format_shipengine_exception(exc: Exception) -> str:
    details: List[str] = []

    message = str(exc).strip()
    if message:
        details.append(message)

    response = getattr(exc, "response", None)
    if response is not None:
        try:
            response_json = response.json()
            details.append(str(response_json))
        except Exception:
            response_text = getattr(response, "text", None)
            if response_text:
                details.append(str(response_text)[:800])

    exception_repr = repr(exc)
    if exception_repr and exception_repr not in details:
        details.append(exception_repr)

    typed_prefix = type(exc).__name__
    if not details:
        return typed_prefix

    return f"{typed_prefix}: {' | '.join(details)}"


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
    shipping_amount = rate.get("shipping_amount") or {}
    shipping_value = shipping_amount.get("amount", rate.get("rate"))
    delivery_date = rate.get("estimated_delivery_date", rate.get("delivery_date"))
    return RateResponse(
        id=rate.get("rate_id") or rate.get("id"),
        carrier=DEFAULT_CARRIER,
        carrier_id=rate.get("carrier_id") or DEFAULT_CARRIER_ID,
        service=rate.get("service_type") or rate.get("service"),
        rate=str(shipping_value),
        currency=(shipping_amount.get("currency") or rate.get("currency") or "USD").upper(),
        delivery_days=rate.get("delivery_days"),
        delivery_date=delivery_date,
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
    to_phone = payload.to_address.phone or "5555555555"
    from_phone = payload.from_address.phone or "5555555555"

    try:
        package_payload = {
            "weight": {
                # Frontend parcel weights are sent in ounces.
                "value": payload.parcel.weight,
                "unit": "ounce",
            }
        }

        has_dimensions = all(
            value is not None and value > 0
            for value in [payload.parcel.length, payload.parcel.width, payload.parcel.height]
        )
        if has_dimensions:
            package_payload["dimensions"] = {
                "length": payload.parcel.length,
                "width": payload.parcel.width,
                "height": payload.parcel.height,
                "unit": "inch",
            }

        # Use ShipEngine REST rates endpoint directly for consistent test-mode behavior.
        response = requests.post(
            "https://api.shipengine.com/v1/rates",
            headers={
                "API-Key": settings.SHIPENGINE_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "rate_options": {
                    "carrier_ids": [DEFAULT_CARRIER_ID],
                },
                "shipment": {
                    "validate_address": "no_validation",
                    "ship_to": {
                        "name": payload.to_address.name,
                        "phone": to_phone,
                        "address_line1": payload.to_address.street1,
                        "address_line2": payload.to_address.street2,
                        "city_locality": payload.to_address.city,
                        "state_province": payload.to_address.state,
                        "postal_code": payload.to_address.zip,
                        "country_code": payload.to_address.country,
                    },
                    "ship_from": {
                        "name": payload.from_address.name,
                        "phone": from_phone,
                        "address_line1": payload.from_address.street1,
                        "address_line2": payload.from_address.street2,
                        "city_locality": payload.from_address.city,
                        "state_province": payload.from_address.state,
                        "postal_code": payload.from_address.zip,
                        "country_code": payload.from_address.country,
                    },
                    "packages": [package_payload],
                },
            },
            timeout=30,
        )

        rates_result = response.json()
        if not response.ok:
            api_errors = rates_result.get("errors") if isinstance(rates_result, dict) else None
            if api_errors and isinstance(api_errors, list):
                first_message = api_errors[0].get("message") or str(api_errors[0])
                raise HTTPException(status_code=502, detail=f"ShipEngine error: {first_message}")
            raise HTTPException(status_code=502, detail="ShipEngine error: Failed to fetch rates")

        rate_response = rates_result.get("rate_response") if isinstance(rates_result, dict) else None
        if not rate_response:
            raise HTTPException(status_code=502, detail="ShipEngine error: Missing rate_response payload")

        raw_rates = rate_response.get("rates") or []
        if not raw_rates:
            errors = rate_response.get("errors") or []
            if errors and isinstance(errors, list):
                first_message = errors[0].get("message") or str(errors[0])
                raise HTTPException(status_code=502, detail=f"No shipping rates available: {first_message}")
            raise HTTPException(status_code=502, detail="No shipping rates available")

        all_rates = [_rate_to_response(rate) for rate in raw_rates]

        # Sort by cheapest rate first
        rates = sorted(all_rates, key=lambda r: float(r.rate) if r.rate else float("inf"))

        shipment_id = rate_response.get("shipment_id") or _mock_shipment_id()
        return shipment_id, rates

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ShipEngine error: {_format_shipengine_exception(exc)}")


def buy_shipping_label(payload: ShippingBuyRequest) -> Dict[str, Any]:
    """Purchase a shipping label (mock or real) and persist tracking info to the sale record."""
    is_mock = settings.MOCK_SHIPPING_LABELS
    tracking_number: Optional[str] = None
    label_url: Optional[str] = None
    status = "label_ready"

    # Generate a fallback shipment_id when not provided (mock mode)
    effective_shipment_id = payload.shipment_id or f"mock-shipment-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    if not is_mock and not payload.shipment_id:
        raise HTTPException(status_code=400, detail="shipment_id is required when mock labels are disabled")

    if is_mock:
        tracking_number = f"1ZMOCK{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        label_url = f"https://mock.shipping.local/labels/{effective_shipment_id}.pdf"
    else:
        _require_api_key()
        shipengine_client = _get_shipengine_client()
        if not payload.rate_id:
            raise HTTPException(status_code=400, detail="rate_id is required when mock labels are disabled")

        try:
            label_result = shipengine_client.create_label_from_rate_id(
                payload.rate_id,
                {
                    "label_format": "pdf",
                },
            )

            if not label_result:
                raise HTTPException(status_code=502, detail="Failed to purchase shipping label — empty response from ShipEngine")

            # ShipEngine may return error info inside the dict
            if label_result.get('errors'):
                error_msgs = '; '.join(e.get('message', str(e)) for e in label_result['errors'])
                raise HTTPException(status_code=502, detail=f"ShipEngine label error: {error_msgs}")

            tracking_number = label_result.get('tracking_number')
            label_url = (
                label_result.get('label_download', {}).get('href')
                if label_result.get('label_download')
                else None
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"ShipEngine error: {type(exc).__name__}: {str(exc)}")

    # Persist tracking info to the Sale record when sale_id is provided
    if payload.sale_id:
        try:
            db = SessionLocal()
            sale = db.query(Sale).filter(Sale.sale_id == payload.sale_id).first()
            if sale:
                sale.tracking_number = tracking_number
                sale.status = "shipped" if tracking_number else sale.status
                sale.shipped_date = datetime.now(timezone.utc) if tracking_number else sale.shipped_date
                db.commit()
            db.close()
        except Exception:
            pass  # label was already purchased; DB save is best-effort

    return {
        "shipment_id": effective_shipment_id,
        "tracking_number": tracking_number,
        "label_url": label_url,
        "mock": is_mock,
        "status": status,
        "sale_id": payload.sale_id,
    }


def get_label_status(sale_id: int) -> Dict[str, Any]:
    """Return the current shipping label status for a given sale."""
    db = SessionLocal()
    try:
        sale = db.query(Sale).filter(Sale.sale_id == sale_id).first()
        if not sale:
            raise HTTPException(status_code=404, detail="Sale not found")
        # Map Sale.status to a label-focused status for the frontend
        sale_status = sale.status or "pending"
        if sale_status == "shipped" and sale.tracking_number:
            label_status = "label_ready"
        elif sale_status in ("delivered", "completed"):
            label_status = "label_ready"
        else:
            label_status = "pending"

        return {
            "sale_id": sale.sale_id,
            "tracking_number": sale.tracking_number,
            "label_url": None,  # not persisted on Sale model
            "shipping_carrier": DEFAULT_CARRIER,
            "status": label_status,
            "mock": settings.MOCK_SHIPPING_LABELS,
        }
    finally:
        db.close()
