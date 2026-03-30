from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config.settings import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,        # Max persistent connections in the pool
    max_overflow=20,     # Extra connections allowed beyond pool_size under load
    pool_timeout=30,     # Seconds to wait for a connection before timing out
    pool_recycle=1800,   # Recycle connections every 30 minutes to prevent stale connections
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

