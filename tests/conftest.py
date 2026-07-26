from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Event


def fake_scrape(db, artist):
    """Stand-in for the Eventim scrape: gives each artist two shows, no network."""
    existing = {e.product_id for e in artist.events}
    added = 0
    for i in range(2):
        pid = f"{artist.name.lower()}-{i}"
        if pid in existing:
            continue
        db.add(Event(
            product_id=pid, artist_id=artist.id, name=f"{artist.name} — Show {i}",
            start_date=datetime(2027, 3, 14, 19, 30),
            city="Berlin" if i == 0 else "Köln", venue="Columbiahalle",
            link="https://example.com/tickets" if i == 0 else None,
        ))
        added += 1
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
