from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db

router = APIRouter()


@router.post("/calculate")
async def calculate_impact(db: Session = Depends(get_db)):
    return {"message": "TODO: implement environmental impact calculation"}