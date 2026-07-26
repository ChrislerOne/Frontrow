from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
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


# ── Catalog + scrape cache (disposable, re-scrapeable) ──────────────────────
class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

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
