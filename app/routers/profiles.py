import re
import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_profile, profile_out
from ..media import delete_photo, hash_token, save_photo
from ..models import Profile
from ..phone import phone_key
from ..schemas import ProfileOut, ProfileUpdate, RegisterOut
from ..security import hash_password

router = APIRouter(prefix="/profiles", tags=["profiles"])

CHATID_RE = re.compile(r"^\d{4,16}$")


def _check_phone(db: Session, phone: str, owner_id: int | None = None) -> str:
    key = phone_key(phone)
    if key is None:
        raise HTTPException(422, "Enter a valid phone number")
    other = db.scalar(select(Profile).where(Profile.phone_key == key))
    if other is not None and other.id != owner_id:
        raise HTTPException(409, "That phone number is already registered")
    return key


@router.post("", response_model=RegisterOut, status_code=201)
async def register(
    request: Request,
    chatid: str = Form(..., max_length=16),
    name: str = Form(..., min_length=1, max_length=80),
    password: str = Form(..., min_length=6, max_length=64),
    bio: str = Form("", max_length=280),
    phone: str = Form("", max_length=24),
    address: str = Form("", max_length=160),
    is_public: bool = Form(True),
    photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    name = " ".join(name.split())
    if not name:
        raise HTTPException(422, "Name is required")
    chatid = chatid.strip()
    if not CHATID_RE.match(chatid):
        raise HTTPException(422, "Chat ID must be 4 to 16 digits")
    if db.scalar(select(Profile.id).where(Profile.chatid == chatid)):
        raise HTTPException(409, "That chat ID is already taken, choose another")

    phone = phone.strip()
    key = _check_phone(db, phone) if phone else None

    filename = await save_photo(photo) if photo is not None else None
    token = secrets.token_urlsafe(32)

    profile = Profile(
        chatid=chatid,
        name=name,
        bio=bio.strip(),
        address=" ".join(address.split()) or None,
        is_public=is_public,
        photo_filename=filename,
        phone=phone or None,
        phone_key=key,
        password_hash=hash_password(password),
        token_hash=hash_token(token),
    )
    db.add(profile)
    try:
        db.commit()
    except IntegrityError:  # someone took the chat ID a moment ago
        db.rollback()
        delete_photo(filename)
        raise HTTPException(409, "That chat ID is already taken, choose another")

    return RegisterOut(profile=profile_out(profile, request, include_phone=True), token=token)


@router.get("/me", response_model=ProfileOut)
def me(request: Request, profile: Profile = Depends(current_profile)):
    return profile_out(profile, request, include_phone=True)


@router.patch("/me", response_model=ProfileOut)
def update_me(
    body: ProfileUpdate,
    request: Request,
    profile: Profile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    if body.name is not None:
        profile.name = body.name
    if body.bio is not None:
        profile.bio = body.bio.strip()
    if body.address is not None:
        profile.address = " ".join(body.address.split()) or None
    if body.is_public is not None:
        profile.is_public = body.is_public
    if body.password is not None:
        profile.password_hash = hash_password(body.password)
    if body.phone is not None:
        phone = body.phone.strip()
        if phone:
            profile.phone_key = _check_phone(db, phone, owner_id=profile.id)
            profile.phone = phone
        else:
            profile.phone = None
            profile.phone_key = None
    db.add(profile)
    db.commit()
    return profile_out(profile, request, include_phone=True)


@router.put("/me/photo", response_model=ProfileOut)
async def change_photo(
    request: Request,
    photo: UploadFile = File(...),
    profile: Profile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    new_name = await save_photo(photo)
    old = profile.photo_filename
    profile.photo_filename = new_name  # new filename each time => no stale caches
    db.add(profile)
    db.commit()
    delete_photo(old)
    return profile_out(profile, request, include_phone=True)


@router.delete("/me/photo", response_model=ProfileOut)
def remove_photo(
    request: Request,
    profile: Profile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    old = profile.photo_filename
    profile.photo_filename = None
    db.add(profile)
    db.commit()
    delete_photo(old)
    return profile_out(profile, request, include_phone=True)


@router.get("/check/{chatid}")
def check_chatid(chatid: str, db: Session = Depends(get_db)):
    """No login needed: is this chat ID free? Used by the register screen."""
    chatid = chatid.strip()
    if not CHATID_RE.match(chatid):
        raise HTTPException(422, "Chat ID must be 4 to 16 digits")
    taken = db.scalar(select(Profile.id).where(Profile.chatid == chatid)) is not None
    return {"available": not taken}


def _like_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("/search", response_model=list[ProfileOut])
def search(
    request: Request,
    q: str = Query(..., min_length=2, max_length=80),
    me: Profile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    """Name search over public profiles only (English or Amharic)."""
    term = " ".join(q.split())
    if len(term) < 2:
        return []
    rows = db.scalars(
        select(Profile)
        .where(
            Profile.is_public.is_(True),
            Profile.id != me.id,
            Profile.name.ilike(f"%{_like_escape(term)}%", escape="\\"),
        )
        .order_by(Profile.name)
        .limit(30)
    ).all()
    return [profile_out(p, request) for p in rows]


@router.get("/lookup/{chatid}", response_model=ProfileOut)
def lookup(
    chatid: str,
    request: Request,
    _: Profile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    target = db.scalar(select(Profile).where(Profile.chatid == chatid.strip()))
    if target is None:
        raise HTTPException(404, "No profile is registered with that chat ID")
    return profile_out(target, request)
