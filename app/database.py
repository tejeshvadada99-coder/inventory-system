"""
database.py
------------
Sets up the connection to PostgreSQL and hands out DB "sessions" (a session
is a temporary workspace for talking to the database — you open one per
request and close it when you're done).

Every router file imports `get_db` from here and uses it as a FastAPI
dependency, e.g.:

    @router.get("/products")
    def list_products(db: Session = Depends(get_db)):
        ...
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# The engine is the actual connection pool to PostgreSQL.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# SessionLocal is a factory that creates new DB sessions on demand.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the parent class every table model (in models.py) inherits from.
# SQLAlchemy uses it to know which Python classes map to which DB tables.
Base = declarative_base()


def get_db():
    """
    FastAPI dependency: opens one DB session per incoming request,
    gives it to the route function, then always closes it afterwards
    (even if the route raised an error).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
