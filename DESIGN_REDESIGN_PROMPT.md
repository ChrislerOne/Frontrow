# Frontrow — total visual redesign brief

Paste everything below the line into Claude Design. Start a **new** project; this is not a
revision of "Perforated stub card prototype".

This supersedes `DESIGN_BRIEF.md` (the original, written before the app existed in this
form) and the visual half of `DESIGN_REFRESH_PROMPT.md` (nearly all of which is now built).

---

I want a total visual redesign of **Frontrow**, and I want **three distinct directions to
choose between** — not one direction iterated. Nothing about the current look is sacred.

## 0. What I'm asking for, concretely

Three named art directions. Each one must include:

1. **A concept** — a name and one paragraph explaining the point of view, in terms of this
   product, not in terms of design trends.
2. **Tokens** — full colour set for dark **and** light as CSS custom properties, type
   scale with roles, spacing scale, radii, elevation. Both themes must pass WCAG AA for
   text and UI.
3. **Typography** — the typefaces and what each role is for. Justify them. Do not reach
   for Inter, Helvetica, or `system-ui` as a default: the previous round of this project
   was briefed to avoid Inter and used Inter for both headings and body anyway, which is
   part of why I'm starting over.
4. **A signature element** — the one component the app is remembered by, worked out fully.
5. **Motion notes**, each with a `prefers-reduced-motion` still fallback.

Then render **the same two proof screens in all three directions** so I can compare them
directly:

- **The dashboard, filled** — desktop and mobile, dark and light.
- **A component + state sheet** — every state listed in §3.

Finish with **a recommendation**: which direction you'd ship and why, and what you'd graft
from the runners-up.

**Diversity requirement.** The three must not be siblings. At least one must abandon the
"ticket stub" metaphor completely. At least one must propose a signature element that
isn't a physical-object metaphor at all. If two directions could share a stylesheet with
different variables, they're one direction — replace one.

## 1. What Frontrow is

A private, invite-only web app for a small group of friends (~10 people, Google sign-in)
to **track the artists they want to see live and catch new shows early**. A background job
checks Eventim every 12 hours. You keep lists of artists, see their upcoming concerts,
mark the ones you've bought tickets for, and share a list with a friend.

It should feel like the anticipation of a great show. Not a SaaS dashboard, not a
ticketing site.

Mobile-first — it gets opened on a phone for ten seconds ("anyone playing near me?") —
and equally good on a wide desktop.

## 2. What's actually on screen today

This is the real inventory. The design has to cover all of it.

### Top chrome
- Sticky bar: wordmark, "refresh now" icon button, avatar + menu (Profile & settings /
  Share this list / Sign out).
- **List switcher**: current list name, a role chip (`owner` / `editor` / `viewer`), an
  icon distinguishing "shared with me" from "I'm sharing this", a dropdown to switch or
  create a list, and rename / delete / share actions.

### Add an artist
- Text input with autocomplete (each suggestion is a round artist photo + name), a primary
  "Track" button, a hint line, a busy state (the add runs a live scrape), and a soft
  warning box when the ticket source can't be reached.

### Left column — tracked artists
Rows of: round artist photo (56×56 source, monogram fallback), name, and exactly one
status: a **count**, or **"No events planned"**, or **"Not checked yet"**, or
**"Sold out"**. Plus a remove control.

### Right column — the concerts
- Heading, a **three-way view switch: List / Calendar / Map**, "Refresh now".
- **Quick filter chips with live counts**: `All 12` · `New 4` · `Tickets bought 2` ·
  `Sold out 3`. Single-select.
- **Filter popover** with two tabs: *Cities* (checklist with per-city counts) and *Radius*
  (distance presets around a home city, plus "use my location").
- **List view** — collapsible groups, one per artist, sorted by each artist's next show:
  - Group header: disclosure caret, artist photo, artist name, a summary line
    (`3 shows · from 52,60 € · 1 sold out · 1 bought`), and `NEXT · SA 12 SEP`.
  - Group body: a grid of **event cards**. Each card carries: a serial-ish code, an
    availability tag, the event title, a "Ticket bought" line, a date line, a venue · city
    line, a "from 52,60 €" price, and two actions — a **ticket-bought toggle**
    (`Got a ticket` ⇄ `Ticket bought`) and a link (`Tickets` / `Event page` /
    `No link yet`).
- **Calendar view** — month grid, prev / next / Today, shows sitting on their dates,
  bought-ticket ones emphasised, sold-out ones struck through, and a `DATE TBA` row
  beneath for undated shows. A 7-column grid is tight at 390px — solve that deliberately;
  an agenda list on mobile is a legitimate answer.
- **Map view** — Leaflet with OpenStreetMap tiles. Custom pins in three states (normal /
  ticket bought / unavailable), popups with date, venue, price and ticket link, an
  optional home marker with a radius circle, and a line saying how many shows couldn't be
  placed.
