import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import APP_KEY
from ..database import get_db
from ..deps import profile_out
from ..models import Profile
from ..phone import phone_key
from ..schemas import ProfileOut

router = APIRouter(prefix="/callers", tags=["callers"])


@router.get("/lookup", response_model=ProfileOut)
def lookup_caller(
    request: Request,
    number: str = Query(..., min_length=3, max_length=32),
    x_app_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Who owns this phone number? Used by the app when a call comes in.
    Protected by a shared app key so numbers can't be probed from outside."""
    if not x_app_key or not hmac.compare_digest(x_app_key, APP_KEY):
        raise HTTPException(401, "Invalid app key")
    key = phone_key(number)
    if key is None:
        raise HTTPException(404, "Unknown number")
    p = db.scalar(select(Profile).where(Profile.phone_key == key))
    if p is None:
        raise HTTPException(404, "Unknown number")
    return profile_out(p, request)
