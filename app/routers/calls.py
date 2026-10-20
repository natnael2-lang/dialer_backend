from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_profile
from ..models import Call, Profile
from ..schemas import CallCreate

router = APIRouter(prefix="/calls", tags=["calls"])


@router.post("", status_code=201)
def log_call(
    body: CallCreate,
    me: Profile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    """The app reports each call it places, so the dashboard can chart them."""
    target = db.scalar(select(Profile).where(Profile.chatid == body.chatid))
    if target is None:
        raise HTTPException(404, "No profile with that chat ID")
    db.add(Call(caller_id=me.id, target_id=target.id))
    db.commit()
    return {"ok": True}
