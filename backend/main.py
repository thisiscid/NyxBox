from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import session, Session
import sqlalchemy
from database import create_tables, get_db
from models import User
from contextlib import asynccontextmanager
from authlib.integrations.requests_client import OAuth2Session
from jose import JWTError, jwt
import httpx
from datetime import datetime, timedelta, timezone
from config import settings
import os
from typing import Optional
import secrets

oauth_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_tables()
    yield

app = FastAPI(title="NyxBox API", lifespan=lifespan)

@app.get("/auth/google") # Start Google OAuth flow
def begin_google_oauth(session_id: str):
    global oauth_state
    # redirect_uri = f"{settings.GOOGLE_REDIRECT_URI}?session_id={session_id}"
    random_state_value = secrets.token_urlsafe(32)
    oauth = OAuth2Session(
        client_id=settings.GOOGLE_CLIENT_ID,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        scope=['openid', 'email', 'profile'])
    auth_url, _ = oauth.create_authorization_url(
        'https://accounts.google.com/o/oauth2/v2/auth',
        state=random_state_value)
    oauth_state[random_state_value]=session_id
    return {"auth_url": auth_url}

@app.get("/auth/google/callback")
def redirect_google_oauth(request: Request, code: str, state: Optional[str] = None, db: Session = Depends(get_db), session_id: str = ""): 
    oauth = OAuth2Session(
        client_id=settings.GOOGLE_CLIENT_ID,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=state 
    )
    if not state:
        raise HTTPException(status_code=400, detail="State parameter missing from callback")
    try:
        token = oauth.fetch_token(
            'https://oauth2.googleapis.com/token',
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            authorization_response=str(request.url)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch token: {str(e)}")
    original_session_id = oauth_state.pop(state, None)
    if not state:
        raise HTTPException(status_code=400, detail="State parameter missing from callback")
    if not original_session_id:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    # Get user info from Google
    try:
        user_info_resp = oauth.get('https://www.googleapis.com/oauth2/v3/userinfo')
        user_info_resp.raise_for_status() 
        user_info = user_info_resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user info: {str(e)}")
    existing_user = db.query(User).filter(
        (User.google_id == str(user_info['sub'])) | 
        (User.email == user_info['email'])
    ).first()
    refresh_jwt=str(secrets.token_hex(32))
    if existing_user:
        if existing_user.google_id is None:
            setattr(existing_user, 'google_id', str(user_info['sub']))
            db.commit()
        user = existing_user
        user.refresh_jwt=refresh_jwt # type: ignore
        user.refresh_jwt_expiry = datetime.now(timezone.utc) + timedelta(days=30) # type: ignore
        db.commit() 
    else:
        user = User(
            email=user_info['email'],
            name=user_info.get('name') or user_info['login'],  
            google_id=str(user_info['sub']),
            refresh_jwt=refresh_jwt,
            refresh_jwt_expiry = datetime.now(timezone.utc) + timedelta(days=30)
        )
        db.add(user)       # Add to database
        db.commit()        # Save changes
        db.refresh(user)
    if not settings.JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET not configured")
    user_jwt=jwt.encode(
        claims={"user_id": user.id, "exp": datetime.now(timezone.utc)+timedelta(hours=1), "iat": datetime.now(timezone.utc)},
        key=settings.JWT_SECRET
    )
    return {"message": "Google login successful", "jwt": user_jwt, "refresh": refresh_jwt, "id": user.id, "name": user.name, "email": user.email}

@app.get("/auth/github") # Start Github OAuth flow
def begin_github_auth(session_id: str):
    global oauth_state
    random_state_value = secrets.token_urlsafe(32)
    oauth = OAuth2Session(
        client_id=settings.GITHUB_CLIENT_ID,
        redirect_uri=settings.GITHUB_REDIRECT_URI,
        scope=['user:email', 'user:user'])
    auth_url, state = oauth.create_authorization_url(
        'https://github.com/login/oauth/authorize',
        state=random_state_value)
    oauth_state[random_state_value] = session_id
    return {"auth_url": auth_url}

@app.get("/auth/github/callback")
def redirect_github_auth(request: Request, code: str, state: Optional[str] = None, db: Session = Depends(get_db)): 
    global oauth_state
    oauth = OAuth2Session(
        client_id=settings.GITHUB_CLIENT_ID,
        redirect_uri=settings.GITHUB_REDIRECT_URI,
        state=state 
    )
    try:
        token = oauth.fetch_token(
            'https://github.com/login/oauth/access_token',
            client_secret=settings.GITHUB_CLIENT_SECRET,
            authorization_response=str(request.url)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch token: {str(e)}")
    original_session_id = oauth_state.pop(state, None)
    if not state:
        raise HTTPException(status_code=400, detail="State parameter missing from callback")
    if not original_session_id:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    # Get user info from Google
    try:
        user_info_resp = oauth.get('https://api.github.com/user')
        user_info_resp.raise_for_status() 
        user_info = user_info_resp.json()
        email_resp = oauth.get('https://api.github.com/user/emails')
        email_resp.raise_for_status()
        emails = email_resp.json()
        primary_email = next((email['email'] for email in emails if email['primary']), None)
        user_info['email'] = primary_email

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user info: {str(e)}")
    refresh_jwt=str(secrets.token_hex(32))
    existing_user = db.query(User).filter(
        (User.github_id == str(user_info['id'])) | 
        (User.email == user_info['email'])
    ).first()
    if existing_user:
        if existing_user.github_id is None:
            setattr(existing_user, 'github_id', str(user_info['id']))
            db.commit()
        user = existing_user
        user.refresh_jwt=refresh_jwt # type: ignore
        user.refresh_jwt_expiry = datetime.now(timezone.utc) + timedelta(days=30) # type: ignore
        db.commit()
    else:
        user = User(
            email=user_info['email'],
            name=user_info.get('name') or user_info['login'],  
            github_id=str(user_info['id']),
            refresh_jwt=refresh_jwt,
            refresh_jwt_expiry=datetime.now(timezone.utc) + timedelta(days=30)
        )
        db.add(user)       # Add to database
        db.commit()        # Save changes
        db.refresh(user)
    if not settings.JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET not configured")
    user_jwt=jwt.encode(
        claims={"user_id": user.id, "exp": datetime.now(timezone.utc)+timedelta(hours=1), "iat": datetime.now(timezone.utc)},
        key=settings.JWT_SECRET
    )
    return {"message": "Github login successful", "jwt": user_jwt, "refresh_jwt": refresh_jwt, "id": user.id, "name": user.name, "email": user.email}

@app.get("/auth/refresh") # To get a new JWT with a valid refresh jwt
def refresh_jwt(request: Request, refresh_jwt: str, db: Session = Depends(get_db)):
    jwt_user = db.query(User).filter(
        (User.refresh_jwt == refresh_jwt)
    ).first()
    now = datetime.now(timezone.utc)
    if not jwt_user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if not refresh_jwt:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    expiry_timestamp: Optional[datetime] = jwt_user.refresh_jwt_expiry # type:ignore
    if expiry_timestamp is not None and expiry_timestamp.tzinfo is None:
        expiry_timestamp = expiry_timestamp.replace(tzinfo=timezone.utc)
    if expiry_timestamp is None or expiry_timestamp < now:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    else:
        new_refresh_jwt=str(secrets.token_hex(32))
        jwt_user.refresh_jwt=new_refresh_jwt # type: ignore
        jwt_user.refresh_jwt_expiry = datetime.now(timezone.utc) + timedelta(days=30) # type: ignore
        db.commit()
        if not settings.JWT_SECRET:
            raise HTTPException(status_code=500, detail="No JWT Secret found")
        user_jwt=jwt.encode(
            claims={"user_id": jwt_user.id, "exp": datetime.now(timezone.utc)+timedelta(hours=1), "iat": datetime.now(timezone.utc)},
            key=settings.JWT_SECRET
        )
        return {"message": "Refresh JWT generated", "refresh_jwt": new_refresh_jwt, "user_jwt": user_jwt}

@app.post("/auth/logout") # Log User Out
def logout_user(refresh_jwt: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.refresh_jwt == refresh_jwt).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user.refresh_jwt = None # type: ignore
    user.refresh_jwt_expiry = None # type: ignore
    db.commit()
    return {"message": "Logged out successfully"}

@app.get("/auth/me") # Get user info
def user_info(refresh_jwt: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.refresh_jwt == refresh_jwt).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return {"id": user.id, 
            "email": user.email, 
            "name": user.name, 
            "google_id": user.google_id, 
            "github_id": user.github_id, 
            "avatar": user.avatar_url
            }

@app.get("/challenges") # List challenges  
def list_available_challs():
    pass
@app.get("/challenges/{id}") # Get challenge
def get_chall_by_id():
    pass
@app.post("/challenges/{id}/submit") # Submit solution
def submit_solution_by_id():
    pass