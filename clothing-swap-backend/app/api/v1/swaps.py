from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db

router = APIRouter()


@router.get("/")
async def get_swaps(db: Session = Depends(get_db)):
    return {"message": "TODO: implement get all swaps"}


@router.get("/{swap_id}")
async def get_swap(swap_id: int, db: Session = Depends(get_db)):
    return {"message": f"TODO: implement get swap {swap_id}"}


@router.post("/")
async def create_swap(db: Session = Depends(get_db)):
    return {"message": "TODO: implement create swap"}


@router.put("/{swap_id}")
async def update_swap(swap_id: int, db: Session = Depends(get_db)):
    return {"message": f"TODO: implement update swap {swap_id}"}


@router.delete("/{swap_id}")
async def delete_swap(swap_id: int, db: Session = Depends(get_db)):
    return {"message": f"TODO: implement delete swap {swap_id}"}