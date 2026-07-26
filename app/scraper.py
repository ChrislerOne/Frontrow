from sqlalchemy.orm import Session

from .adapters.eventim import EventimAdapter
from .models import Artist, Event, ListArtist

adapter = EventimAdapter()


def scrape_artist(db: Session, artist: Artist) -> int:
    known_ids = {event.product_id for event in artist.events}
    new_count = 0

    for concert in adapter.fetch_concerts(artist.name):
        if concert.product_id in known_ids:
            continue  # already stored, or a duplicate across paginated results
        known_ids.add(concert.product_id)
        db.add(
            Event(
                product_id=concert.product_id,
                artist_id=artist.id,
                name=concert.name,
                start_date=concert.start_date,
                city=concert.city,
                venue=concert.venue,
                link=concert.link,
            )
        )
        new_count += 1

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
    return results
