from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import PUBLIC_BASE_URL
from .database import get_db
from .media import hash_token
from .models import Profile
from .schemas import ProfileOut

bearer = HTTPBearer(auto_error=False)


def base_url(request: Request) -> str:
    """Prefer PUBLIC_BASE_URL (https on Render); fall back to the request URL."""
    return PUBLIC_BASE_URL or str(request.base_url).rstrip("/")


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


def profile_out(p: Profile, request: Request, include_phone: bool = False) -> ProfileOut:
    """include_phone=True means "this is the owner's own profile"."""
    url = f"{base_url(request)}/media/{p.photo_filename}" if p.photo_filename else None
    public = p.is_public is not False
    return ProfileOut(
        chatid=p.chatid,
        name=p.name,
        bio=p.bio or "",
        photo_url=url,
        phone=p.phone if include_phone else None,  # never leak other people's numbers
        address=p.address if (include_phone or public) else None,
        is_public=public,
    )
