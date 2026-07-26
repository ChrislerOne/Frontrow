import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import current_user, require_edit, require_owner, require_view, role_of
from .database import Base, engine, get_db
from .artist_search import deezer_search
from .models import (
    Artist, ArtistList, ArtistSuggestion, Event, EventSeen, ListArtist, ListInvite,
    ListMember, ShareLink, User,
)
from .scheduler import start_scheduler
from .scraper import scrape_all, scrape_artist


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # additive: creates new tables, leaves existing
    start_scheduler()
    yield


app = FastAPI(title="Frontrow", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


class NameIn(BaseModel):
    name: str


class ShareIn(BaseModel):
    role: str = "viewer"


class JoinIn(BaseModel):
    token: str


class SeenIn(BaseModel):
    product_id: str


class InviteIn(BaseModel):
    email: str
    role: str = "editor"


# ── helpers ──────────────────────────────────────────────────────────────────
def _naive(dt):
    return dt.replace(tzinfo=None) if (dt and dt.tzinfo) else dt


def _event_dict(e: Event, is_new: bool) -> dict:
    return {
        "id": e.id,
        "product_id": e.product_id,
        "artist": e.artist.name,
        "name": e.name,
        "start_date": e.start_date.isoformat() if e.start_date else None,
        "city": e.city,
        "venue": e.venue,
        "link": e.link,
        "is_new": is_new,
    }


def _list_events(db: Session, lst: ArtistList, user: User | None) -> list[dict]:
    """Events for every artist in the list. `is_new` is per-user: a show is new if
    it was first seen after the user added that artist and they haven't marked it
    seen. Anonymous (public share) callers get is_new=False."""
    added_by_artist = {la.artist_id: _naive(la.added_at) for la in lst.artists_assoc}
    artist_ids = list(added_by_artist)
    if not artist_ids:
        return []
    events = db.query(Event).filter(Event.artist_id.in_(artist_ids)).all()
    seen: set[str] = set()
    if user is not None:
        seen = {s.product_id for s in db.query(EventSeen).filter(EventSeen.user_id == user.id)}
    out = []
    for e in events:
        is_new = False
        if user is not None:
            fs, added = _naive(e.first_seen_at), added_by_artist.get(e.artist_id)
            is_new = e.product_id not in seen and bool(fs and added and fs >= added)
        out.append(_event_dict(e, is_new))
    out.sort(key=lambda d: (d["start_date"] is None, d["start_date"] or ""))
    return out


def _list_summary(db: Session, lst: ArtistList, role: str) -> dict:
    invite_count = (
        db.query(ListInvite).filter_by(list_id=lst.id).count() if role == "owner" else 0
    )
    shared_out = role == "owner" and (
        any(s.enabled for s in lst.shares) or len(lst.members) > 1 or invite_count > 0
    )
    return {
        "id": lst.id,
        "name": lst.name,
        "is_default": lst.is_default,
        "role": role,
        "can_edit": role in ("owner", "editor"),
        "artist_count": len(lst.artists_assoc),
        "shared_with_me": role != "owner",  # someone shared this list with me
        "shared_out": shared_out,           # I own it and it's shared with others
    }


def _artist_or_create(db: Session, name: str) -> Artist:
    artist = db.query(Artist).filter(Artist.name == name).first()
    if artist is None:
        artist = Artist(name=name)
        db.add(artist)
        db.commit()
        db.refresh(artist)
    return artist


# ── identity ─────────────────────────────────────────────────────────────────
@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return {"email": user.email, "name": user.name}


# ── lists ────────────────────────────────────────────────────────────────────
@app.get("/api/lists")
def list_lists(user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned = db.query(ArtistList).filter(ArtistList.owner_id == user.id).all()
    member_of = (
        db.query(ArtistList)
        .join(ListMember, ListMember.list_id == ArtistList.id)
        .filter(ListMember.user_id == user.id, ArtistList.owner_id != user.id)
        .all()
    )
    out = [_list_summary(db, l, "owner") for l in owned]
    out += [_list_summary(db, l, role_of(db, user, l)) for l in member_of]
    out.sort(key=lambda d: (not d["is_default"], d["name"].lower()))
    return out


@app.post("/api/lists")
def create_list(payload: NameIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "List name required")
    lst = ArtistList(owner_id=user.id, name=name, is_default=False)
    db.add(lst)
    db.commit()
    db.refresh(lst)
    db.add(ListMember(list_id=lst.id, user_id=user.id, role="owner"))
    db.commit()
    return _list_summary(db, lst, "owner")


@app.get("/api/lists/{list_id}")
def get_list(list_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lst = require_view(db, user, list_id)
    role = role_of(db, user, lst)
    summary = _list_summary(db, lst, role)
    summary["artists"] = sorted(
        ({"id": la.artist.id, "name": la.artist.name, "event_count": len(la.artist.events)}
         for la in lst.artists_assoc),
        key=lambda a: a["name"].lower(),
    )
    return summary


@app.patch("/api/lists/{list_id}")
def rename_list(list_id: int, payload: NameIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lst = require_owner(db, user, list_id)
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "List name required")
    lst.name = name
    db.commit()
    return _list_summary(db, lst, "owner")


@app.delete("/api/lists/{list_id}")
def delete_list(list_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lst = require_owner(db, user, list_id)
    if lst.is_default:
        raise HTTPException(400, "Can't delete your default list")
    db.delete(lst)
    db.commit()
    return {"deleted": list_id}


@app.get("/api/lists/{list_id}/events")
def list_events(list_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lst = require_view(db, user, list_id)
    return _list_events(db, lst, user)


@app.post("/api/lists/{list_id}/artists")
def add_artist(list_id: int, payload: NameIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lst = require_edit(db, user, list_id)
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "Artist name required")

    artist = _artist_or_create(db, name)
    if not db.query(ListArtist).filter_by(list_id=lst.id, artist_id=artist.id).first():
        db.add(ListArtist(list_id=lst.id, artist_id=artist.id))
        db.commit()

    try:
        found = scrape_artist(db, artist)
    except Exception as exc:  # Eventim down / blocked — keep it tracked, scrape next cycle
        db.rollback()
        return {"artist_id": artist.id, "name": name, "concerts_found": 0, "warning": str(exc)}
    return {"artist_id": artist.id, "name": name, "concerts_found": found}


@app.delete("/api/lists/{list_id}/artists/{artist_id}")
def remove_artist(list_id: int, artist_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lst = require_edit(db, user, list_id)
    assoc = db.query(ListArtist).filter_by(list_id=lst.id, artist_id=artist_id).first()
    if not assoc:
        raise HTTPException(404, "Artist not in this list")
    db.delete(assoc)
    db.commit()
    return {"removed": artist_id}


# ── sharing ──────────────────────────────────────────────────────────────────
def _share_dict(link: ShareLink) -> dict:
    return {"id": link.id, "token": link.token, "role": link.role,
            "enabled": link.enabled, "url": f"/s/{link.token}"}


@app.get("/api/lists/{list_id}/shares")
def list_shares(list_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lst = require_owner(db, user, list_id)
    return [_share_dict(s) for s in lst.shares if s.enabled]


@app.post("/api/lists/{list_id}/shares")
def create_share(list_id: int, payload: ShareIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lst = require_owner(db, user, list_id)
    role = payload.role if payload.role in ("viewer", "editor") else "viewer"
    link = ShareLink(list_id=lst.id, token=secrets.token_urlsafe(12), role=role, enabled=True)
    db.add(link)
    db.commit()
    db.refresh(link)
    return _share_dict(link)


@app.delete("/api/shares/{share_id}")
def revoke_share(share_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    link = db.get(ShareLink, share_id)
    if not link:
        raise HTTPException(404, "Share not found")
    require_owner(db, user, link.list_id)
    db.delete(link)
    db.commit()
    return {"revoked": share_id}


@app.post("/api/shares/join")
def join_share(payload: JoinIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """A logged-in, allow-listed user opens an editor link and becomes an editor."""
    link = db.query(ShareLink).filter(ShareLink.token == payload.token, ShareLink.enabled.is_(True)).first()
    if not link:
        raise HTTPException(404, "This link isn't live anymore")
    if link.role != "editor":
        raise HTTPException(400, "This is a view-only link")
    lst = link.list
    if role_of(db, user, lst) is None:
        db.add(ListMember(list_id=lst.id, user_id=user.id, role="editor"))
        db.commit()
    return {"list_id": lst.id, "name": lst.name}


# ── members / email invites ──────────────────────────────────────────────────
@app.get("/api/lists/{list_id}/members")
def list_members(list_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lst = require_owner(db, user, list_id)
    members = []
    for m in lst.members:
        u = db.get(User, m.user_id)
        members.append({
            "user_id": m.user_id,
            "email": u.email if u else "?",
            "name": u.name if u else None,
            "role": m.role,
            "is_you": m.user_id == user.id,
        })
    members.sort(key=lambda x: (x["role"] != "owner", x["email"]))
    invites = [
        {"id": inv.id, "email": inv.email, "role": inv.role}
        for inv in db.query(ListInvite).filter_by(list_id=lst.id)
    ]
    return {"members": members, "invites": invites}


@app.post("/api/lists/{list_id}/invites")
def invite_member(list_id: int, payload: InviteIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lst = require_owner(db, user, list_id)
    email = payload.email.strip().lower()
    if "@" not in email:
        raise HTTPException(400, "Enter a valid email")
    if email == user.email:
        raise HTTPException(400, "You already own this list")
    role = payload.role if payload.role in ("editor", "viewer") else "editor"

    existing = db.query(User).filter(User.email == email).first()
    if existing:  # already has an account → add them straight away
        m = db.query(ListMember).filter_by(list_id=lst.id, user_id=existing.id).first()
        if m:
            m.role = role
        else:
            db.add(ListMember(list_id=lst.id, user_id=existing.id, role=role))
        db.commit()
        return {"status": "added", "email": email, "role": role}

    inv = db.query(ListInvite).filter_by(list_id=lst.id, email=email).first()
    if inv:
        inv.role = role
    else:
        db.add(ListInvite(list_id=lst.id, email=email, role=role))
    db.commit()
    return {"status": "invited", "email": email, "role": role}


@app.delete("/api/lists/{list_id}/members/{member_user_id}")
def remove_member(list_id: int, member_user_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lst = require_owner(db, user, list_id)
    if member_user_id == lst.owner_id:
        raise HTTPException(400, "The owner can't be removed")
    m = db.query(ListMember).filter_by(list_id=lst.id, user_id=member_user_id).first()
    if m:
        db.delete(m)
        db.commit()
    return {"removed": member_user_id}


@app.delete("/api/invites/{invite_id}")
def cancel_invite(invite_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    inv = db.get(ListInvite, invite_id)
    if not inv:
        raise HTTPException(404, "Invite not found")
    require_owner(db, user, inv.list_id)
    db.delete(inv)
    db.commit()
    return {"cancelled": invite_id}


# Public (no auth) — must be added to oauth2-proxy --skip-auth-route.
@app.get("/api/shared/{token}")
def shared_view(token: str, db: Session = Depends(get_db)):
    link = db.query(ShareLink).filter(ShareLink.token == token, ShareLink.enabled.is_(True)).first()
    if not link:
        raise HTTPException(404, "This link isn't live anymore")
    lst = link.list
    owner = lst.owner
    return {
        "owner_name": (owner.name or owner.email.split("@")[0]),
        "list_name": lst.name,
        "role": link.role,
        "concerts": _list_events(db, lst, user=None),
    }


# ── events / scrape ──────────────────────────────────────────────────────────
@app.post("/api/events/seen")
def mark_seen(payload: SeenIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.query(EventSeen).filter_by(user_id=user.id, product_id=payload.product_id).first():
        db.add(EventSeen(user_id=user.id, product_id=payload.product_id))
        db.commit()
    return {"product_id": payload.product_id, "is_new": False}


@app.get("/api/artists/search")
def artist_search(q: str = "", limit: int = 8, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Autocomplete artist names. Cache-first: if we already have prefix matches in our
    DB we serve those and skip Deezer entirely; only a cache miss triggers one Deezer
    call, whose results we then store — so external calls stay minimal."""
    q = q.strip()
    if len(q) < 2:
        return []
    limit = max(1, min(limit, 15))

    cached = (
        db.query(ArtistSuggestion)
        .filter(ArtistSuggestion.name.ilike(f"{q}%"))
        .order_by(ArtistSuggestion.name)
        .limit(limit)
        .all()
    )
    if cached:
        return [{"name": r.name, "image": r.image} for r in cached]  # cache hit — no Deezer call

    try:
        fresh = deezer_search(q, limit)
    except Exception:
        fresh = []
    for r in fresh:
        if not db.query(ArtistSuggestion).filter_by(name=r["name"]).first():
            db.add(ArtistSuggestion(name=r["name"], image=r.get("image")))
    if fresh:
        db.commit()
    return fresh[:limit]


@app.post("/api/scrape")
def trigger_scrape(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return scrape_all(db)


# Public read-only share page (must be added to oauth2-proxy --skip-auth-route).
@app.get("/s/{token}")
def shared_page(token: str):
    return FileResponse("frontend/share.html")


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
