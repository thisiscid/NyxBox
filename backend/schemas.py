# ... (near other imports and model imports)
from typing import List, Optional # Add List if not already there
from pydantic import BaseModel
from datetime import datetime # Ensure datetime is imported

# ... (your existing User model and other Pydantic schemas if any) ...

# Schema for author information (if you add it later)
class ChallengeAuthorSchema(BaseModel):
    id: int
    name: str
    avatar_url: Optional[str] = None

    class Config:
        orm_mode = True

# Schema for a single challenge item in a list
class ChallengeListItemSchema(BaseModel):
    id: int
    name: str
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: datetime
    # Future/Optional fields
    solves: Optional[int] = None
    likes: Optional[int] = None
    author: Optional[ChallengeAuthorSchema] = None # Will be null if not implemented

    class Config:
        orm_mode = True

# Schema for the full details of a single challenge
class ChallengeDetailSchema(ChallengeListItemSchema): # Inherits from ListItem
    description: Optional[str] = None
    # Test cases are essential as per your last message
    test_cases_python: Optional[str] = None
    test_cases_javascript: Optional[str] = None
    test_cases_cpp: Optional[str] = None
    test_cases_java: Optional[str] = None
    updated_at: datetime

# Schema for the response when listing multiple challenges
class PaginatedChallengeListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[ChallengeListItemSchema]
