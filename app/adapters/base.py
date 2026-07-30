from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class ConcertResult:
    product_id: str
    name: str
    start_date: datetime | None
    city: str | None
    venue: str | None
    link: str | None
    status: str | None = None      # source's own wording, e.g. "Available" / "SoldOut"
    in_stock: bool | None = None
    price: float | None = None     # cheapest listed ticket
    currency: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class SourceAdapter(Protocol):
    name: str

    def fetch_concerts(self, artist_name: str) -> list[ConcertResult]:
        ...
