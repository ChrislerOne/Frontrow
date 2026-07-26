import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# Defaults to a file in the working dir for local runs; set DATABASE_PATH to a
# mounted volume path (e.g. /data/tracker.db) so the DB survives container redeploys.
DATABASE_PATH = os.getenv("DATABASE_PATH", "tracker.db")

engine = create_engine(
    f"sqlite:///{DATABASE_PATH}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    # WAL lets the 12h scheduler write while requests read without "database is
    # locked"; busy_timeout waits instead of failing on brief contention.
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
