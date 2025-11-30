from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db

router = APIRouter()


@router.post("/register")
async def register(db: Session = Depends(get_db)):
    return {"message": "TODO: implement user registration"}


@router.post("/login")
async def login(db: Session = Depends(get_db)):
    return {"message": "TODO: implement user login"}


@router.post("/refresh")
async def refresh_token(db: Session = Depends(get_db)):
    return {"message": "TODO: implement token refresh"}