- **Empty states**: no artists yet · nothing announced yet · no shows match this filter.
- **Toasts**, bottom-centre, dismissible, with an optional action button (`Undo`).

### Profile
Avatar, name, email · Appearance (dark / light / system) · Default city · Session
(sign out) · **Danger zone** (remove all artists).

### Dialogs
- Confirm (remove artist, delete list, clear list) and prompt (new list, rename).
- **Share dialog** — the busiest surface in the app: a list of existing links with role
  chips, copy and revoke controls; buttons to create a view link or an editor link; a
  people list with roles and removal; pending email invites; an invite-by-email form; a
  280-character "say something" note; and a "preview the public page" link.
- A **"Signing out…"** full-screen state.

### Standalone pages (no app CSS, no app JS — see §4)
- **Landing / sign-in** — the only public marketing surface. Currently a hero
  ("Know before the tickets go"), a "Now showing" sample board of upcoming shows, a
  Sign in with Google button, an invite-only note. Variants: default, after sign-out,
  sign-in failed.
- **Access denied** — signed in with Google but not on the invite list.
- **404 · 500 · offline.**
- **Public share page** — read-only, branded: whose list it is, an optional quoted note,
  the concert cards with no controls, and a soft "get your own Frontrow" close. Plus
  empty and revoked-link states.

## 3. States that must survive the redesign

Design each one; they carry the product's meaning.

- **Availability**, straight from the ticket source: `available` · `sold out` ·
  `cancelled` · `no tickets` (listed but nothing on offer) · `unknown` (older rows —
  must read as normal, never as unavailable).
- **Ticket bought** — the app's one positive, personal state. It must read as *good news*,
  and it must still read clearly **on a sold-out card**, because you can hold a ticket for
  a show that later sold out. Getting this pair right is the single most important
  interaction in the app.
- **New** — first seen in the last 14 days. Quiet; it drives a filter, and I do **not**
  want a loud "NEW" stamp back.
- **Permissions** — owner / editor / viewer, and shared-with-me vs sharing-out.
- Loading skeletons, the add-artist busy state, and the soft "couldn't reach the source"
  warning.

## 4. Hard technical constraints

These are not negotiable; they're what makes the design buildable.

- **Plain static HTML / CSS / JS.** No framework, no build step. I hand-implement.
- **All tokens as CSS custom properties in one stylesheet** that wholesale replaces the
  current one. Components as semantic HTML.
- **Dark is the default, light is required**, both AA. Honour `prefers-color-scheme`, with
  a manual override applied as an attribute on `<html>`.
- **Five pages must be fully standalone** — inline CSS, no shared stylesheet, no CDN font,
  no icon font. Two of them are rendered by the auth proxy (which has no access to the
  app's assets) and the error pages have to render when the app or the network is down.
  So: every direction needs a version of its identity that survives with **zero external
  requests**. If a direction depends on a web font, say what those five pages do instead.
- **The map is OpenStreetMap's standard tiles, which only exist in a light style.** Each
  direction must state how the map reads in dark mode. (Today: the tile images are
  CSS-inverted and desaturated.) Attribution must stay visible — the tile policy requires
  it.
- **One icon set.** Currently Phosphor. If a direction wants different icons, name a set
  that's available as a web font or inline SVG.
- **German content.** Venue and city names run long — "Kulturzentrum Schlachthof",
  "Mitsubishi Electric Halle", "Zusatzvorstellung". Dates are German short form with 24h
  time. Prices are `52,60 €`. Every direction must be stress-tested against these, and
  say what truncates first — never the artist's name.
- **Real artist photography exists** (round thumbnails, with a monogram fallback for
  artists the catalog doesn't know). The original brief assumed a typographic, image-free
  system; that's no longer true, so take a position on how photos sit in the design.
- Scale: 5–20 artists and 30–80 events per list. Dense enough that a spacious card grid
  needs a real answer for the long tail.

## 5. What I'm dropping — don't preserve any of it

The current system is called Nocturne and I want it gone: a single blurple accent
(`#9184d9`), Inter for both headings and body, 8px radii, a near-neutral dark ground with
1px hairline shadows, mono metadata lines, `FR-1209-BER` serial codes, and the perforated
ticket-stub card.

What I want kept is **behavioural, not visual**: the layout logic, the information
density, every state in §3, and the copy — which is deliberate and in the app's voice
(warm, concise, a fellow music fan; "No artists yet. Add one and Frontrow starts watching
for shows.", "Couldn't reach the ticket source right now — Frontrow will keep checking.",
"That page isn't on the bill."). Improve the copy where a new direction demands it, but
don't turn it corporate.

## 6. Deliverables

- Three directions as above, each self-contained enough to implement from.
- The two proof screens per direction, mobile + desktop, dark + light.
- A component + state sheet per direction covering §3.
- Tokens as CSS custom properties, ready to replace the current stylesheet.
- Exportable HTML/CSS wherever possible — this gets hand-built, so a close spec beats a
  pretty picture.
- Your recommendation, with reasoning.
