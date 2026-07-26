import httpx

# Deezer's search is free, needs no key, and returns clean artist names + a thumbnail.
# We use it only to populate the add-artist autocomplete; tracking/events stay on Eventim.
DEEZER_URL = "https://api.deezer.com/search/artist"


def deezer_search(q: str, limit: int = 8) -> list[dict]:
    """Return [{name, image}] for an artist query. Raises on network/HTTP error so the
    caller can fall back to the local cache."""
    resp = httpx.get(DEEZER_URL, params={"q": q, "limit": limit}, timeout=6.0)
    resp.raise_for_status()
    out: list[dict] = []
    for artist in resp.json().get("data", []):
        name = (artist.get("name") or "").strip()
        if name:
            out.append({"name": name, "image": artist.get("picture_small")})
    return out
