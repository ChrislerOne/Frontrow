"""Geocoding via OpenStreetMap's Nominatim, used as sparingly as possible.

Eventim already supplies coordinates for ~97% of products, so this exists for the
remainder plus the home city a user picks in Profile. Every result is written to the
`places` table and never looked up again — venues and cities don't move, and Nominatim's
usage policy requires caching, a single thread, an identifying User-Agent and at most one
request a second. A lookup that finds nothing is cached as a NULL row so it isn't retried
on every scrape.

Policy: https://operations.osmfoundation.org/policies/nominatim/
"""

import threading
import time

import httpx
from sqlalchemy.orm import Session

from .models import Event, Place

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "Frontrow/1.0 (private concert tracker; +https://frontrow.lewerenz.app)"
MIN_INTERVAL = 1.1          # seconds between network calls; policy says max 1/s
BACKFILL_PER_RUN = 8        # keeps a scrape cycle short; the rest go next time

_lock = threading.Lock()    # the scheduler thread and a request can both land here
_last_call = 0.0


def _throttled_get(params: dict) -> list:
    global _last_call
    with _lock:
        wait = MIN_INTERVAL - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        try:
            resp = httpx.get(
                NOMINATIM_URL,
                params={**params, "format": "jsonv2", "limit": 1},
                headers={"User-Agent": USER_AGENT, "Accept-Language": "de,en"},
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()
        finally:
            _last_call = time.monotonic()


def place_for(db: Session, query: str, *, resolve: bool = True) -> Place | None:
    """Resolve a free-text place, cache-first. Returns the cached row even when it holds
    no coordinates — that's a remembered miss, not a reason to ask again.

    With resolve=False this is cache-only and never touches the network, which is what
    read paths want: GET /api/me runs on every page load and must not be able to block
    on a slow geocoder."""
    query = " ".join((query or "").split())
    if not query:
        return None

    cached = db.query(Place).filter(Place.query == query).first()
    if cached or not resolve:
        return cached

    lat = lon = label = None
    try:
        # No country restriction. Eventim sells across DE/AT/CH, and pinning the search
        # to one country doesn't fail — it silently returns the wrong place. "St. Pölten"
        # with countrycodes=de resolved to a spot in Bavaria, 330 km from the Austrian
        # city it meant.
        hits = _throttled_get({"q": query})
        if hits:
            lat, lon = float(hits[0]["lat"]), float(hits[0]["lon"])
            label = hits[0].get("display_name")
    except Exception as exc:
        print(f"[geocode] '{query}' failed: {exc}")
        return None  # a transient failure must not be cached as a miss

    row = Place(query=query, label=label, latitude=lat, longitude=lon)
    db.add(row)
    db.commit()
    return row


def city_point(db: Session, city: str, *, resolve: bool = True) -> tuple[float, float] | None:
    row = place_for(db, city, resolve=resolve)
    if row and row.latitude is not None:
        return row.latitude, row.longitude
    return None


def backfill_event_coords(db: Session, limit: int = BACKFILL_PER_RUN) -> int:
    """Fill in coordinates for events Eventim gave none for, most specific query first.
    Bounded per run so a scrape can't turn into a geocoding marathon.

    Only events that have actually been through a scrape (last_checked_at set) are
    considered. Without that check, adding the coordinate columns made all 69 existing
    rows look unlocated and the first run burned geocodes on venues Eventim supplies
    for free on the next scrape."""
    pending = (
        db.query(Event)
        .filter(Event.latitude.is_(None))
        .filter(Event.last_checked_at.isnot(None))
        .filter((Event.city.isnot(None)) | (Event.venue.isnot(None)))
        .limit(limit)
        .all()
    )
    filled = 0
    for event in pending:
        for query in _queries(event):
            row = place_for(db, query)
            if row and row.latitude is not None:
                event.latitude, event.longitude = row.latitude, row.longitude
                filled += 1
                break
    if filled:
        db.commit()
    return filled


def _queries(event: Event) -> list[str]:
    out = []
    if event.venue and event.city:
        out.append(f"{event.venue}, {event.city}")
    if event.city:
        out.append(event.city)
    return out
