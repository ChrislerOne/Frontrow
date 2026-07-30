# Frontrow — design refresh prompt

Paste everything below the line into the Claude Design project
**"Perforated stub card prototype"** (`claude.ai/design/p/c84f19b7-b7ed-497a-b032-ae63e9ac058c`).
It assumes the existing project files `Frontrow.dc.html` + `Frontrow App.dc.html` and the
Nocturne design system stay in place — this is an update, not a restart.

---

Update this prototype so it matches what Frontrow actually became, and finish the parts
that were designed but never resolved. Keep Nocturne, keep the ticket-stub card, keep the
`Frontrow.dc.html` / `Frontrow App.dc.html` split and the screen + variant + device +
theme switchers. Every screen still needs mobile **and** desktop, dark **and** light.

## 1. The concert card changed — redesign it around this

The card is no longer about "new vs seen". Drop the **NEW stamp** and the **Mark seen /
torn stub / 62%-opacity Seen** state entirely, along with the `newTreatment` prop. Replace
them with:

- **Ticket bought** — the user marks shows they hold a ticket for. This is the card's
  highlight state: an accent ring, an accent "Ticket bought" line, and a filled toggle
  button. Unset the button reads **"Got a ticket"**. It must stay usable on a sold-out or
  cancelled show — you can hold a ticket for a show that later sold out.
- **Availability**, straight from the ticket source, as a tag on the card:
  `SOLD OUT` and `CANCELLED` (danger tone) and `NO TICKETS` (muted — listed but nothing on
  offer, e.g. pre-sale). These cards stay on the board, dimmed, with the ticket button
  degraded from "Tickets" to "Event page". A cancelled show has no ticket button at all.
  Design the case where a card is **both sold out and ticket-bought** — the highlight must
  win over the dimming.
- **Price** — a mono `FROM €52,60` line in the stub. Absent on anything not in stock.
- **Artist thumbnail** — a small round photo (56×56 source) next to every artist name.
  Fall back to a music-note monogram when the catalog has no picture. This reverses the
  brief's "typographic / no-image" position; the app has real artist photos now.
- "New" still exists as a *quiet* concept only (first seen in the last 14 days) — it drives
  a filter chip, not a stamp on the card.

## 2. The dashboard changed — redesign around this

- **Concerts are grouped by artist**, collapsed by default, sorted by each artist's next
  show. The group header carries: caret, artist thumbnail, artist name, and a summary line
  like `3 shows · from €52,60 · 1 sold out · 1 bought`, plus `NEXT · SA 12 SEP` on the
  right. Design it at mobile width, where that summary line has to truncate gracefully.
- **Quick-filter chips** replace the All/New segmented control: `All 5 · New 5 ·
  Tickets bought 1 · Sold out 2`, each with a live count, single-select, sitting next to
  the city filter.
- **A Calendar view**, toggled by a List/Calendar segmented control, sharing the same
  filters as the list. Month grid, prev/next/Today, shows placed on their date, ticket-
  bought ones accented, sold-out ones struck through, and a "DATE TBA" row underneath for
  undated shows. **This screen has never been designed — design it properly**, including
  its empty month, its mobile layout (a 7-column grid at 390px is tight — propose the right
  answer, an agenda list is a legitimate one), and how a day with 4+ shows behaves.
- **Multiple lists.** Frontrow is no longer one watchlist. There's a list switcher in the
  header showing the current list, its role (`owner` / `editor` / `viewer`), and an icon
  for "shared with me" vs "I'm sharing this"; a menu to switch lists and create one; and
  rename/delete actions. Design the switcher, the menu, and the empty "no lists" case.
- **The tracked-artists sidebar** no longer shows a bare count. Each row shows the artist
  thumbnail, the name, and a state: a count, or `No events planned`, or `Not checked yet`,
  or `Sold out` in danger tone. Design all four.

## 3. Designed but never finished — resolve these

- **Radius filter.** The filter popover has a Cities tab and a Radius tab ("Around
  {city}" / "Within {n} km") that was never specified beyond labels. Either design it
  properly — including what happens with no geodata — or cut it and say so.
- **Share dialog.** Two designed pieces were never resolved: the **scope** control
  ("Every upcoming show" vs "Only shows in {city}") and the optional **note** ("Say
  something", shown on the public page next to your name). Decide whether each survives.
  Also: the dialog now needs **email invites** (invite by address, with a role, plus a
  pending-invite list) alongside the links, and links come in two kinds — a public
  **view** link and an **editor** link that lets a signed-in person add artists. Design
  the whole dialog around both.
- **Profile.** The designed "Default city", "Sharing" section and "Danger zone — Remove
  all artists" were never resolved. Decide which are real and specify them; the Appearance
  and Session sections are already built.
- **Shared public page.** The design has an owner avatar, a possessive title ("Jonas's
  front row"), a summary line and the optional note. Confirm the final composition —
  the built page is plainer than the mock.
- **Toast actions.** Toasts were designed with actions ("Removed Portishead · Undo",
  and a "Retry" on the soft warning) that were never built. Keep them or cut them, and
  say which.
- **Logout.** The "Signing out…" interstitial → landing-with-confirmation flow was
  described but not drawn as a state.

## 4. Never built at all — I need these as standalone, self-contained HTML

These five are served by the auth proxy or as error pages, so they get **no app JS or
nav**. They must be single files that only need the Nocturne stylesheet inlined.

- **Landing / sign-in** — the "NOW SHOWING" marquee hero, "Know before the tickets go",
  Sign in with Google, the invite-only note, and the three variants: default, after
  sign-out, sign-in failed.
- **Access denied** — "This inbox isn't on the list", the address that was refused,
  Request access, Use a different account.
- **404** — "That page isn't on the bill."
- **500** — "Something broke backstage."
- **Offline** — "You're offline."

The copy above already exists in the prototype; carry it over.

## 5. Keep

The Nocturne tokens exactly as they are (they're vendored into the app as `nocturne.css`
and I don't want a re-theme). The perforated ticket-stub card. The mono metadata line.
Phosphor icons. The German-length discipline. The motion table, minus the stamp-press
and stub-tear entries, plus whatever the new highlight/calendar transitions need.

## 6. Deliver

Updated `Frontrow.dc.html` component/token sheet reflecting the new card states, chips,
group header, thumbnails and calendar cells; updated `Frontrow App.dc.html` screens with
their variants; the five standalone pages from §4; and microcopy for everything new.
Exportable HTML/CSS wherever you can — this gets hand-implemented.
