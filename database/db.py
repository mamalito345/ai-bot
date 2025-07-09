from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from databases import Database
from app.config import settings

DATABASE_URL = settings.database_url

# async client (FastAPI)
database = Database(DATABASE_URL)

# sync engine (tabloları yaratmak için)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # sadece SQLite için
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
