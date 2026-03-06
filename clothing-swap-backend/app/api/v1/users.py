from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ...database import get_db
from ...models.user import User
from ...schemas.create_user import UserCreate,SignIn
import hashlib

router = APIRouter()

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

@router.get("/")
async def get_users(db: Session = Depends(get_db)):
    return {"message": "TODO: implement get all users"}


@router.post("/signin")
async def signin(user_info: SignIn, db: Session = Depends(get_db)):
    email = user_info.email
    hashedpassword= hash_password(user_info.password)
    exist = db.query(User).filter(User.email == email).first()
    if not exist or hashedpassword!=exist.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "message": "Login successfully",
        "user": {
            "id": exist.user_id,
            "email": exist.email,
            "name": exist.display_name,
        }
    }


@router.post("/signup")
async def create_user_signup(user_info: UserCreate,db: Session = Depends(get_db)):
    full_name = user_info.display_name
    email = user_info.email
    hashedpassword= hash_password(user_info.password)
    exist = db.query(User).filter(User.email == email).first()
    if exist:
        raise HTTPException(
        status_code=400,
        detail="Account already exists, email already registered"
    )
    make_user = User(
        email= email,
        display_name=full_name,
        password_hash=hashedpassword
    )
    db.add(make_user)
    db.commit()
    db.refresh(make_user)
    return {
        "message": "Account created successfully",
        "user": make_user.to_dict()
    }


@router.post("/google")
# async def create_user(db: Session = Depends(get_db)):
    # return {"message": "TODO: implement create user"}
async def create_user_google(payload: dict = Body(...), db : Session = Depends(get_db)):
    goog_email = payload.get("email")
    goog_name = payload.get("name")
    # see if the user is already created
    exist = db.query(User).filter(User.email == goog_email).first()
    if exist:
        print("Already exists")
        return exist.to_dict()
    # print("TYPE OF PASSWORD:", type(user.password))
    # print("PASSWORD VALUE:", user.password)
    # print("PASSWORD LENGTH:", len(user.password))
    make_user = User(
        email= goog_email,
        display_name=goog_name,
    )
    db.add(make_user)
    db.commit()
    db.refresh(make_user)
    return {
        "message": "Account created from google",
        "user": make_user.to_dict()
    }


@router.put("/{user_id}")
async def update_user(user_id: int, db: Session = Depends(get_db)):
    return {"message": f"TODO: implement update user {user_id}"}


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    return {"message": f"TODO: implement delete user {user_id}"}