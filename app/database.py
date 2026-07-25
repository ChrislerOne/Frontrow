import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Defaults to a file in the working dir for local runs; set DATABASE_PATH to a
# mounted volume path (e.g. /data/tracker.db) so the DB survives container redeploys.
DATABASE_PATH = os.getenv("DATABASE_PATH", "tracker.db")

engine = create_engine(
    f"sqlite:///{DATABASE_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
