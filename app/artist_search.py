import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import Artist, ArtistSuggestion

# Deezer's search is free, needs no key, and returns clean artist names + a thumbnail.
# We use it for the add-artist autocomplete and artist thumbnails; tracking/events stay
# on Eventim.
DEEZER_URL = "https://api.deezer.com/search/artist"


def deezer_search(q: str, limit: int = 8) -> list[dict]:
    """Return [{name, image}] for an artist query. Raises on network/HTTP error so the
    caller can fall back to the local cache."""
    resp = httpx.get(DEEZER_URL, params={"q": q, "limit": limit}, timeout=6.0)
    resp.raise_for_status()
    out: list[dict] = []
    for artist in resp.json().get("data", []):
        name = (artist.get("name") or "").strip()
        if name:
            out.append({"name": name, "image": artist.get("picture_small")})
    return out


def _suggestion(db: Session, name: str) -> ArtistSuggestion | None:
    return db.query(ArtistSuggestion).filter(func.lower(ArtistSuggestion.name) == name.lower()).first()


def ensure_artist_image(db: Session, artist: Artist) -> None:
    """Give a tracked artist the same thumbnail the search bar shows. Cache-first: the
    autocomplete usually cached it already, so this rarely costs a Deezer call. Silent
    on failure — a missing picture is not worth failing an add or a scrape over."""
    if artist.image:
        return

    cached = _suggestion(db, artist.name)
    if cached and cached.image:
        artist.image = cached.image
        db.commit()
        return

    try:
        results = deezer_search(artist.name, limit=5)
    except Exception:
        return
    match = next((r for r in results if r["name"].lower() == artist.name.lower() and r["image"]), None)
    if not match:
        return

    artist.image = match["image"]
    if not _suggestion(db, match["name"]):
        db.add(ArtistSuggestion(name=match["name"], image=match["image"]))
    db.commit()
