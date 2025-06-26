from typing import List, Optional, Any
from pydantic import BaseModel
from datetime import datetime 
from sqlalchemy import Column, Integer, String, JSON, DateTime, create_engine, UniqueConstraint

# Schema for author information (if you add it later)
class ChallengeAuthorSchema(BaseModel):
    id: int
    name: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

# Schema for a single challenge item in a list
class ChallengeListItemSchema(BaseModel):
    id: int
    name: str
    difficulty: Optional[str] = None
    description: str
    function_name: str
    params: List[str]
    tests: List[dict]
    tags: Optional[List[str]] = None
    created_at: datetime
    points: Optional[int] = None
    solves: Optional[int] = None
    likes: Optional[int] = None
    # author: Optional[ChallengeAuthorSchema] = None # Will be null if not implemented

    class Config:
        from_attributes = True

# Probably unneded
# This actually sucks, we are just going to return everything in a list
# We shouldn't need to get per challenge, just return the challenges at once
class ChallengeDetailSchema(ChallengeListItemSchema): # Inherits from ListItem
    # description: Optional[str] = None
    updated_at: datetime
    tests: List[Any]


# Schema for the response when listing multiple challenges
class PaginatedChallengeListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[ChallengeListItemSchema]

class RefreshTokensRequest(BaseModel):
    refresh_token: str