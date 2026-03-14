from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db

router = APIRouter()


@router.get("/")
async def get_brands(db: Session = Depends(get_db)):
    return {"message": "TODO: implement get all brands"}


@router.get("/{brand_id}")
async def get_brand(brand_id: int, db: Session = Depends(get_db)):
    return {"message": f"TODO: implement get brand {brand_id}"}


@router.post("/")
async def create_brand(db: Session = Depends(get_db)):
    return {"message": "TODO: implement create brand"}


@router.put("/{brand_id}")
async def update_brand(brand_id: int, db: Session = Depends(get_db)):
    return {"message": f"TODO: implement update brand {brand_id}"}


@router.delete("/{brand_id}")
async def delete_brand(brand_id: int, db: Session = Depends(get_db)):
    return {"message": f"TODO: implement delete brand {brand_id}"}