from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
    # A festival's productId can be reached via several tracked artists, so the same
    # event is stored once per artist who plays it — unique on the pair, not productId.
    __table_args__ = (UniqueConstraint("product_id", "artist_id", name="uq_product_artist"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[str] = mapped_column(String, index=True)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id"))
    name: Mapped[str] = mapped_column(String)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    venue: Mapped[str | None] = mapped_column(String, nullable=True)
    link: Mapped[str | None] = mapped_column(String, nullable=True)
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    artist: Mapped["Artist"] = relationship(back_populates="events")
