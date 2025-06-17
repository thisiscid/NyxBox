from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Settings
from models import Base

# Create database engine
if Settings.DATABASE_URL is None:
    raise ValueError("DATABASE_URL is not configured")
engine = create_engine(Settings.DATABASE_URL, connect_args={"check_same_thread": False})

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()