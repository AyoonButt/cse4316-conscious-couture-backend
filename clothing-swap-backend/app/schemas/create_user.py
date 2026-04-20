from datetime import date
import re
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional
from passlib.context import CryptContext

# pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")

# pydantic schema to validate input data
# def hash_password(password):
    # return pwd_context.hash(password)
class SignIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=5,max_length=72)
class UserCreate(BaseModel):
    username : Optional[str] = None
    email: EmailStr
    password: str = Field(min_length=5,max_length=72)
    display_name: str
    birth_date: Optional[date] = None
    address_line1: Optional[str] = Field(default=None, min_length=3, max_length=255)
    address_line2: Optional[str] = Field(default=None, max_length=255)
    phone_number: Optional[str] = Field(default=None, min_length=10, max_length=20)
    city: Optional[str] = Field(default=None, min_length=2, max_length=100)
    state: Optional[str] = Field(default=None, min_length=2, max_length=2)
    postal_code: Optional[str] = Field(default=None, min_length=5, max_length=10)
    country: Optional[str] = Field(default='US', min_length=2, max_length=2)

    @field_validator('country')
    @classmethod
    def validate_country(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.upper()
        if normalized != 'US':
            raise ValueError('Only US addresses are supported')
        return normalized

    @field_validator('state')
    @classmethod
    def validate_state(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.upper()
        if not re.fullmatch(r'[A-Z]{2}', normalized):
            raise ValueError('State must be a 2-letter US state code')
        return normalized

    @field_validator('postal_code')
    @classmethod
    def validate_postal_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not re.fullmatch(r'\d{5}(?:-\d{4})?', cleaned):
            raise ValueError('Postal code must be US ZIP format (12345 or 12345-6789)')
        return cleaned

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        digits = re.sub(r'\D', '', value)
        if len(digits) == 11 and digits.startswith('1'):
            digits = digits[1:]

        if len(digits) != 10:
            raise ValueError('Phone number must be a valid US number')

        return f'+1{digits}'

    @field_validator('birth_date')
    @classmethod
    def validate_birth_date(cls, value: Optional[date]) -> Optional[date]:
        if value is None:
            return value
        if value >= date.today():
            raise ValueError('Birth date must be in the past')
        return value

    @model_validator(mode='after')
    def validate_full_address_if_provided(self):
        fields = [self.address_line1, self.city, self.state, self.postal_code, self.country]
        provided = [f for f in fields if f]
        if provided and len(provided) != len(fields):
            raise ValueError('Provide full US address: address_line1, city, state, postal_code, country')
        return self
# hash password
