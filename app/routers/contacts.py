from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_profile, profile_out
from ..models import Contact, Profile
from ..schemas import ContactCreate, ContactOut, ContactUpdate

router = APIRouter(prefix="/contacts", tags=["contacts"])


def _out(c: Contact, request: Request) -> ContactOut:
    return ContactOut(id=c.id, nickname=c.nickname, profile=profile_out(c.target, request))


@router.get("", response_model=list[ContactOut])
def list_contacts(
    request: Request,
    me: Profile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(Contact).where(Contact.owner_id == me.id).order_by(Contact.nickname)
    ).unique()
    return [_out(c, request) for c in rows]


@router.post("", response_model=ContactOut, status_code=201)
def add_contact(
    body: ContactCreate,
    request: Request,
    me: Profile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    target = db.scalar(select(Profile).where(Profile.chatid == body.chatid))
    if target is None:
        raise HTTPException(404, "No profile is registered with that chat ID")
    if target.id == me.id:
        raise HTTPException(400, "That's your own chat ID")
    exists = db.scalar(
        select(Contact.id).where(Contact.owner_id == me.id, Contact.target_id == target.id)
    )
    if exists:
        raise HTTPException(409, "You already saved this person")

    nickname = " ".join((body.nickname or target.name).split()) or target.name
    contact = Contact(owner_id=me.id, target_id=target.id, nickname=nickname)
    contact.target = target
    db.add(contact)
    db.commit()
    return _out(contact, request)


@router.patch("/{contact_id}", response_model=ContactOut)
def rename_contact(
    contact_id: int,
    body: ContactUpdate,
    request: Request,
    me: Profile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    contact = db.scalar(select(Contact).where(Contact.id == contact_id, Contact.owner_id == me.id))
    if contact is None:
        raise HTTPException(404, "Contact not found")
    contact.nickname = body.nickname
    db.commit()
    return _out(contact, request)


@router.delete("/{contact_id}", status_code=204)
def delete_contact(
    contact_id: int,
    me: Profile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    contact = db.scalar(select(Contact).where(Contact.id == contact_id, Contact.owner_id == me.id))
    if contact is None:
        raise HTTPException(404, "Contact not found")
    db.delete(contact)
    db.commit()
    return Response(status_code=204)
