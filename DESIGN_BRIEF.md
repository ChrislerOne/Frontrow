# Frontrow — Visual Design Brief

A complete brief for a full visual redesign of **Frontrow**. Hand this whole document
to a design tool/designer. It contains the product context, the real data the UI shows,
every screen (existing and new), all required states, a recommended art direction, and a
deliverables checklist.

---

## 0. How to use this brief

**What to ask the designer to produce** (see the full checklist in §11):
mockups for every screen in §8 in **both mobile and desktop**, in **dark (primary) and
light**, plus a component sheet (§7) and design tokens (§5). The output will be
hand-implemented as **static HTML/CSS/JS** — so keep it buildable without a heavy framework.

**What's a requirement vs a suggestion:** §2–3 (product, data), §6 (states), §8 (screens),
§9 (voice), §10 (constraints) are **requirements** — the design must cover them. §4 (art
direction) is a **strong recommended point of view**; the designer may push it further or
propose an alternative, but must replace it with something equally specific — not a generic
template.

---

## 1. The one-line brief

Frontrow is a private, invite-only web app for a small group of friends to **track the
artists they want to see live and catch new concert announcements early**. The redesign
should feel like the anticipation of a great show — not like a SaaS dashboard.

---

## 2. Product context

- **What it does:** you add artists to a watchlist; a background job checks ticketing
  sources every 12h; new shows surface with a **NEW** flag. You can filter concerts by
  city, open the ticket link, mark a show as seen, and remove artists.
- **Who uses it:** ~2–20 invited people (friends), signed in with Google. Not public,
  not enterprise. No "growth funnel" — but there IS a public landing page for the
  sign-in moment and for sharing.
- **Where/how:** **mobile-first** — people check this on their phone, often in seconds
  ("anyone playing near me soon?"). Must be equally good on desktop.
- **Locale:** primarily German audience/venues; dates display in German locale. Design
  for longer German words and 24h time.
- **Current look (being replaced):** a single dark page, ~760px column, system font,
  indigo accent, green "NEW" pill. Functional but generic. The redesign replaces this.

---

## 3. Real content & data (design with these, not lorem ipsum)

Everything the UI can show today comes from these objects. Use realistic values.

**Artist**
- `name` — e.g. "Rammstein", "Bonobo", "Fontaines D.C."
- `event_count` — integer, number of tracked concerts for that artist

**Concert / Event**
- `artist` — the tracked artist's name
- `name` — the event/show title, e.g. "Rammstein — Europe Stadium Tour 2026"
- `start_date` — date + time, **or empty** → show "Date TBA"
- `city` — e.g. "Berlin", "Köln", "Hamburg" (may be empty)
- `venue` — e.g. "Olympiastadion", "Lanxess Arena" (may be empty)
- `link` — external "Tickets" URL (may be empty → no ticket button)
- `is_new` — boolean → drives the **NEW** treatment

**Cities** — a distinct list of cities across all tracked concerts (feeds the filter).

**Sample rows to use in mockups**
```
Fontaines D.C.  · Fri 14 Nov 2026, 20:00 · Palladium, Köln          [NEW] [Tickets]
Bonobo          · Sat 22 Nov 2026, 19:30 · Columbiahalle, Berlin          [Tickets]
Rammstein       · Date TBA               · Olympiastadion, München  [NEW]
```

