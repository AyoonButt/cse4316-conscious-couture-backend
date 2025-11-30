from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db

router = APIRouter()


@router.get("/")
async def get_materials(db: Session = Depends(get_db)):
    return {"message": "TODO: implement get all materials"}


@router.get("/{material_name}")
async def get_material(material_name: str, db: Session = Depends(get_db)):
    return {"message": f"TODO: implement get material {material_name}"}