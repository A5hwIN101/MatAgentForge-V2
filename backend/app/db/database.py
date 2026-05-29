from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


ROOT_DIR = Path(__file__).resolve().parents[3]
SQLITE_DIR = ROOT_DIR / "data" / "sqlite"
SQLITE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = SQLITE_DIR / "app.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    from app.db.models import Base as ModelBase

    SQLITE_DIR.mkdir(parents=True, exist_ok=True)
    ModelBase.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
