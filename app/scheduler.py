from apscheduler.schedulers.background import BackgroundScheduler

from .database import SessionLocal
from .geocode import backfill_event_coords
from .scraper import scrape_all

scheduler = BackgroundScheduler()


def _scheduled_scrape() -> None:
    db = SessionLocal()
    try:
        results = scrape_all(db)
        new_total = sum(results.values())
        # Eventim covers ~97% of venues; this tops up the rest a few at a time.
        located = backfill_event_coords(db)
        print(f"[scheduler] scraped {len(results)} artists, {new_total} new concerts, "
              f"{located} venues located")
    finally:
        db.close()


def start_scheduler() -> None:
    scheduler.add_job(
        _scheduled_scrape,
        trigger="interval",
        hours=12,
        id="eventim_scrape",
        replace_existing=True,
    )
    scheduler.start()
