from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os
from ..schemas.create_user import UserCreate
from ..api.v1.users import create_user_google
from ..database import get_db

GOOGLE_CLIENT_ID = os.getenv("830347299700-s47i9sicfvfh7ph3b5q9kunbk02dhldm.apps.googleusercontent.com")  # your Google client ID

router = APIRouter()

async def verify(token: str):
    try:
        # Verify token signature, expiration, and audience
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        return idinfo
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

@router.post("/google")
async def google_login(req: Request,db : Session = Depends(get_db)): #handles http interaction from frontend
    body = await req.json()
    # print("BODY RECEIVED:", body)

    token = body.get("idToken")
    if not token:
        raise HTTPException(status_code=400, detail="No ID token provided")

    payload = await verify(token)
    print("Google Id token verified:", payload)
    make_user = await create_user_google(payload,db)
    return make_user