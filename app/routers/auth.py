import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import profile_out
from ..media import hash_token
from ..models import Profile
from ..schemas import LoginIn, RegisterOut
from ..security import login_blocked, login_failed, login_ok, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=RegisterOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "?"
    if login_blocked(ip, body.chatid):
        raise HTTPException(429, "Too many attempts. Try again in a few minutes.")

    profile = db.scalar(select(Profile).where(Profile.chatid == body.chatid))
    ok = verify_password(body.password, profile.password_hash if profile else None)
    if not profile or not ok:
        login_failed(ip, body.chatid)
        raise HTTPException(401, "Wrong chat ID or password")

    login_ok(ip, body.chatid)
    # A fresh token per login. (Only one device token is stored, so logging in
    # on a new phone signs the old phone out.)
    token = secrets.token_urlsafe(32)
    profile.token_hash = hash_token(token)
    db.commit()
    return RegisterOut(profile=profile_out(profile, request, include_phone=True), token=token)
