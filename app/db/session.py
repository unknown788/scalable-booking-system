from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Increase the pool size for better concurrency
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,          # The number of connections to keep open
    max_overflow=10,       # Max additional connections to allow
    pool_timeout=30,       # How long to wait for a connection
    pool_recycle=1800      # Recycle connections after 30 mins
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
