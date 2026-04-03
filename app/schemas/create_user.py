from pydantic import BaseModel, EmailStr, Field
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
    # location: Optional[str] = None
# hash password
