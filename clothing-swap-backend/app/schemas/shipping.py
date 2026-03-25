from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AddressInput(BaseModel):
    street1: str
    city: str
    state: str
    zip: str
    country: str = "US"
    name: Optional[str] = None
    street2: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class AddressVerificationRequest(BaseModel):
    street1: str
    city: str
    state: str
    zip: str
    country: str = "US"
    street2: Optional[str] = None


class AddressVerificationResponse(BaseModel):
    valid: bool
    normalized_address: Optional[AddressInput] = None
    errors: Optional[List[str]] = None


class ParcelInput(BaseModel):
    weight: float
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class ShippingRatesRequest(BaseModel):
    from_address: AddressInput
    to_address: AddressInput
    parcel: ParcelInput


class RateResponse(BaseModel):
    id: str
    carrier: str
    carrier_id: str
    service: str
    rate: str
    currency: Optional[str] = None
    delivery_days: Optional[int] = None
    delivery_date: Optional[str] = None


class ShippingRatesResponse(BaseModel):
    shipment_id: str
    rates: List[RateResponse]


class ShippingBuyRequest(BaseModel):
    shipment_id: str
    rate_id: Optional[str] = None


class ShippingBuyResponse(BaseModel):
    shipment_id: str
    tracking_code: Optional[str] = None
    label_url: Optional[str] = None
