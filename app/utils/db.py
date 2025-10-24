from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.utils.settings import get_settings
from app.services.orm_models import Base


def get_engine():
    settings = get_settings()
    print(settings.db_host, settings.db_user, settings.db_pass, settings.db_name)
    if not all([settings.db_host, settings.db_user, settings.db_pass, settings.db_name]):
        raise RuntimeError("Database configuration is incomplete. Check db_host, db_user, db_pass, db_name")
    
    # Build MySQL connection URL with SSL parameters
    database_url = f"mysql+pymysql://{settings.db_user}:{settings.db_pass}@{settings.db_host}:{settings.db_port}/{settings.db_name}?ssl_ca=server-ca.pem&ssl_cert=client-cert.pem&ssl_key=client-key.pem"
    
    # SQLAlchemy 2.0 engine with connection pooling and SSL
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,  # Recycle connections every hour
        future=True,
        connect_args={
            "ssl_disabled": False,
            "ssl_verify_cert": True,
            "ssl_verify_identity": True
        }
    )
    return engine


def create_all(engine) -> None:
    """Create all tables defined in the ORM models."""
    Base.metadata.create_all(bind=engine)


def get_session_factory() -> sessionmaker[Session]:
    """Get a session factory for database operations."""
    engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
