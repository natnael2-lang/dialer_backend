import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_profile, profile_out
from ..media import delete_photo, hash_token, save_photo
from ..models import Profile
from ..schemas import ProfileOut, ProfileUpdate, RegisterOut

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _new_chatid(db: Session) -> str:
    for _ in range(20):
        candidate = str(secrets.randbelow(9_000_000) + 1_000_000)  # 7 digits
        if not db.scalar(select(Profile.id).where(Profile.chatid == candidate)):
            return candidate
    raise HTTPException(500, "Could not allocate a chat ID, try again")


@router.post("", response_model=RegisterOut, status_code=201)
async def register(
    request: Request,
    name: str = Form(..., min_length=1, max_length=80),
    bio: str = Form("", max_length=280),
    photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    name = " ".join(name.split())
    if not name:
        raise HTTPException(422, "Name is required")

    filename = await save_photo(photo) if photo is not None else None
    token = secrets.token_urlsafe(32)

    for _ in range(3):
        profile = Profile(
            chatid=_new_chatid(db),
            name=name,
            bio=bio.strip(),
            photo_filename=filename,
            token_hash=hash_token(token),
        )
        db.add(profile)
        try:
            db.commit()
            break
        except IntegrityError:  # chatid collision under concurrency
            db.rollback()
    else:
        delete_photo(filename)
        raise HTTPException(500, "Could not register, try again")

    return RegisterOut(profile=profile_out(profile, request), token=token)


@router.get("/me", response_model=ProfileOut)
def me(request: Request, profile: Profile = Depends(current_profile)):
    return profile_out(profile, request)


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
    db.add(profile)
    db.commit()
    return profile_out(profile, request)


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
    return profile_out(profile, request)


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
    return profile_out(profile, request)


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
