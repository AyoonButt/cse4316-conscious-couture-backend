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
    shipment_id: Optional[str] = None
    rate_id: Optional[str] = None
    sale_id: Optional[int] = None


class ShippingBuyResponse(BaseModel):
    shipment_id: str
    tracking_number: Optional[str] = None
    label_url: Optional[str] = None
    mock: bool = False
    status: str = "label_ready"
    sale_id: Optional[int] = None


class ShippingConfigResponse(BaseModel):
    mock_rates: bool
    mock_labels: bool
    carrier_id: str
    carrier_name: str


class LabelStatusResponse(BaseModel):
    sale_id: int
    tracking_number: Optional[str] = None
    label_url: Optional[str] = None
    shipping_carrier: Optional[str] = None
    status: str
    mock: bool = False
