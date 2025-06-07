from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import session
import sqlalchemy
from database import create_tables, get_db
from models import User
from contextlib import asynccontextmanager
from authlib.integrations.requests_client import OAuth2Session
# from jose import JWTError, jwt
import httpx
from datetime import datetime, timedelta
from config import settings
import os
from typing import Optional

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_tables()
    yield
    # Shutdown (if you need cleanup later)

app = FastAPI(title="NyxBox API", lifespan=lifespan)

@app.get("/auth/google") # Start Google OAuth flow
def begin_google_oauth():
    oauth = OAuth2Session(
        client_id=settings.GOOGLE_CLIENT_ID,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        scope=['openid', 'email', 'profile'])
    auth_url, state = oauth.create_authorization_url('https://accounts.google.com/oauth/authorize')
    return {"auth_url": auth_url, "state": state} # Optionally return state if client needs it

@app.get("/auth/google/callback")
def redirect_google_oauth(request: Request, code: str, state: Optional[str] = None): # Changed request to be non-optional
    oauth = OAuth2Session(
        client_id=settings.GOOGLE_CLIENT_ID,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=state # Pass the received state to the session for validation if needed
    )
    try:
        token = oauth.fetch_token(
            'https://oauth2.googleapis.com/token',
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            authorization_response=str(request.url) # Pass the full callback URL
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch token: {str(e)}")

    # Get user info from Google
    try:
        user_info_resp = oauth.get('https://www.googleapis.com/oauth2/v3/userinfo')
        user_info_resp.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        user_info = user_info_resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user info: {str(e)}")
    
    # TODO: Create/find user in database using user_info['sub'] (Google's unique ID) or email
    # Example: 
    # db_user = db.query(User).filter(User.google_id == user_info.get("sub")).first()
    # if not db_user:
    #     db_user = User(google_id=user_info.get("sub"), email=user_info.get("email"), name=user_info.get("name"), avatar_url=user_info.get("picture"))
    #     db.add(db_user)
    #     db.commit()
    #     db.refresh(db_user)
    
    # TODO: Generate JWT token for your application using db_user.id or email
    # jwt_token = create_jwt_token(data={"user_id": db_user.id})

    # For now, just return success and user info
    return {"message": "Login successful", "user_info": user_info, "token_details": token}

@app.post("/auth/logout") # Log User Out
@app.get("/auth/me") # Get user info
def user_info():
    pass
@app.get("/challenges") # List challenges  
def list_available_challs():
    pass
@app.get("/challenges/{id}") # Get challenge
def get_chall_by_id():
    pass
@app.post("/challenges/{id}/submit") # Submit solution
def submit_solution_by_id():
    pass