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
                  start_date=datetime(2027, 5, 1, 20, 0),
                  last_checked_at=datetime(2026, 7, 30, 12, 0),
                  geo_source="eventim-city")
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


def test_a_city_centroid_is_upgraded_to_the_real_venue(session_factory, monkeypatch):
    """The bug this fixes: Eventim's geoLocation is the city centre, so seven Berlin
    venues all came back as 52.5167, 13.4000 and stacked into one map pin."""
    db = session_factory()
    asked = []

    def fake(params):
        asked.append(params["q"])
        return [{"lat": "52.4906", "lon": "13.3792", "display_name": "Columbiahalle"}]

    monkeypatch.setattr(geocode, "_throttled_get", fake)
    e = _event(db, n=1, city="Berlin", venue="Columbiahalle", latitude=52.5167, longitude=13.4)
    assert geocode.locate_events(db) == 1
    assert asked == ["Columbiahalle, Berlin"]
    db.refresh(e)
    assert (e.latitude, e.longitude, e.geo_source) == (52.4906, 13.3792, "venue")


def test_a_venue_osm_does_not_know_is_never_asked_about_again(session_factory, monkeypatch):
    db = session_factory()
    calls = {"n": 0}

    def empty(params):
        calls["n"] += 1
        return []

    monkeypatch.setattr(geocode, "_throttled_get", empty)
    e = _event(db, n=2, city="Passau", venue="Zauberberg", latitude=48.57, longitude=13.46)
    assert geocode.locate_events(db) == 0
    db.refresh(e)
    assert e.geo_source == "venue-unknown"
    assert (e.latitude, e.longitude) == (48.57, 13.46)   # the city point stands
    assert geocode.locate_events(db) == 0
    assert calls["n"] == 1                               # asked once, ever


def test_a_venue_point_is_never_overwritten_by_a_later_scrape(session_factory, monkeypatch):
    """Otherwise every 12h cycle would drag the pin back to the city centre."""
    from app import scraper
    from app.adapters.base import ConcertResult
    db = session_factory()
    e = _event(db, n=3, city="Berlin", venue="Columbiahalle",
               latitude=52.4906, longitude=13.3792, geo_source="venue")
    artist = e.artist

    class Stub:
        def fetch_concerts(self, name):
            return [ConcertResult(product_id=e.product_id, name="Show", start_date=e.start_date,
                                  city="Berlin", venue="Columbiahalle", link=None,
                                  latitude=52.5167, longitude=13.4)]

    monkeypatch.setattr(scraper, "adapter", Stub())
    scraper.scrape_artist(db, artist)
    db.refresh(e)
    assert (e.latitude, e.longitude, e.geo_source) == (52.4906, 13.3792, "venue")
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


def test_backfill_ignores_events_that_have_never_been_scraped(session_factory, monkeypatch):
    """Adding the coordinate columns made every existing row look unlocated; without this
    guard the first run spent geocodes on venues Eventim supplies for free."""
    db = session_factory()
    monkeypatch.setattr(geocode, "_throttled_get",
                        lambda params: (_ for _ in ()).throw(AssertionError("must not geocode")))
    e = _event(db, n=30, city="Bremen", venue="Lagerhaus")
    e.last_checked_at = None
    db.commit()
    assert geocode.locate_events(db) == 0
    db.close()


def test_geocoding_is_not_pinned_to_one_country(session_factory, monkeypatch):
    """countrycodes=de didn't fail on Austrian venues, it silently returned a German
    place 330 km away."""
    db = session_factory()
    seen = {}

    def fake(params):
        seen.update(params)
        return [{"lat": "48.2047", "lon": "15.6256", "display_name": "St. Pölten, Österreich"}]

    monkeypatch.setattr(geocode, "_throttled_get", fake)
    assert geocode.city_point(db, "St. Pölten") == (48.2047, 15.6256)
    assert "countrycodes" not in seen
    db.close()
