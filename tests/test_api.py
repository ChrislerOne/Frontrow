from app.models import Artist

from tests.conftest import H


def default_list(client, email):
    client.get("/api/me", headers=H(email))  # first touch creates the user + default list
    return client.get("/api/lists", headers=H(email)).json()[0]


# ── identity & lists ─────────────────────────────────────────────────────────
def test_me_creates_user_and_default_list(client):
    r = client.get("/api/me", headers=H("a@x.com"))
    assert r.status_code == 200 and r.json()["email"] == "a@x.com"
    lists = client.get("/api/lists", headers=H("a@x.com")).json()
    assert len(lists) == 1
    assert lists[0]["is_default"] and lists[0]["name"] == "My artists" and lists[0]["role"] == "owner"


def test_no_auth_header_is_401(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/lists").status_code == 401


def test_create_and_delete_list(client):
    default_list(client, "a@x.com")
    made = client.post("/api/lists", json={"name": "Festivals"}, headers=H("a@x.com")).json()
    assert made["name"] == "Festivals" and made["role"] == "owner" and not made["is_default"]
    assert len(client.get("/api/lists", headers=H("a@x.com")).json()) == 2
    assert client.delete(f"/api/lists/{made['id']}", headers=H("a@x.com")).status_code == 200
    assert len(client.get("/api/lists", headers=H("a@x.com")).json()) == 1


def test_cannot_delete_default_list(client):
    lid = default_list(client, "a@x.com")["id"]
    assert client.delete(f"/api/lists/{lid}", headers=H("a@x.com")).status_code == 400


# ── artists & events ─────────────────────────────────────────────────────────
def test_add_artist_populates_events(client):
    lid = default_list(client, "a@x.com")["id"]
    r = client.post(f"/api/lists/{lid}/artists", json={"name": "Bonobo"}, headers=H("a@x.com"))
    assert r.status_code == 200 and r.json()["concerts_found"] == 2
    evs = client.get(f"/api/lists/{lid}/events", headers=H("a@x.com")).json()
    assert len(evs) == 2
    assert all(e["is_new"] for e in evs)  # everything is new right after you add the artist


def test_remove_artist(client):
    lid = default_list(client, "a@x.com")["id"]
    aid = client.post(f"/api/lists/{lid}/artists", json={"name": "Bonobo"}, headers=H("a@x.com")).json()["artist_id"]
    assert client.delete(f"/api/lists/{lid}/artists/{aid}", headers=H("a@x.com")).status_code == 200
    assert client.get(f"/api/lists/{lid}/events", headers=H("a@x.com")).json() == []


def test_attending_toggle_is_per_user(client):
    lid = default_list(client, "a@x.com")["id"]
    client.post(f"/api/lists/{lid}/artists", json={"name": "Bonobo"}, headers=H("a@x.com"))
    evs = client.get(f"/api/lists/{lid}/events", headers=H("a@x.com")).json()
    pid = evs[0]["product_id"]
    assert all(e["attending"] is False for e in evs)
    assert client.post("/api/events/attending", json={"product_id": pid, "attending": True}, headers=H("a@x.com")).status_code == 200
    after = client.get(f"/api/lists/{lid}/events", headers=H("a@x.com")).json()
    assert {e["product_id"]: e["attending"] for e in after}[pid] is True
    # a different user is unaffected, and toggling off works
    default_list(client, "b@x.com")
    client.post(f"/api/lists/{lid}/invites", json={"email": "b@x.com", "role": "viewer"}, headers=H("a@x.com"))
    b_evs = client.get(f"/api/lists/{lid}/events", headers=H("b@x.com")).json()
    assert {e["product_id"]: e["attending"] for e in b_evs}[pid] is False
    client.post("/api/events/attending", json={"product_id": pid, "attending": False}, headers=H("a@x.com"))
    a_evs = client.get(f"/api/lists/{lid}/events", headers=H("a@x.com")).json()
    assert {e["product_id"]: e["attending"] for e in a_evs}[pid] is False


# ── permissions ──────────────────────────────────────────────────────────────
def test_non_member_cannot_see_or_edit(client):
    lid = default_list(client, "a@x.com")["id"]
    client.post(f"/api/lists/{lid}/artists", json={"name": "Bonobo"}, headers=H("a@x.com"))
    default_list(client, "b@x.com")  # b exists but is not on a's list
    assert client.get(f"/api/lists/{lid}", headers=H("b@x.com")).status_code == 403
    assert client.get(f"/api/lists/{lid}/events", headers=H("b@x.com")).status_code == 403
    assert client.post(f"/api/lists/{lid}/artists", json={"name": "X"}, headers=H("b@x.com")).status_code == 403


def test_only_owner_can_rename(client):
    lid = default_list(client, "a@x.com")["id"]
    # b becomes an editor via a share, then still can't rename
    share = client.post(f"/api/lists/{lid}/shares", json={"role": "editor"}, headers=H("a@x.com")).json()
    client.post("/api/shares/join", json={"token": share["token"]}, headers=H("b@x.com"))
    assert client.patch(f"/api/lists/{lid}", json={"name": "hax"}, headers=H("b@x.com")).status_code == 403
    assert client.patch(f"/api/lists/{lid}", json={"name": "Renamed"}, headers=H("a@x.com")).status_code == 200


# ── sharing ──────────────────────────────────────────────────────────────────
def test_viewer_share_is_public_and_readonly(client):
    lid = default_list(client, "a@x.com")["id"]
    client.post(f"/api/lists/{lid}/artists", json={"name": "Bonobo"}, headers=H("a@x.com"))
    share = client.post(f"/api/lists/{lid}/shares", json={"role": "viewer"}, headers=H("a@x.com")).json()
    # public — no auth header at all
    pub = client.get(f"/api/shared/{share['token']}")
    assert pub.status_code == 200
    body = pub.json()
    assert body["role"] == "viewer" and len(body["concerts"]) == 2 and body["list_name"] == "My artists"
    # a viewer link can't be joined as editor
    assert client.post("/api/shares/join", json={"token": share["token"]}, headers=H("b@x.com")).status_code == 400


def test_editor_share_lets_another_user_add(client):
    lid = default_list(client, "a@x.com")["id"]
    share = client.post(f"/api/lists/{lid}/shares", json={"role": "editor"}, headers=H("a@x.com")).json()
    joined = client.post("/api/shares/join", json={"token": share["token"]}, headers=H("b@x.com"))
    assert joined.status_code == 200 and joined.json()["list_id"] == lid
    # b now sees the list as editor and can add an artist
    b_lists = client.get("/api/lists", headers=H("b@x.com")).json()
    shared = [l for l in b_lists if l["id"] == lid][0]
    assert shared["role"] == "editor" and shared["can_edit"]
    add = client.post(f"/api/lists/{lid}/artists", json={"name": "Kraftwerk"}, headers=H("b@x.com"))
    assert add.status_code == 200


def test_revoked_share_is_dead(client):
    lid = default_list(client, "a@x.com")["id"]
    share = client.post(f"/api/lists/{lid}/shares", json={"role": "viewer"}, headers=H("a@x.com")).json()
    assert client.delete(f"/api/shares/{share['id']}", headers=H("a@x.com")).status_code == 200
    assert client.get(f"/api/shared/{share['token']}").status_code == 404


# ── email invites & shared flags ─────────────────────────────────────────────
def test_invite_existing_user_adds_member(client):
    lid = default_list(client, "a@x.com")["id"]
    default_list(client, "b@x.com")  # b already has an account
    r = client.post(f"/api/lists/{lid}/invites", json={"email": "b@x.com", "role": "editor"}, headers=H("a@x.com"))
    assert r.status_code == 200 and r.json()["status"] == "added"
    shared = [l for l in client.get("/api/lists", headers=H("b@x.com")).json() if l["id"] == lid][0]
    assert shared["role"] == "editor" and shared["can_edit"] and shared["shared_with_me"]


def test_invite_pending_resolves_on_first_login(client):
    lid = default_list(client, "a@x.com")["id"]
    assert client.post(f"/api/lists/{lid}/invites", json={"email": "c@x.com", "role": "viewer"}, headers=H("a@x.com")).json()["status"] == "invited"
    c_lists = client.get("/api/lists", headers=H("c@x.com")).json()  # first login → invite resolves
    shared = [l for l in c_lists if l["id"] == lid][0]
    assert shared["role"] == "viewer" and shared["shared_with_me"]


def test_owner_sees_shared_out_flag(client):
    lid = default_list(client, "a@x.com")["id"]
    assert client.get("/api/lists", headers=H("a@x.com")).json()[0]["shared_out"] is False
    client.post(f"/api/lists/{lid}/shares", json={"role": "viewer"}, headers=H("a@x.com"))
    assert client.get("/api/lists", headers=H("a@x.com")).json()[0]["shared_out"] is True


def test_remove_member_and_cancel_invite(client):
    lid = default_list(client, "a@x.com")["id"]
    default_list(client, "b@x.com")
    client.post(f"/api/lists/{lid}/invites", json={"email": "b@x.com", "role": "editor"}, headers=H("a@x.com"))
    b = [m for m in client.get(f"/api/lists/{lid}/members", headers=H("a@x.com")).json()["members"] if m["email"] == "b@x.com"][0]
    assert client.delete(f"/api/lists/{lid}/members/{b['user_id']}", headers=H("a@x.com")).status_code == 200
    assert lid not in [l["id"] for l in client.get("/api/lists", headers=H("b@x.com")).json()]

    client.post(f"/api/lists/{lid}/invites", json={"email": "d@x.com"}, headers=H("a@x.com"))
    iid = client.get(f"/api/lists/{lid}/members", headers=H("a@x.com")).json()["invites"][0]["id"]
    assert client.delete(f"/api/invites/{iid}", headers=H("a@x.com")).status_code == 200
    assert client.get(f"/api/lists/{lid}/members", headers=H("a@x.com")).json()["invites"] == []


def test_non_owner_cannot_manage_members(client):
    lid = default_list(client, "a@x.com")["id"]
    default_list(client, "b@x.com")
    assert client.get(f"/api/lists/{lid}/members", headers=H("b@x.com")).status_code == 403
    assert client.post(f"/api/lists/{lid}/invites", json={"email": "z@x.com"}, headers=H("b@x.com")).status_code == 403


# ── legacy migration ─────────────────────────────────────────────────────────
def test_first_user_adopts_existing_catalog(client, session_factory):
    s = session_factory()
    s.add(Artist(name="Kraftwerk"))
    s.commit()
    s.close()
    lid = default_list(client, "a@x.com")["id"]
    detail = client.get(f"/api/lists/{lid}", headers=H("a@x.com")).json()
    assert any(a["name"] == "Kraftwerk" for a in detail["artists"])


# ── identity display name ────────────────────────────────────────────────────
def test_numeric_google_sub_is_not_used_as_name(client):
    r = client.get("/api/me", headers={"X-Forwarded-Email": "z@x.com", "X-Forwarded-User": "109187918541011064832"})
    assert r.status_code == 200 and r.json()["name"] != "109187918541011064832"


def test_preferred_username_is_used_as_name(client):
    r = client.get("/api/me", headers={"X-Forwarded-Email": "q@x.com", "X-Forwarded-Preferred-Username": "Wendy Appleseed"})
    assert r.json()["name"] == "Wendy Appleseed"


# ── artist autocomplete (cache-first Deezer) ─────────────────────────────────
def test_artist_search_is_cache_first(client, monkeypatch):
    calls = {"n": 0}

    def fake(q, limit=8):
        calls["n"] += 1
        return [{"name": "Fontaines D.C.", "image": None}, {"name": "The Fontaines", "image": None}]

    monkeypatch.setattr("app.main.deezer_search", fake)

    assert client.get("/api/artists/search?q=f", headers=H("a@x.com")).json() == []  # too short
    assert calls["n"] == 0

    r1 = client.get("/api/artists/search?q=fontaines", headers=H("a@x.com")).json()  # cache miss → Deezer once
    assert [x["name"] for x in r1] == ["Fontaines D.C.", "The Fontaines"] and calls["n"] == 1

    r2 = client.get("/api/artists/search?q=fontaines", headers=H("a@x.com")).json()  # cache hit → no call
    assert calls["n"] == 1 and any(x["name"] == "Fontaines D.C." for x in r2)


def test_artist_search_survives_deezer_outage(client, monkeypatch):
    def boom(q, limit=8):
        raise RuntimeError("deezer down")

    monkeypatch.setattr("app.main.deezer_search", boom)
    assert client.get("/api/artists/search?q=zzznomatch", headers=H("a@x.com")).json() == []


def test_artist_search_dedupes_duplicate_names(client, monkeypatch):
    monkeypatch.setattr("app.main.deezer_search", lambda q, limit=8: [{"name": "Bonobo", "image": None}] * 3)
    r = client.get("/api/artists/search?q=bonobo", headers=H("a@x.com")).json()
    assert [x["name"] for x in r] == ["Bonobo"]
