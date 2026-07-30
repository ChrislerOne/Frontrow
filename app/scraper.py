from sqlalchemy.orm import Session

from .adapters.base import ConcertResult
from .adapters.eventim import EventimAdapter
from .artist_search import ensure_artist_image
from .models import Artist, Event, ListArtist, utcnow

adapter = EventimAdapter()


def _apply(event: Event, concert: ConcertResult) -> None:
    """Refresh the volatile fields. Availability and price change over the life of a
    show — a date that was on sale last cycle can be sold out this one — so a known
    event is updated rather than skipped."""
    event.name = concert.name
    event.start_date = concert.start_date
    event.city = concert.city
    event.venue = concert.venue
    event.link = concert.link
    event.status = concert.status
    event.in_stock = concert.in_stock
    event.price = concert.price
    event.currency = concert.currency
    # Only ever set coordinates, never clear them: a later payload that omits geoLocation
    # must not wipe a position we already resolved.
    if concert.latitude is not None and concert.longitude is not None:
        event.latitude, event.longitude = concert.latitude, concert.longitude
    event.last_checked_at = utcnow()


def scrape_artist(db: Session, artist: Artist) -> int:
    known = {event.product_id: event for event in artist.events}
    seen: set[str] = set()
    new_count = 0

    for concert in adapter.fetch_concerts(artist.name):
        if concert.product_id in seen:
            continue  # duplicate across paginated results
        seen.add(concert.product_id)

        event = known.get(concert.product_id)
        if event is None:
            event = Event(product_id=concert.product_id, artist_id=artist.id)
            db.add(event)
            new_count += 1
        _apply(event, concert)

    artist.last_checked_at = utcnow()
    db.commit()
    return new_count


def scrape_all(db: Session) -> dict[str, int]:
    """Scrape every artist that belongs to at least one list. Artists nobody tracks
    are left alone."""
    tracked_ids = {row[0] for row in db.query(ListArtist.artist_id).distinct().all()}
    results: dict[str, int] = {}
    if not tracked_ids:
        return results
    for artist in db.query(Artist).filter(Artist.id.in_(tracked_ids)).all():
        try:
            results[artist.name] = scrape_artist(db, artist)
        except Exception as exc:  # one blocked artist shouldn't abort the whole refresh
            db.rollback()
            print(f"[scrape] '{artist.name}' failed: {exc}")
            results[artist.name] = 0
        ensure_artist_image(db, artist)  # backfills thumbnails added before this ran
    return results
