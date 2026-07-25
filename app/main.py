from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Artist, Event
from .scheduler import start_scheduler
from .scraper import scrape_all, scrape_artist


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield


app = FastAPI(title="Frontrow", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ArtistIn(BaseModel):
    name: str


def _event_dict(event: Event) -> dict:
    return {
        "id": event.id,
        "artist": event.artist.name,
        "name": event.name,
        "start_date": event.start_date.isoformat() if event.start_date else None,
        "city": event.city,
        "venue": event.venue,
        "link": event.link,
        "is_new": event.is_new,
    }


@app.post("/api/artists")
def add_artist(payload: ArtistIn, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "Artist name required")

    artist = db.query(Artist).filter(Artist.name == name).first()
    already_tracked = artist is not None
    if artist is None:
        artist = Artist(name=name)
        db.add(artist)
        db.commit()
        db.refresh(artist)
    artist_id = artist.id

    try:
        # Scrape on add and on re-add — idempotent, so re-adding just refreshes and
        # recovers an artist whose first scrape was blocked.
        found = scrape_artist(db, artist)
    except Exception as exc:  # Eventim down / blocked — keep the artist, scrape next cycle
        db.rollback()
        return {"id": artist_id, "name": name, "already_tracked": already_tracked,
                "concerts_found": 0, "warning": str(exc)}
    return {"id": artist_id, "name": name, "already_tracked": already_tracked,
            "concerts_found": found}


@app.get("/api/artists")
def list_artists(db: Session = Depends(get_db)):
    return [
        {"id": a.id, "name": a.name, "event_count": len(a.events)}
        for a in db.query(Artist).order_by(Artist.name).all()
    ]


@app.delete("/api/artists/{artist_id}")
def remove_artist(artist_id: int, db: Session = Depends(get_db)):
    artist = db.get(Artist, artist_id)
    if not artist:
        raise HTTPException(404, "Artist not found")
    db.delete(artist)
    db.commit()
    return {"deleted": artist_id}


@app.get("/api/events")
def list_events(only_new: bool = False, city: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Event)
    if only_new:
        query = query.filter(Event.is_new.is_(True))
    if city:
        query = query.filter(Event.city == city)
    return [_event_dict(e) for e in query.order_by(Event.start_date).all()]


@app.get("/api/cities")
def list_cities(db: Session = Depends(get_db)):
    rows = (
        db.query(Event.city)
        .filter(Event.city.isnot(None))
        .distinct()
        .order_by(Event.city)
        .all()
    )
    return [row[0] for row in rows]


@app.post("/api/events/{event_id}/seen")
def mark_seen(event_id: int, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    event.is_new = False
    db.commit()
    return {"id": event_id, "is_new": False}


@app.post("/api/scrape")
def trigger_scrape(db: Session = Depends(get_db)):
    return scrape_all(db)


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
