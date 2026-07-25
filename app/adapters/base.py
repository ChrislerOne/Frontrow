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


class SourceAdapter(Protocol):
    name: str

    def fetch_concerts(self, artist_name: str) -> list[ConcertResult]:
        ...
