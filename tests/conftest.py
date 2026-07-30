from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Event, utcnow


def fake_scrape(db, artist):
    """Stand-in for the Eventim scrape, no network: every artist gets two shows — the
    first on sale with a price, the second sold out."""
    existing = {e.product_id: e for e in artist.events}
    added = 0
    for i in range(2):
        pid = f"{artist.name.lower()}-{i}"
        event = existing.get(pid)
        if event is None:
            event = Event(product_id=pid, artist_id=artist.id)
            db.add(event)
            added += 1
        event.name = f"{artist.name} — Show {i}"
        event.start_date = datetime(2027, 3, 14, 19, 30)
        event.city = "Berlin" if i == 0 else "Köln"
        event.venue = "Columbiahalle"
        event.link = "https://example.com/tickets" if i == 0 else None
        event.status = "Available" if i == 0 else "SoldOut"
        event.in_stock = i == 0
        event.price = 45.45 if i == 0 else None
        event.currency = "EUR" if i == 0 else None
        event.last_checked_at = utcnow()
    artist.last_checked_at = utcnow()
    db.commit()
    return added


@pytest.fixture
def session_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path/'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False)


@pytest.fixture
def client(session_factory, monkeypatch):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # The scrape is exercised via both add-artist (app.main) and scrape_all (app.scraper).
    monkeypatch.setattr("app.main.scrape_artist", fake_scrape)
    monkeypatch.setattr("app.scraper.scrape_artist", fake_scrape)
    yield TestClient(app)
    app.dependency_overrides.clear()


def H(email):
    """Auth header the way oauth2-proxy sets it on the upstream request."""
    return {"X-Forwarded-Email": email}
