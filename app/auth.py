import os

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import Artist, ArtistList, ListArtist, ListMember, User

# For local dev without the oauth2-proxy in front. In production this is unset and
# the X-Forwarded-Email header (set by oauth2-proxy) is required.
DEV_USER_EMAIL = os.getenv("DEV_USER_EMAIL")


def _seed_default_list(db: Session, user: User) -> None:
    lst = ArtistList(owner_id=user.id, name="My artists", is_default=True)
    db.add(lst)
    db.flush()
    db.add(ListMember(list_id=lst.id, user_id=user.id, role="owner"))
    # Legacy adoption: the very first user inherits the old single global list —
    # every catalog artist joins their default list so nothing they tracked is lost.
    if db.query(User).count() == 1:
        for artist in db.query(Artist).all():
            db.add(ListArtist(list_id=lst.id, artist_id=artist.id))
    db.commit()


def current_user(
    x_forwarded_email: str | None = Header(default=None),
    x_forwarded_user: str | None = Header(default=None),
    x_auth_request_email: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Identify the caller from the header oauth2-proxy sets on the upstream request.
    The app is only reachable through the proxy (internal network, `expose` only),
    so this header is trustworthy."""
    email = (x_forwarded_email or x_auth_request_email or DEV_USER_EMAIL or "").strip().lower()
    if not email:
        raise HTTPException(401, "Not authenticated")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email, name=x_forwarded_user)
        db.add(user)
        db.commit()
        db.refresh(user)
        _seed_default_list(db, user)
    return user


# ── Permissions ─────────────────────────────────────────────────────────────
def role_of(db: Session, user: User, lst: ArtistList) -> str | None:
    if lst.owner_id == user.id:
        return "owner"
    m = (
        db.query(ListMember)
        .filter(ListMember.list_id == lst.id, ListMember.user_id == user.id)
        .first()
    )
    return m.role if m else None


def _load(db: Session, list_id: int) -> ArtistList:
    lst = db.get(ArtistList, list_id)
    if not lst:
        raise HTTPException(404, "List not found")
    return lst


def require_view(db: Session, user: User, list_id: int) -> ArtistList:
    lst = _load(db, list_id)
    if role_of(db, user, lst) is None:
        raise HTTPException(403, "You don't have access to this list")
    return lst


def require_edit(db: Session, user: User, list_id: int) -> ArtistList:
    lst = _load(db, list_id)
    if role_of(db, user, lst) not in ("owner", "editor"):
        raise HTTPException(403, "You can't edit this list")
    return lst


def require_owner(db: Session, user: User, list_id: int) -> ArtistList:
    lst = _load(db, list_id)
    if role_of(db, user, lst) != "owner":
        raise HTTPException(403, "Only the owner can do that")
    return lst
