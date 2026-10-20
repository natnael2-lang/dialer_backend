import hmac
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..config import ADMIN_KEY
from ..database import get_db
from ..deps import base_url
from ..models import Call, Contact, Profile

router = APIRouter(prefix="/admin", tags=["admin"])

PAGE = Path(__file__).resolve().parent.parent / "static" / "admin.html"


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    if not x_admin_key or not hmac.compare_digest(x_admin_key, ADMIN_KEY):
        raise HTTPException(401, "Wrong admin key")


@router.get("", include_in_schema=False)
def dashboard():
    # The page itself holds no data; it asks for the key, then calls the API below.
    return FileResponse(PAGE, media_type="text/html", headers={"Cache-Control": "no-store"})


def _daily(db: Session, column, days: int, tz_minutes: int) -> list[dict]:
    """Per-day counts for the last `days` days in the viewer's time zone."""
    now = datetime.now(timezone.utc)
    offset = timedelta(minutes=tz_minutes)
    rows = db.scalars(select(column).where(column >= now - timedelta(days=days + 1))).all()
    counts: Counter = Counter()
    for dt in rows:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        counts[(dt + offset).date()] += 1
    today = (now + offset).date()
    out = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        out.append({"date": d.isoformat(), "count": counts.get(d, 0)})
    return out


def _since(db: Session, column, delta: timedelta) -> int:
    return db.scalar(select(func.count()).where(column >= datetime.now(timezone.utc) - delta)) or 0


@router.get("/api/stats", dependencies=[Depends(require_admin)])
def stats(tz: int = Query(0, ge=-840, le=840), db: Session = Depends(get_db)):
    count = lambda *where: db.scalar(select(func.count(Profile.id)).where(*where)) or 0  # noqa: E731
    users = count()

    def top(group_col, limit=5):
        rows = db.execute(
            select(Profile.chatid, Profile.name, func.count(Call.id).label("n"))
            .join(Call, group_col == Profile.id)
            .group_by(Profile.id)
            .order_by(func.count(Call.id).desc())
            .limit(limit)
        ).all()
        return [{"chatid": r.chatid, "name": r.name, "count": r.n} for r in rows]

    return {
        "totals": {
            "users": users,
            "new_24h": _since(db, Profile.created_at, timedelta(hours=24)),
            "new_7d": _since(db, Profile.created_at, timedelta(days=7)),
            "with_photo": count(Profile.photo_filename.is_not(None)),
            "with_bio": count(func.length(func.trim(Profile.bio)) > 0),
            "with_phone": count(Profile.phone.is_not(None)),
            "contacts": db.scalar(select(func.count(Contact.id))) or 0,
            "calls": db.scalar(select(func.count(Call.id))) or 0,
            "calls_7d": _since(db, Call.created_at, timedelta(days=7)),
        },
        "registrations": _daily(db, Profile.created_at, 30, tz),
        "calls_daily": _daily(db, Call.created_at, 30, tz),
        "most_called": top(Call.target_id),
        "most_active": top(Call.caller_id),
    }


@router.get("/api/users", dependencies=[Depends(require_admin)])
def users(
    request: Request,
    q: str = Query("", max_length=80),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    def n(model, col):
        return (
            select(func.count(model.id)).where(col == Profile.id).correlate(Profile).scalar_subquery()
        )

    stmt = select(
        Profile,
        n(Contact, Contact.owner_id).label("contacts"),
        n(Contact, Contact.target_id).label("saved_by"),
        n(Call, Call.caller_id).label("calls_made"),
        n(Call, Call.target_id).label("calls_received"),
    )
    total_stmt = select(func.count(Profile.id))
    term = q.strip()
    if term:
        like = f"%{term}%"
        cond = or_(Profile.name.ilike(like), Profile.chatid.like(like), Profile.phone.like(like))
        stmt = stmt.where(cond)
        total_stmt = total_stmt.where(cond)

    rows = db.execute(stmt.order_by(Profile.created_at.desc()).limit(limit).offset(offset)).all()
    base = base_url(request)
    return {
        "total": db.scalar(total_stmt) or 0,
        "items": [
            {
                "chatid": p.chatid,
                "name": p.name,
                "bio": p.bio or "",
                "phone": p.phone,
                "photo_url": f"{base}/media/{p.photo_filename}" if p.photo_filename else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "contacts": contacts,
                "saved_by": saved_by,
                "calls_made": calls_made,
                "calls_received": calls_received,
            }
            for p, contacts, saved_by, calls_made, calls_received in rows
        ],
    }
