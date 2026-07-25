from apscheduler.schedulers.background import BackgroundScheduler

from .database import SessionLocal
from .scraper import scrape_all

scheduler = BackgroundScheduler()


def _scheduled_scrape() -> None:
    db = SessionLocal()
    try:
        results = scrape_all(db)
        new_total = sum(results.values())
        print(f"[scheduler] scraped {len(results)} artists, {new_total} new concerts")
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
