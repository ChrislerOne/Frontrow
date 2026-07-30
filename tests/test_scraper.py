from datetime import datetime

from sqlalchemy import create_engine

from app import scraper
from app.adapters.base import ConcertResult
from app.migrate import ensure_columns
from app.models import Artist


class StubAdapter:
    def __init__(self, results):
        self.results = results

    def fetch_concerts(self, artist_name):
        return self.results


def _result(status, in_stock, price):
    return ConcertResult(
        product_id="p1", name="Show", start_date=datetime(2027, 5, 1, 20, 0),
        city="Berlin", venue="Columbiahalle", link="https://example.com/t",
        status=status, in_stock=in_stock, price=price, currency="EUR" if price else None,
    )


def test_rescrape_refreshes_availability_of_a_known_event(session_factory, monkeypatch):
    """A date that was on sale last cycle can be sold out this one, so a known
    product_id must be updated — not skipped as already-stored."""
    db = session_factory()
    artist = Artist(name="Bonobo")
    db.add(artist)
    db.commit()

    monkeypatch.setattr(scraper, "adapter", StubAdapter([_result("Available", True, 45.45)]))
    assert scraper.scrape_artist(db, artist) == 1
    assert artist.last_checked_at is not None
    event = artist.events[0]
    assert (event.status, event.in_stock, event.price) == ("Available", True, 45.45)

    monkeypatch.setattr(scraper, "adapter", StubAdapter([_result("SoldOut", False, None)]))
    assert scraper.scrape_artist(db, artist) == 0  # nothing new, but the row changes
    db.refresh(event)
    assert (event.status, event.in_stock, event.price) == ("SoldOut", False, None)
    assert len(artist.events) == 1
    db.close()


def test_scrape_marks_artist_checked_even_with_no_results(session_factory, monkeypatch):
    db = session_factory()
    artist = Artist(name="Nobody")
    db.add(artist)
    db.commit()
    monkeypatch.setattr(scraper, "adapter", StubAdapter([]))
    assert scraper.scrape_artist(db, artist) == 0
    assert artist.last_checked_at is not None and artist.events == []
    db.close()


def test_ensure_columns_upgrades_a_pre_existing_table(tmp_path):
    """create_all() never adds a column to a table that already exists — this is what
    keeps a live database usable after a model gains a field."""
    engine = create_engine(f"sqlite:///{tmp_path/'legacy.db'}")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE artists (id INTEGER PRIMARY KEY, name VARCHAR)")

    applied = ensure_columns(engine)
    assert "artists.last_checked_at" in applied
    assert not any(c.startswith("events.") for c in applied)  # that table doesn't exist yet
    with engine.begin() as conn:
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(artists)")}
    assert {"last_checked_at", "image"} <= cols
    assert ensure_columns(engine) == []  # idempotent
