from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db

router = APIRouter()


@router.get("/")
async def get_users(db: Session = Depends(get_db)):
    return {"message": "TODO: implement get all users"}


@router.get("/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    return {"message": f"TODO: implement get user {user_id}"}


@router.post("/")
async def create_user(db: Session = Depends(get_db)):
    return {"message": "TODO: implement create user"}


@router.put("/{user_id}")
async def update_user(user_id: int, db: Session = Depends(get_db)):
    return {"message": f"TODO: implement update user {user_id}"}


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    return {"message": f"TODO: implement delete user {user_id}"}