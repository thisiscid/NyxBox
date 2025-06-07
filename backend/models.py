import sqlalchemy

from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone, timedelta

Base = declarative_base()
    
def get_expiry_time():
    return datetime.now(timezone.utc)+timedelta(days=30)

class User(Base):
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    google_id = Column(String, unique=True)
    github_id = Column(String, unique=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    refresh_jwt = Column(String, unique=True)
    refresh_jwt_expiry = Column(DateTime, default=get_expiry_time)
    
    def __repr__(self):
        return f"<User(email='{self.email}', name='{self.name}')>"
