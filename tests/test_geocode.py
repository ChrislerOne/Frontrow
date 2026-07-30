"""Geocoding is cache-first and permanent, because Nominatim's usage policy requires it
and because venues don't move. These tests pin that down: nothing here touches the network.
"""

from datetime import datetime

from app import geocode
from app.models import Artist, Event, Place


def _event(db, **kw):
    artist = db.query(Artist).filter_by(name="Bonobo").first() or Artist(name="Bonobo")
    db.add(artist)
    db.commit()
    fields = dict(product_id=f"p{kw.pop('n', 1)}", artist_id=artist.id, name="Show",
                  start_date=datetime(2027, 5, 1, 20, 0))
    fields.update(kw)
    e = Event(**fields)
    db.add(e)
    db.commit()
    return e


def test_a_resolved_place_is_never_looked_up_twice(session_factory, monkeypatch):
    db = session_factory()
    calls = {"n": 0}

    def fake(params):
        calls["n"] += 1
        return [{"lat": "52.5", "lon": "13.4", "display_name": "Berlin, Deutschland"}]

    monkeypatch.setattr(geocode, "_throttled_get", fake)
    assert geocode.city_point(db, "Berlin") == (52.5, 13.4)
    assert geocode.city_point(db, "Berlin") == (52.5, 13.4)
    assert geocode.city_point(db, " Berlin ") == (52.5, 13.4)  # normalised to the same key
    assert calls["n"] == 1
    db.close()


def test_a_place_that_cannot_be_found_is_remembered_as_a_miss(session_factory, monkeypatch):
    """Otherwise every scrape would re-ask for the same unfindable venue."""
    db = session_factory()
    calls = {"n": 0}

    def empty(params):
        calls["n"] += 1
        return []

    monkeypatch.setattr(geocode, "_throttled_get", empty)
    assert geocode.city_point(db, "Nowhere-at-all") is None
    assert geocode.city_point(db, "Nowhere-at-all") is None
    assert calls["n"] == 1
    row = db.query(Place).filter_by(query="Nowhere-at-all").one()
    assert row.latitude is None
    db.close()


def test_a_network_failure_is_not_cached(session_factory, monkeypatch):
    db = session_factory()

    def boom(params):
        raise RuntimeError("nominatim down")

    monkeypatch.setattr(geocode, "_throttled_get", boom)
    assert geocode.city_point(db, "Bremen") is None
    assert db.query(Place).count() == 0  # so it can be retried later
    db.close()


def test_backfill_prefers_the_venue_then_falls_back_to_the_city(session_factory, monkeypatch):
    db = session_factory()
    asked = []

    def fake(params):
        asked.append(params["q"])
        if params["q"] == "Kulturzentrum Lagerhaus, Bremen":
            return []                                  # venue unknown to OSM
        return [{"lat": "53.07", "lon": "8.8", "display_name": "Bremen"}]

    monkeypatch.setattr(geocode, "_throttled_get", fake)
    e = _event(db, n=1, city="Bremen", venue="Kulturzentrum Lagerhaus")
    assert geocode.backfill_event_coords(db) == 1
    assert asked == ["Kulturzentrum Lagerhaus, Bremen", "Bremen"]
    db.refresh(e)
    assert (e.latitude, e.longitude) == (53.07, 8.8)
    db.close()


def test_backfill_skips_events_that_already_have_coordinates(session_factory, monkeypatch):
    db = session_factory()
    monkeypatch.setattr(geocode, "_throttled_get",
                        lambda params: (_ for _ in ()).throw(AssertionError("must not geocode")))
    _event(db, n=2, city="Berlin", venue="Columbiahalle", latitude=52.49, longitude=13.42)
    assert geocode.backfill_event_coords(db) == 0
    db.close()


def test_backfill_is_bounded_per_run(session_factory, monkeypatch):
    """A scrape cycle must not turn into a geocoding marathon."""
    db = session_factory()
    calls = {"n": 0}

    def fake(params):
        calls["n"] += 1
        return [{"lat": "50.0", "lon": "8.0", "display_name": "x"}]

    monkeypatch.setattr(geocode, "_throttled_get", fake)
    for i in range(6):
        _event(db, n=10 + i, city=f"City{i}")
    assert geocode.backfill_event_coords(db, limit=2) == 2
    assert calls["n"] == 2
    db.close()


def test_events_expose_coordinates_and_me_exposes_the_home_point(client, monkeypatch, session_factory):
    from tests.conftest import H

    monkeypatch.setattr(geocode, "_throttled_get",
                        lambda params: [{"lat": "50.94", "lon": "6.96", "display_name": "Köln"}])
    client.get("/api/me", headers=H("a@x.com"))
    lid = client.get("/api/lists", headers=H("a@x.com")).json()[0]["id"]
    client.post(f"/api/lists/{lid}/artists", json={"name": "Bonobo"}, headers=H("a@x.com"))

    evs = client.get(f"/api/lists/{lid}/events", headers=H("a@x.com")).json()
    assert all("lat" in e and "lon" in e for e in evs)

    assert client.get("/api/me", headers=H("a@x.com")).json()["home"] is None
    me = client.patch("/api/me", json={"default_city": "Köln"}, headers=H("a@x.com")).json()
    assert me["home"] == {"city": "Köln", "lat": 50.94, "lon": 6.96}
    # and the read path serves it from cache without geocoding again
    monkeypatch.setattr(geocode, "_throttled_get",
                        lambda params: (_ for _ in ()).throw(AssertionError("GET /api/me must not geocode")))
    assert client.get("/api/me", headers=H("a@x.com")).json()["home"]["lat"] == 50.94
