from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ...database import get_db
from ...models.user import User
from ...models.statistics import UserImpactStatistics
from ...schemas.create_user import UserCreate,SignIn
import hashlib
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ...models.clothing import ClothingItem
from typing import Optional
from pydantic import BaseModel

SECRET_KEY = "secret"
ALGORITHM = "HS256"
security = HTTPBearer()
router = APIRouter()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="No user id, please log in")
        return user_id

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
@router.get("/{clothing_id}")
def get_name_for_item(clothing_id: int, db: Session = Depends(get_db)):
    clothing_item = db.query(ClothingItem).filter(ClothingItem.clothing_id == clothing_id).first()
    if not clothing_item:
        raise HTTPException(status_code=401, detail="Clothing item not found")
    exist = db.query(User).filter(User.user_id == clothing_item.owner_user_id).first()
    if not exist:
        raise HTTPException(status_code=401, detail="User id not found")
    return {"name": exist.display_name}


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

@router.get("/")
async def get_users(db: Session = Depends(get_db)):
    return {"message": "TODO: implement get all users"}


@router.get("/leaderboard/top-sustainable")
async def get_top_sustainable_users(db: Session = Depends(get_db)):
    results = (
        db.query(User, UserImpactStatistics)
        .outerjoin(UserImpactStatistics, User.user_id == UserImpactStatistics.user_id)
        .filter(User.share_stats == True)
        .order_by(UserImpactStatistics.cumulative_co2_saved_kg.desc().nullslast())
        .limit(20)
        .all()
    )
    
    leaderboard = []
    for user, stats in results:
        leaderboard.append({
            "user_id": user.user_id,
            "username": user.username,
            "display_name": user.display_name,
            "location": user.location,
            "total_swaps": user.total_swaps,
            "impact_points": user.impact_points,
            "cumulative_co2_saved_kg": float(stats.cumulative_co2_saved_kg) if stats and stats.cumulative_co2_saved_kg else 0,
            "cumulative_water_saved_liters": float(stats.cumulative_water_saved_liters) if stats and stats.cumulative_water_saved_liters else 0,
            "cumulative_energy_saved_kwh": float(stats.cumulative_energy_saved_kwh) if stats and stats.cumulative_energy_saved_kwh else 0,
            "equivalent_km_not_driven": float(stats.equivalent_km_not_driven) if stats and stats.equivalent_km_not_driven else 0,
            "equivalent_trees_planted": float(stats.equivalent_trees_planted) if stats and stats.equivalent_trees_planted else 0,
            "impact_rank": stats.impact_rank if stats else None,
            "badges": user.badges or [],
        })
    
    return {"leaderboard": leaderboard}


@router.post("/signin")
async def signin(user_info: SignIn, db: Session = Depends(get_db)):
    email = user_info.email
    hashedpassword= hash_password(user_info.password)
    exist = db.query(User).filter(User.email == email).first()
    if not exist or hashedpassword!=exist.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token_data = {
        "user_id": exist.user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=2)
    }

    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return {
        "access_token": token,
        "token_type": "bearer",
        "message": "Login successfully",
        "user": {
            "id": exist.user_id,
            "email": exist.email,
            "name": exist.display_name,
            "email_notifications": exist.email_notifications,
        }
    }


@router.post("/signup")
async def create_user_signup(user_info: UserCreate,db: Session = Depends(get_db)):
    full_name = user_info.display_name
    email = user_info.email
    hashedpassword= hash_password(user_info.password)
    username = user_info.username or email.split('@')[0]
    exist = db.query(User).filter(User.email == email).first()
    if exist:
        raise HTTPException(
        status_code=400,
        detail="Account already exists, email already registered"
    )
    username_exists = db.query(User).filter(User.username == username).first()
    if username_exists:
        username = f"{username}_{email.split('@')[1].split('.')[0]}"
    make_user = User(
        username=username,
        email= email,
        display_name=full_name,
        password_hash=hashedpassword
    )
    db.add(make_user)
    db.commit()
    db.refresh(make_user)

    token_data = {
        "user_id": make_user.user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=2)
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "message": "Account created successfully",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": make_user.user_id,
            "email": make_user.email,
            "name": make_user.display_name,
            "email_notifications": make_user.email_notifications,
        }
    }


@router.post("/google")
async def create_user_google(payload: dict = Body(...), db : Session = Depends(get_db)):
    goog_email = payload.get("email")
    goog_name = payload.get("name")
    # see if the user is already created
    exist = db.query(User).filter(User.email == goog_email).first()
    if exist:
        user = exist
        token_data = {
            "user_id": user.user_id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=2)
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        return {
            "access_token": token,
            "token_type": "bearer",
            "message": "Login successfully from Google",
            "user": {
                "id": user.user_id,
                "email": user.email,
                "name": user.display_name,
                "email_notifications": user.email_notifications,
            }
        }

    # ── NEW Google user ──
    username = goog_email.split('@')[0]
    username_exists = db.query(User).filter(User.username == username).first()
    if username_exists:
        username = f"{username}_{goog_email.split('@')[1].split('.')[0]}"
    make_user = User(
        username=username,
        email= goog_email,
        display_name=goog_name,
        password_hash="",
    )
    db.add(make_user)
    db.commit()
    db.refresh(make_user)

    # ── FIX: Generate JWT token for new Google users too ──
    token_data = {
        "user_id": make_user.user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=2)
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": token,
        "token_type": "bearer",
        "message": "Account created from Google",
        "user": {
            "id": make_user.user_id,
            "email": make_user.email,
            "name": make_user.display_name,
            "email_notifications": make_user.email_notifications,
        }
    }


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user),
    payload: dict = Body(...),
):
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Cannot update another user's profile")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    allowed = {'display_name', 'email_notifications', 'location', 'bio', 'share_stats'}
    for field, value in payload.items():
        if field in allowed:
            setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return {
        "id": user.user_id,
        "email": user.email,
        "name": user.display_name,
        "email_notifications": user.email_notifications,
    }


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/{user_id}/password")
async def change_password(
    user_id: int,
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user),
):
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Cannot change another user's password")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.password_hash != hash_password(payload.current_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    return {"message": f"TODO: implement delete user {user_id}"}