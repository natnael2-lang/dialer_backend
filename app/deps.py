from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .media import hash_token
from .models import Profile
from .schemas import ProfileOut

bearer = HTTPBearer(auto_error=False)


def current_profile(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Profile:
    if creds is None:
        raise HTTPException(401, "Missing token")
    profile = db.scalar(select(Profile).where(Profile.token_hash == hash_token(creds.credentials)))
    if profile is None:
        raise HTTPException(401, "Invalid token")
    return profile


def profile_out(p: Profile, request: Request) -> ProfileOut:
    url = None
    if p.photo_filename:
        url = f"{str(request.base_url).rstrip('/')}/media/{p.photo_filename}"
    return ProfileOut(chatid=p.chatid, name=p.name, bio=p.bio or "", photo_url=url)
