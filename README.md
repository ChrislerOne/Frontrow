# Frontrow

Track artists you want to see live. A background job polls Eventim every 12 hours
and surfaces new concerts for the artists on your list.

## Stack

- **FastAPI** — web API + serves the frontend
- **SQLite + SQLAlchemy** — your own copy of the data (the site never calls Eventim live)
- **APScheduler** — runs the scrape every 12 hours
- **Playwright (headless Chromium)** — drives a real browser to get past Eventim's Akamai bot protection
- **Vanilla HTML/JS** frontend

## Architecture

```
[frontend] --reads--> [SQLite DB] <--writes-- [12h scheduler job]
                                                     |
                                          [adapters/eventim.py]  <- only Eventim-specific code
```

The DB is the source of truth. Adding an artist also triggers one immediate scrape
so the list isn't empty for 12 hours. "New concert" = an Eventim `productId` not yet
in the `events` table.

## Run

```bash
cd concert-tracker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium    # one-time: downloads the headless browser
uvicorn app.main:app           # do NOT use --reload: it starts the scheduler twice
```

Open http://127.0.0.1:8000

## Deploy on Coolify (Hetzner)

Files provided: `Dockerfile`, `docker-compose.yml`, `.dockerignore`.

1. Push this directory to a Git repo Coolify can reach.
2. In Coolify: **New Resource → Docker Compose**, point it at the repo. It picks up
   `docker-compose.yml` and builds the `Dockerfile` (multi-arch base image, builds
   fine on Hetzner's amd64).
3. Set a domain — Coolify's proxy handles the domain + Let's Encrypt SSL in front of
   the container's port 8000.
4. The named volume `concert-data` (mounted at `/data`) persists `tracker.db` across
   redeploys. Don't remove it.
5. **Add Basic Auth** in Coolify if the domain is public — the app itself has no auth,
   so anyone could otherwise add artists and trigger scrapes.

Verified locally: image builds against `playwright==1.61.0`, Chromium launches inside
the container, and a scrape stored 25 events with a clean log (no sandbox/GPU noise).

**The one thing this can't verify locally:** from a Hetzner **datacenter IP**, Akamai
is far more likely to block the Eventim scrape than from your home IP. If the deployed
app returns nothing, that's why — route the browser through a residential proxy, or
switch to a `TicketmasterAdapter`. See the Eventim caveat below.

## API

| Method | Path                       | Purpose                          |
|--------|----------------------------|----------------------------------|
| POST   | `/api/artists`             | Track an artist `{ "name": … }`  |
| GET    | `/api/artists`             | List tracked artists             |
| DELETE | `/api/artists/{id}`        | Untrack an artist                |
| GET    | `/api/events?only_new=true`| List concerts (optionally new)   |
| POST   | `/api/events/{id}/seen`    | Clear the NEW flag               |
| POST   | `/api/scrape`              | Trigger a scrape immediately     |

## Known caveats (read these)

- **Eventim is behind Akamai Bot Manager.** Plain HTTP gets a persistent
  `403 Access Denied` (verified). The adapter works around this by driving a real
  headless Chromium: it loads eventim.de to establish a browser session, then calls
  the JSON API via an in-page `fetch()` that carries the browser's fingerprint and
  Akamai cookies. **Consequences you're signing up for:**
  - **Heavy & slow.** Every scrape launches Chromium (~1–2s startup + RAM). Fine at a
    12h cadence with a modest artist list; not fine at high frequency.
  - **Fragile.** If Akamai tightens (e.g. starts blocking headless Chromium), the
    `fetch` returns `403` → `EventimBlockedError`. You'd then need stealth plugins,
    `headless=False` + a virtual display, or residential proxies.
  - **Still ToS-violating.** This is unofficial use of Eventim's internal API.
- **The clean alternative** is a `TicketmasterAdapter` against the official, free,
  self-serve [Discovery API](https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/)
  (covers DE, no browser, no blocking) — same `SourceAdapter` interface, ~1 file.
- **Field mapping** (`city`/`venue` from `liveEntertainment.location`) is verified
  against live data but lives in one place (`_to_concert`) if Eventim's shape shifts.
- **Relevance filtering** (`_features_artist`): Eventim's `search_term` is fuzzy, so
  results are kept only if the searched name matches an entry in the product's
  `attractions[]` list (normalized for case/whitespace). This keeps headline shows
  and festivals the artist actually plays, and drops incidental text matches. Tradeoff:
  a show that lists the artist only in its title (e.g. an unlisted support slot) is
  dropped. To also match on event name, relax the check in `_features_artist`.
- **Field mapping is best-effort.** `city` / `venue` come from
  `typeAttributes.liveEntertainment.location`; if Eventim's shape differs, adjust
  `_to_concert()` in the adapter — that's the one place to change.
- **No multi-user / auth yet.** Every artist in the DB is "tracked" by the single
  implicit list. To add users: a `users` table + a `user_artist` join, then filter
  `/api/events` by the requesting user.
- **The DB is a disposable cache.** Everything in `tracker.db` is re-scrapeable from
  Eventim. There's no migration tooling, so after any model change (e.g. a `UNIQUE`
  constraint) just delete `tracker.db` and let it rebuild on the next add/refresh.
- **Festivals are stored once per tracked artist who plays them** (unique on
  `product_id` + `artist_id`). If you track several artists in the same festival
  lineup, that festival appears once per artist. To collapse it to a single row
  showing all your artists, switch `Event` to a many-to-many model (events +
  `artist_event` join table).
- **Existing events aren't updated**, only new ones inserted. If a concert's date
  changes, add an upsert in `scrape_artist()`.

## Adding another source later

Implement the `SourceAdapter` protocol in `app/adapters/base.py` (one method:
`fetch_concerts(artist_name) -> list[ConcertResult]`), then point `scraper.py` at it.
That's the whole extension surface.