**Actions the UI triggers:** add artist (runs an immediate check), remove artist,
mark concert seen (clears NEW), manual "refresh now", filter by city. Adding an artist
can return either "Found N concerts" or a soft warning ("Couldn't reach the source —
we'll retry automatically").

---

## 4. Recommended art direction (a real point of view)

**Concept: "The dark room, lit by the stage — and the ticket stub in your pocket."**
Frontrow lives in the world of live music: dim venues, marquee signage, tour posters, and
the paper ticket stub. Lean into that vernacular instead of a neutral UI kit.

**Why this and not the usual:** the easy defaults here would be a cool near-black page with
one acid accent, or a generic card dashboard. We go **warm** (a dimmed-room dark, not
blue-black), use **marquee amber** as the brand and a **hot magenta "stamp"** for NEW, and
make the **concert card a ticket stub** — a motif no generic template carries.

### Palette (starting tokens — refine, keep the roles)
Dark is primary; a light theme is required (§6).

| Role | Hex (dark) | Use |
|---|---|---|
| `bg` (the room) | `#15120E` | page background, warm near-black |
| `surface` (the stub) | `#1E1A14` | cards, sheets, inputs |
| `surface-2` | `#272219` | raised/hover surface |
| `hairline` | `#332C22` | borders, perforations, dividers |
| `text` | `#F5EFE4` | primary text (marquee-bulb off-white) |
| `text-muted` | `#A99C87` | secondary/meta text |
| `brand` (marquee amber) | `#F4A93C` | logo, primary buttons, key highlights |
| `stamp` (NEW / energy) | `#FF4D6D` | the NEW stamp, live/energy accents |
| `success` | `#46C46A` | confirmations (use sparingly) |
| `danger` | `#E4483A` | destructive actions, errors |

Spend the boldness on **amber + the magenta stamp**; keep everything else quiet.

### Type (3 deliberate roles)
- **Marquee / display** — condensed, all-caps, poster energy, used with restraint for the
  wordmark and big hero moments. Suggestion: *Bebas Neue* (or a condensed grotesque).
- **Headings / UI** — *Space Grotesk* (geometric, a little character, very readable).
- **Body** — *Hanken Grotesk* (clean humanist grotesque; avoid defaulting to Inter).
- **Data / mono** — *Space Mono* for ticket-stub metadata: dates, times, venue codes,
  serial-style details. This mono treatment is part of the identity.

### Signature element
**The concert card as a ticket stub:** a main panel (artist + show) and a perforated
"stub" (date/time + city·venue in mono + the Tickets action). The **NEW** state is a
diagonal magenta **stamp**, not a pill. Marking a show "seen" reads like *tearing the stub*.
Make this card the thing the app is remembered by; keep the rest disciplined.

### Motion (restrained, respect `prefers-reduced-motion`)
- Wordmark: a barely-there marquee shimmer on load (optional, subtle).
- Card: gentle lift on hover; the NEW **stamp** presses in on first appearance.
- "Mark seen": a quick stub-tear/settle.
- Page transitions and list loads: soft fade/slide, nothing bouncy.

---

## 5. Design system / foundations (requirements)

- **Color:** deliver the token set in §4 as CSS custom properties, with **light-theme
  equivalents** for every role. Meet **WCAG AA** contrast for text and UI (verify amber
  and magenta on both themes — they often fail on light).
- **Type scale:** define a clear scale (e.g. display / h1 / h2 / body-lg / body / meta /
  mono) with sizes, weights, line-heights, letter-spacing. Mobile and desktop sizes.
- **Spacing:** an explicit scale (e.g. 4/8/12/16/24/32/48). Consistent card padding.
- **Radii & edges:** pick a radius language and hold it (the ticket motif may mix soft
  corners with a notched/perforated edge — define both).
- **Elevation:** 1–2 shadow levels max on dark; keep it subtle (dark rooms don't glow).
- **Iconography:** one icon set/style (line vs solid), sized to the type scale. Icons for:
  add, remove/trash, ticket, share, city/location pin, calendar, refresh, filter, profile,
  logout, external-link, check/seen.
- **Layout grid:** define container width(s) and a responsive grid. The single-column
  reading feel can stay, but specify how lists reflow to 2+ columns on wide screens.
- **Imagery:** the app has no artist photos today. Decide the position: either a
  **typographic/no-image** system (recommended — leans into the poster/marquee identity)
  or an **artist-avatar** system with a strong placeholder (monogram/initials in brand
  colors). Specify whichever you choose consistently.

---

## 6. Global patterns & states (requirements — design each)

- **Loading:** skeletons for the artist list and concert list; a busy state for the
  "add artist" action (it runs a live check that can take a few seconds); a page-level
  first-load state.
- **Empty states (write real copy, §9):**
  - No artists tracked yet → invite to add the first artist.
  - Artists tracked but no concerts found yet → reassure it's watching.
  - City filter with no matches → offer to clear the filter.
  - Shared list that's empty.
- **Error & warning states:**
  - Add-artist soft warning: "Couldn't reach the source right now — we'll keep trying."
  - Action failure (remove/mark-seen) → inline or toast, with retry.
  - Full-page errors: 404, 500, and an **offline** state.
- **Success feedback:** toast/inline for "Tracking {artist} — found N concerts",
  "Removed {artist}", "Marked as seen", "Link copied".
- **Toasts/notifications:** define the component and its placement (mobile + desktop).
- **Focus & keyboard:** visible focus rings on everything interactive; logical tab order;
  Enter submits the add-artist field.
- **Responsive:** mobile-first; define ≥1 breakpoint behavior for lists, header, filters.
- **Theme:** dark (default) + light; respect `prefers-color-scheme`; a manual toggle
  lives in Profile/Settings.
- **Reduced motion:** every animation has a still fallback.

---

## 7. Components (design with all states: default / hover / active / focus / disabled / loading)

- **Buttons:** primary (amber), secondary/ghost, destructive (danger), icon-only.
- **Text input** (add artist) + inline validation/empty guard.
- **Select / filter** (city filter) — and its empty/"all cities" state.
- **Concert card (the ticket-stub signature)** — with and without NEW, with and without a
  ticket link, with "Date TBA", with long German venue names.
- **Artist row** — name, concert count, remove control; hover/active.
- **NEW stamp** and any secondary badges (e.g. "TBA", city tag).
- **Header / top bar** — wordmark, and (signed-in) a profile menu with logout.
- **Profile menu / dropdown.**
- **Avatar** (from Google) with initials fallback.
- **Modal / dialog** — used for "remove artist?" confirm and the share dialog.
- **Toast / notification.**
- **Empty-state block** (icon/illustration + headline + action).
- **Tabs or segmented control** if used (e.g. "All / New" concerts).

---

## 8. Screens & flows

For each screen: purpose · key elements · states · notes. Screens marked **(new)** don't
exist yet; screens with **⚙︎ backend** need server work to be fully functional (design them
anyway — note the dependency).

### 8.1 Landing / sign-in page (new · public)
- **Purpose:** the first thing an unauthenticated visitor sees; explains Frontrow in one
  breath and offers **Sign in with Google**. Also the destination after logout.
- **Elements:** wordmark; a hero that embodies the concept (recommended: a **"NOW SHOWING"
  marquee/board** listing a few example shows); one-line value prop; **Sign in with Google**
  button; a quiet "invite-only" note; footer.
- **States:** default; post-logout ("You're signed out"); an error variant if sign-in fails.
- **Notes:** invite-only, so no "sign up". The sign-in button starts the Google flow
  (implementation: links to the auth start path). Keep it fast and confident.

### 8.2 Access-denied / not-invited page (new · public) ⚙︎
- **Purpose:** shown when someone signs in with a Google account that **isn't on the
  invite list** (today this is a raw 403). Make it human.
- **Elements:** calm headline ("This inbox isn't on the list"), a sentence explaining it's
  invite-only, a **"Request access"** mailto/link to the owner, and a "Sign in with a
  different account" link.
- **Notes:** this replaces the default auth-proxy 403 page (customizable). Friendly, not
  a dead end.

### 8.3 Home / dashboard (redesign of the current app · authed)
- **Purpose:** the core screen — watchlist + upcoming concerts.
- **Elements:**
  - Header: wordmark + profile menu.
  - **Add artist**: prominent input + primary button; runs an immediate check.
  - **Tracked artists**: list of artist rows (name · concert count · remove).
  - **Upcoming concerts**: the ticket-stub cards, sorted by date; **city filter**;
    "Refresh now"; optional "All / New" toggle.
  - Per card: artist, show name, date/time (or TBA), venue·city, NEW stamp, Tickets link,
    "mark seen".
- **States:** first-load skeleton; adding-artist busy; empty (no artists / no concerts);
  filtered-empty; the add-artist soft warning; success toasts.
- **Responsive:** single strong column on mobile; concerts may go multi-column on desktop.

### 8.4 Concert detail (new · optional · authed)
- **Purpose:** an expanded view of one show (tap a card). Useful on mobile.
- **Elements:** big date/time, venue + city, artist, show title, prominent Tickets CTA,
  "mark seen", back. Room for future fields (price, on-sale date, map).
- **Notes:** optional; if skipped, the card's Tickets link is the primary action.

### 8.5 Profile (new · authed) ⚙︎
- **Purpose:** who you're signed in as + personal settings + sign out.
- **Elements:** Google **avatar, name, email**; **theme toggle** (dark/light/system);
  **default city** preference (optional); a link to **your shared lists** (§8.6);
  **Sign out**; a small "Danger zone" (e.g. remove all tracked artists) if desired.
- **Notes:** identity (email/name) is available from the auth layer; avatar may need
  extra config. Preferences beyond theme need backend storage — mark as phase 2 if needed.

### 8.6 List sharing (new · authed) ⚙︎
- **Purpose:** let a user share their upcoming-concerts list with someone.
- **Two parts to design:**
  1. **Share dialog** (from dashboard/profile): explains what gets shared (read-only
     upcoming concerts), a **generated share link** with **Copy**, a toggle to
     **enable/revoke** the link, and optional scope (all vs a single city).
  2. **Shared-list view** (new · **public**, read-only): a branded page showing the
     shared concerts as ticket-stub cards, no add/remove/controls, a header that says
     whose list it is, and a soft "Frontrow" sign-in CTA for visitors. Include an empty
     state.
- **States:** link disabled (default) → enabled → copied → revoked; expired/invalid link
  page; empty shared list.
- **Notes:** needs a tokenized public route that bypasses login for that page only. Design
  it to feel intentional, not like the logged-in app with buttons removed.

### 8.7 Settings (new · optional · authed)
- Can be merged into Profile. Covers theme, default city, and (future) notification
  cadence. Only build a separate screen if Profile gets crowded.

### 8.8 Logout (flow, not a screen · authed)
- Triggered from the profile menu. Design the menu item and the resulting state: a brief
  "Signing out…" then land on §8.1 with a "You're signed out" confirmation.

### 8.9 System / error pages (new · public + authed)
- **404** (wrong URL), **500** (something broke), **offline** (no connection). Give each
  a headline, one helpful sentence, and a way back — in the Frontrow voice, on-brand.

### Primary flow (for reference)
`Landing → Sign in with Google → (on allowlist?) → Dashboard` · off-list → `Access-denied`.
Within the app: `Add artist → immediate check → toast` · `Filter by city` ·
`Open Tickets` · `Mark seen (clears NEW)` · `Remove artist (confirm)` ·
`Share → link → shared view` · `Profile → theme / sign out`.

---

## 9. Content & voice

- **Voice:** a fellow music fan — warm, concise, a little excited, never corporate. Sentence
  case. Active voice. Specific over clever.
- **Naming stays consistent through a flow:** the button that says "Track" leads to a toast
  that says "Tracking {artist}"; "Sign in with Google" → signed-in state; "Share" → "Link
  copied".
- **Errors give direction, don't apologize or blame:** e.g. *"Couldn't reach the ticket
  source right now — Frontrow will keep checking and show new shows automatically."*
- **Empty states invite action:** e.g. *"No artists yet. Add one and Frontrow starts
  watching for shows."*
- **Provide real microcopy** for: primary buttons, the add-artist placeholder, all empty
  states, the soft warning, toasts, the access-denied page, the share dialog, and the
  error pages. Design for **German-length** strings (they run ~30% longer).

---

## 10. Implementation constraints & notes (so the design is buildable)

- **Front end is static HTML/CSS/JS** served by a small backend; **no mandatory heavy
  framework.** Favor a design that maps cleanly to hand-written HTML/CSS with CSS custom
  properties for tokens. Custom fonts via web-font files are fine.
- **Auth is handled by an auth proxy in front of the app** (Google sign-in + email
  allowlist). Practical implications for the designer:
  - The **sign-in and access-denied pages** are effectively the auth layer's pages — they
    can be replaced with custom branded templates, so design them as **standalone HTML**
    (they won't have the app's JS/nav).
  - The **shared-list view** and **landing** must work as **public** pages (no login).
  - Inside the app, the logged-in user's **email/name** is available; **avatar** may need
    a small config addition.
- **Dark is the default theme**; light is required and must pass contrast.
- **Deliver tokens as CSS variables** and components as plain, semantic HTML where possible.

---

## 11. Deliverables checklist (what to ask Claude design to produce)

- [ ] **Design tokens** (§5): full color set (dark + light), type scale, spacing, radii,
      shadows — as CSS custom properties.
- [ ] **Type & color specimen** sheet showing the chosen typefaces in all roles.
- [ ] **Component sheet** (§7) with every state.
- [ ] **Screens** (§8), each in **mobile + desktop**, **dark + light**:
      Landing/sign-in · Access-denied · Dashboard (with empty, loading, and filled states) ·
      Concert detail (optional) · Profile · Share dialog + Shared-list view · Logout state ·
      404 / 500 / offline.
- [ ] The **ticket-stub concert card** worked out fully (NEW stamp, no-link, Date-TBA,
      long venue name, seen/tear interaction).
- [ ] **Microcopy** for every button, empty state, error, and toast (§9), German-length safe.
- [ ] **Motion notes** (§4) with reduced-motion fallbacks.
- [ ] Ideally, **exportable HTML/CSS** (or a close spec) for at least the dashboard and the
      ticket-stub card, since the app is hand-implemented.

---

## 12. Out of scope / future (mention, don't design deeply)

- Multi-user data separation (today one shared watchlist; per-user lists are future).
- Email/push notifications for new shows (today it's the in-app NEW flag).
- Ticket price / on-sale date / maps on concert cards (fields don't exist yet).
- Artist photos (decide the image position in §5; real photos are a later data problem).
