from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ...database import get_db
from ...models.user import User
from ...schemas.create_user import UserCreate,SignIn
import hashlib
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "secret"
ALGORITHM = "HS256"
security = HTTPBearer()
router = APIRouter()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # verifies the user is logged in, if not, throws error
    print("TOKEN RECEIVED:", token)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("PAYLOAD:", payload)
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="No user id, please log in")
        return user_id

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

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

    token_data = {
        "user_id": make_user.user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=2)
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "message": "Account created successfully",
        # "user": make_user.to_dict()
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": make_user.user_id,
            "email": make_user.email,
            "name": make_user.display_name
        }
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
        user = exist
        token_data = {
            "user_id": user.user_id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=2)
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        print("Logged in from Google")
        return {
            "access_token": token,
            "token_type": "bearer",
            "message": "Login successfully from Google",
            "user": {
                "id": user.user_id,
                "email": user.email,
                "name": user.display_name,
            }
        }
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