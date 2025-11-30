from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db

router = APIRouter()


@router.get("/user/{user_id}")
async def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    return {"message": f"TODO: implement get user {user_id} statistics"}


@router.get("/platform")
async def get_platform_stats(db: Session = Depends(get_db)):
    return {"message": "TODO: implement get platform-wide statistics"}