import sqlalchemy

from sqlalchemy import Column, Integer, String, JSON, DateTime, create_engine, UniqueConstraint
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
    slack_id = Column(String, unique=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    refresh_jwt = Column(String, unique=True)
    refresh_jwt_expiry = Column(DateTime, default=get_expiry_time)
    # Community features
    bio = Column(String, nullable=True)
    is_admin = Column(Integer, default=0)  # 1 for admin, 0 for regular user
    
    def __repr__(self):
        return f"<User(email='{self.email}', name='{self.name}')>"

class Challenges(Base):
    
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, unique=True, nullable=False)
    tests = Column(JSON, nullable=False)
    points = Column(Integer, default=0)  # Points/score for solving
    author = Column(String, nullable=True)  # Who created the challenge
    difficulty = Column(String, nullable=False)
    function_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    params = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    constraints = Column(String, nullable=False)
    notes = Column(String, nullable=True)
    hints = Column(JSON, nullable=True)
    
    # The below likely won't get used for a good while until I implement more endpoints

    is_active = Column(Integer, default=0)  # 1 for active, 0 for hidden/archived
    # Above should always be true until approved! 
    is_reviewed = Column(Integer, default=0) # To let the user know if is_approved is false because it hasn't been reviewed or if it was because it got denied
    is_approved = Column(Integer, default=0) # 0 for approved, 1 for not approved
    submitted_by = Column(Integer, sqlalchemy.ForeignKey("users.id"), nullable=True)  # User ID of submitter
    is_featured = Column(Integer, default=0)  # 1 for featured, 0 for not
    likes = Column(Integer, default=0)
    solves = Column(Integer, default=0)
    tags = Column(JSON, nullable=True)  # List of tags
    flagged = Column(Integer, default=0)  # 1 if flagged for review

class UserSolve(Base):
    __tablename__ = "user_solves"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, sqlalchemy.ForeignKey("users.id"), nullable=False)
    challenge_id = Column(Integer, sqlalchemy.ForeignKey("challenges.id"), nullable=False)
    solved_at = Column(DateTime, default=datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint('user_id', 'challenge_id', name='_user_challenge_solve_uc'),)

class UserLike(Base):
    __tablename__ = "user_likes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, sqlalchemy.ForeignKey("users.id"), nullable=False)
    challenge_id = Column(Integer, sqlalchemy.ForeignKey("challenges.id"), nullable=False)
    liked_at = Column(DateTime, default=datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint('user_id', 'challenge_id', name='_user_challenge_like_uc'),)

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, sqlalchemy.ForeignKey("users.id"), nullable=False)
    challenge_id = Column(Integer, sqlalchemy.ForeignKey("challenges.id"), nullable=False)
    code = Column(String)
    result = Column(String)  # e.g., "passed", "failed"
    submitted_at = Column(DateTime, default=datetime.now(timezone.utc))