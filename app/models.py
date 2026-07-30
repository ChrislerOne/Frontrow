from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── People ──────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # Preferred city; the dashboard opens filtered to it. NULL = show every city.
    default_city: Mapped[str | None] = mapped_column(String, nullable=True)


# ── Catalog + scrape cache (disposable, re-scrapeable) ──────────────────────
class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # NULL until the first successful scrape. Lets the UI tell "we looked and there's
    # nothing" apart from "we haven't looked yet / the source was blocked".
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Thumbnail from the same catalog that powers the add-artist autocomplete.
    image: Mapped[str | None] = mapped_column(String, nullable=True)

    events: Mapped[list["Event"]] = relationship(
        back_populates="artist", cascade="all, delete-orphan"
    )


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("product_id", "artist_id", name="uq_product_artist"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[str] = mapped_column(String, index=True)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id"))
    name: Mapped[str] = mapped_column(String)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    venue: Mapped[str | None] = mapped_column(String, nullable=True)
    link: Mapped[str | None] = mapped_column(String, nullable=True)
    # Legacy: "new" is now computed per-user via EventSeen. Kept (unused) so the
    # schema change stays additive — no destructive migration.
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Availability as last reported by the source. status ∈ {Available, SoldOut,
    # Cancelled}; NULL on rows stored before availability was tracked, which reads as
    # "unknown" — never as sold out. price is the cheapest ticket the source lists.
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    in_stock: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Best known position, plus how precise it is. Eventim's geoLocation turns out to be
    # the CITY centroid, not the venue — every Berlin show came back on the same point —
    # so venue precision has to be geocoded separately. geo_source is one of:
    #   "eventim-city"  — city centroid from the source
    #   "venue"         — real venue point, geocoded once and cached
    #   "venue-unknown" — asked OSM for the venue, it doesn't know it; city point stands
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_source: Mapped[str | None] = mapped_column(String, nullable=True)

    artist: Mapped["Artist"] = relationship(back_populates="events")


# ── Durable user data ───────────────────────────────────────────────────────
class ArtistList(Base):
    """A user-owned list of artists. Private by default; shareable via ShareLink."""

    __tablename__ = "lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # Optional line shown at the top of the public share page. Belongs to the list, not
    # to a single link — every link renders the same page.
    share_note: Mapped[str | None] = mapped_column(String, nullable=True)

    owner: Mapped["User"] = relationship()
    members: Mapped[list["ListMember"]] = relationship(
        back_populates="list", cascade="all, delete-orphan"
    )
    artists_assoc: Mapped[list["ListArtist"]] = relationship(
        back_populates="list", cascade="all, delete-orphan"
    )
    shares: Mapped[list["ShareLink"]] = relationship(
        back_populates="list", cascade="all, delete-orphan"
    )


class ListMember(Base):
    """A user's access to a list. role ∈ {owner, editor, viewer}."""

    __tablename__ = "list_members"
    __table_args__ = (UniqueConstraint("list_id", "user_id", name="uq_list_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("lists.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String, default="viewer")
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    list: Mapped["ArtistList"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship()


class ListArtist(Base):
    """Membership of an artist in a list (many-to-many)."""

    __tablename__ = "list_artists"
    __table_args__ = (UniqueConstraint("list_id", "artist_id", name="uq_list_artist"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("lists.id"))
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id"))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    list: Mapped["ArtistList"] = relationship(back_populates="artists_assoc")
    artist: Mapped["Artist"] = relationship()


class ShareLink(Base):
    """A token that grants access to a list. role ∈ {viewer, editor}."""

    __tablename__ = "share_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("lists.id"))
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    role: Mapped[str] = mapped_column(String, default="viewer")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    list: Mapped["ArtistList"] = relationship(back_populates="shares")


class ListInvite(Base):
    """A pending invite by email for someone who hasn't logged in yet. Resolved into a
    ListMember the first time that email signs in. role ∈ {editor, viewer}."""

    __tablename__ = "list_invites"
    __table_args__ = (UniqueConstraint("list_id", "email", name="uq_list_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("lists.id"))
    email: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String, default="editor")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class EventSeen(Base):
    """Per-user 'seen' state, keyed by the stable Eventim product_id (not event.id)
    so it survives a cache rebuild."""

    __tablename__ = "event_seen"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_user_product"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[str] = mapped_column(String, index=True)
    seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ArtistSuggestion(Base):
    """Artist names cached from an external catalog (Deezer) to power the add-artist
    autocomplete. Not linked to tracking — just a growing name index."""

    __tablename__ = "artist_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    image: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, default="deezer")
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Place(Base):
    """Permanent cache of anything we've had to geocode: venues Eventim gave no
    coordinates for, and the home city a user picks. Venues and cities don't move, so a
    resolved row is never looked up again — which is also what Nominatim's usage policy
    demands. A row with NULL coordinates is a negative result, kept deliberately so a
    place that can't be found isn't retried on every scrape."""

    __tablename__ = "places"

    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(String, unique=True, index=True)
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String, default="nominatim")
    resolved_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class EventAttending(Base):
    """Per-user 'I'm going / have a ticket' marker, keyed by the stable product_id."""

    __tablename__ = "event_attending"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_user_product_att"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
