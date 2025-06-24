# Built Ins
import hashlib
import json
import os
import secrets
import typing
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

# Third partys
import redis
from authlib.integrations.requests_client import OAuth2Session
from config import settings
from database import create_tables, get_db
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from models import Challenges, User, UserLike, UserSolve
from schemas import ChallengeDetailSchema, ChallengeListItemSchema, RefreshTokensRequest
from sqlalchemy.orm import Session


# oauth_state = {}
# pending_auth: dict[str, dict] = {}

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        if not settings.JWT_SECRET:
            raise HTTPException(status_code=500, detail="JWT_SECRET not configured on server")
        
        payload = jwt.decode(token, settings.JWT_SECRET)
        user_id_from_payload: Optional[int] = payload.get("user_id")
        if user_id_from_payload is None:
            raise credentials_exception
    except JWTError: # Handles expired tokens, invalid signatures, etc.
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id_from_payload).first()
    if user is None:
        raise credentials_exception
    return user

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_tables()
    yield

app = FastAPI(title="NyxBox API", lifespan=lifespan)

@app.get('/redirect')
def redirect_user(token: str):
    try:
        url_data = redis_client.get(f"redirect_url:{token}")
        if url_data:
            return RedirectResponse(url_data) #type: ignore
        else:
            raise HTTPException(status_code=404, detail="URL not found for this session")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Account related things
@app.get("/auth/google") # Start Google OAuth flow
def begin_google_oauth(session_id: str):
    # global oauth_state
    # redirect_uri = f"{settings.GOOGLE_REDIRECT_URI}?session_id={session_id}"
    random_state_value = secrets.token_urlsafe(32)
    oauth = OAuth2Session(
        client_id=settings.GOOGLE_CLIENT_ID,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        scope=['openid', 'email', 'profile'])
    auth_url, _ = oauth.create_authorization_url(
        'https://accounts.google.com/o/oauth2/v2/auth',
        state=random_state_value)
    redis_client.setex(f"oauth_state:{random_state_value}", 120, session_id)
    redirect_token = secrets.token_urlsafe(12)
    redis_client.setex(f"redirect_url:{redirect_token}", 180, auth_url)
    redirect_url = f"{settings.API_BASE_URL}/redirect?token={redirect_token}"
    return {"auth_url": redirect_url}

@app.get("/auth/google/callback")
def redirect_google_oauth(request: Request, code: str, state: Optional[str] = None, db: Session = Depends(get_db), session_id: str = ""): 
    oauth = OAuth2Session(
        client_id=settings.GOOGLE_CLIENT_ID,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=state 
    )
    if not state:
        raise HTTPException(status_code=400, detail="State parameter missing from callback")
    # DO NOT REMOVE, THIS ACTUALLY DOES SOMETHING
    try:
        token = oauth.fetch_token(
            'https://oauth2.googleapis.com/token',
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            authorization_response=str(request.url)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch token: {str(e)}")
    original_session_id = redis_client.get(f"oauth_state:{state}")
    if original_session_id:
        redis_client.delete(f"oauth_state:{state}")    
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
    refresh_jwt_expiry = datetime.now(timezone.utc) + timedelta(days=30)
    if existing_user:
        if existing_user.google_id is None:
            setattr(existing_user, 'google_id', str(user_info['sub']))
            db.commit()
        user = existing_user
        user.refresh_jwt=refresh_jwt # type: ignore
        user.refresh_jwt_expiry = refresh_jwt_expiry # type: ignore
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
    user_jwt_expiry = datetime.now(timezone.utc)+timedelta(hours=1)
    user_jwt=jwt.encode(
        claims={"user_id": user.id, "exp": user_jwt_expiry, "iat": datetime.now(timezone.utc)},
        key=settings.JWT_SECRET
    )
    if not original_session_id:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    redis_client.setex(
    f"pending_auth:{original_session_id}",
    180,
    json.dumps({
            "completed": True,
            "access_token": user_jwt,
            "refresh_token": refresh_jwt,
            "user_data": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            },
            "access_exp": user_jwt_expiry.isoformat(),
            "refresh_exp": refresh_jwt_expiry.isoformat()
        })
    )
    
    #TODO: Switch this over to the file
    html_path = os.path.join(os.path.dirname(__file__), "static", "auth_complete.html")
    with open(html_path, "r") as f:
        html_content = f.read()
    return HTMLResponse(html_content)  # noqa: F541
    # return {"message": "Google login successful", "jwt": user_jwt, "refresh": refresh_jwt, "id": user.id, "name": user.name, "email": user.email}

@app.get("/auth/github") # Start Github OAuth flow
def begin_github_auth(session_id: str):
    # global oauth_state
    random_state_value = secrets.token_urlsafe(32)
    oauth = OAuth2Session(
        client_id=settings.GITHUB_CLIENT_ID,
        redirect_uri=settings.GITHUB_REDIRECT_URI,
        scope=['user:email', 'user:user'])
    auth_url, state = oauth.create_authorization_url(
        'https://github.com/login/oauth/authorize',
        state=random_state_value)
    redis_client.setex(f"oauth_state:{random_state_value}", 120, session_id)
    redirect_token = secrets.token_urlsafe(12)
    redis_client.setex(f"redirect_url:{redirect_token}", 180, auth_url)
    redirect_url = f"{settings.API_BASE_URL}/redirect?token={redirect_token}"
    return {"auth_url": redirect_url}

@app.get("/auth/github/callback")
def redirect_github_auth(request: Request, code: str, state: Optional[str] = None, db: Session = Depends(get_db)): 
    # global oauth_state
    oauth = OAuth2Session(
        client_id=settings.GITHUB_CLIENT_ID,
        redirect_uri=settings.GITHUB_REDIRECT_URI,
        state=state 
    )
    original_session_id = redis_client.get(f"oauth_state:{state}")
    if original_session_id:
        redis_client.delete(f"oauth_state:{state}") 

    if not state:
        raise HTTPException(status_code=400, detail="State parameter missing from callback")
    if not original_session_id:
        raise HTTPException(status_code=400, 
        detail="Invalid or expired state")
    try:
        # DO NOT REMOVE, THIS ACTUALLY DOES SOMETHING
        token = oauth.fetch_token(  # noqa: F841
            'https://github.com/login/oauth/access_token',
            client_secret=settings.GITHUB_CLIENT_SECRET,
            authorization_response=str(request.url)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch token: {str(e)}")
    #Get user info from Github
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
    refresh_jwt_expiry = datetime.now(timezone.utc) + timedelta(days=30)
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
        user.refresh_jwt_expiry = refresh_jwt_expiry # type: ignore
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
    user_expiry = datetime.now(timezone.utc)+timedelta(hours=1)
    user_jwt=jwt.encode(
        claims={"user_id": user.id, "exp": user_expiry, "iat": datetime.now(timezone.utc)},
        key=settings.JWT_SECRET
    )
    if not original_session_id:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    redis_client.setex(
        f"pending_auth:{original_session_id}",
        180,
        json.dumps({
            "completed": True,
            "access_token": user_jwt,
            "refresh_token": refresh_jwt,
            "user_data": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            },
            "access_exp": user_expiry.isoformat(),
            "refresh_exp": refresh_jwt_expiry.isoformat()
            
        })
    )
    #TODO: Switch this over to the file
    html_path = os.path.join(os.path.dirname(__file__), "static", "auth_complete.html")
    with open(html_path, "r") as f:
        html_content = f.read()
    return HTMLResponse(html_content)  # noqa: F541
# ...existing code...
    # return {"message": "Github login successful", "jwt": user_jwt, "refresh_jwt": refresh_jwt, "id": user.id, "name": user.name, "email": user.email}

#TODO: Update these params
#I think thats done
@app.post("/auth/refresh") # To get a new JWT with a valid refresh jwt
def refresh_jwt(token_data: RefreshTokensRequest, db: Session = Depends(get_db)):
    jwt_user = db.query(User).filter(
        (User.refresh_jwt == token_data.refresh_token)
    ).first()
    now = datetime.now(timezone.utc)
    if not jwt_user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if not token_data.refresh_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    expiry_timestamp: Optional[datetime] = jwt_user.refresh_jwt_expiry # type:ignore
    if expiry_timestamp is not None and expiry_timestamp.tzinfo is None:
        expiry_timestamp = expiry_timestamp.replace(tzinfo=timezone.utc)
    if expiry_timestamp is None or expiry_timestamp < now:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    else:
        refresh_expiry = datetime.now(timezone.utc) + timedelta(days=30)
        new_refresh_jwt=str(secrets.token_hex(32))
        jwt_user.refresh_jwt=new_refresh_jwt # type: ignore
        jwt_user.refresh_jwt_expiry = datetime.now(timezone.utc) + timedelta(days=30) # type: ignore
        db.commit()
        if not settings.JWT_SECRET:
            raise HTTPException(status_code=500, detail="No JWT Secret found")
        user_expiry=datetime.now(timezone.utc)+timedelta(hours=1)
        user_jwt=jwt.encode(
            claims={"user_id": jwt_user.id, "exp": user_expiry, "iat": datetime.now(timezone.utc)},
            key=settings.JWT_SECRET
        )
        return {
            # "message": "Refresh JWT generated", 
            "refresh_jwt": new_refresh_jwt, 
            "user_jwt": user_jwt,
            "refresh_expiry": refresh_expiry.isoformat(),
            "user_jwt_expiry": user_expiry.isoformat(),
            "user_data": {
                 "id": jwt_user.id,
                "email": jwt_user.email,
                "name": jwt_user.name,
                "google_id": jwt_user.google_id,
                "github_id": jwt_user.github_id,
                "avatar_url": jwt_user.avatar_url,
                "bio": jwt_user.bio,
                "created_at": jwt_user.created_at
            }
            }

@app.post("/auth/logout") # Log User Out
def logout_user(refresh_jwt: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.refresh_jwt == refresh_jwt).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user.refresh_jwt = None # type: ignore
    user.refresh_jwt_expiry = None # type: ignore
    db.commit()
    return {"message": "Logged out successfully"}

@app.get("/auth/guest")
def provide_pow_for_guest():
    pass

# Change to use JWT
@app.get("/auth/me") # Get user info
async def user_info(current_user: User = Depends(get_current_user)): # Changed signature
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "google_id": current_user.google_id,
        "github_id": current_user.github_id,
        "avatar_url": current_user.avatar_url,
        "bio": current_user.bio,
        "created_at": current_user.created_at
    }

@app.get("/auth/check-status/{session_id}")
def check_auth_status(session_id: str):
    auth_data_raw = redis_client.get(f"pending_auth:{session_id}")
    if auth_data_raw:
        auth_data = json.loads(typing.cast(str, auth_data_raw))
        if auth_data.get("completed"):
            result = {
                "status": "completed",
                "access_token": auth_data.get("access_token"),
                "user_data": auth_data.get("user_data"),
                "refresh_token": auth_data.get("refresh_token"),
                "access_exp": auth_data.get("access_exp"),
                "refresh_exp": auth_data.get("refresh_exp")
            }
            redis_client.delete(f"pending_auth:{session_id}")  # Clean up
            return result
        else:
            return {"status": "pending"}
    else:
        return {"status": "expired"}

#Challenge related things
@app.get("/challenges", response_model=typing.List[ChallengeListItemSchema]) # List challenges  
def list_available_challs(db: Session = Depends(get_db)):
    ret_challs = db.query(Challenges).filter(Challenges.flagged == False).all()  # noqa: E712
    return ret_challs
# When the user access a challenge, the frontend should call /challenges/id and cache it locally

@app.get("/challenges/{chall_id}", response_model=ChallengeDetailSchema) # Get challenge
def get_chall_by_id(chall_id: int, db: Session = Depends(get_db)):
    chall = db.query(Challenges).filter(Challenges.id == id, Challenges.flagged == False).first()  # noqa: E712
    if chall:
        return chall
    else:
        raise HTTPException(404, detail="No such challenge")

# @app.get("/challenges/{id}/approve") This might not be needed? We can make an interface to approve it locally

@app.post("/challenges/{chall_id}/submit") # Submit solution
def submit_solution_by_id(chall_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # We dont need to evaluate code locally bcs:
    # 1. We already have the user evaluate code
    # 2. It's very hard to secure
    chall = db.query(Challenges).filter(Challenges.id == chall_id, Challenges.flagged == False).first()  # noqa: E712
    if not chall:
        raise HTTPException(404, detail="No such challenge")
    
    # Check if user already solved this (prevent duplicate counting)
    existing_solve = db.query(UserSolve).filter(
        UserSolve.user_id == current_user.id, 
        UserSolve.challenge_id == chall_id
    ).first()
    
    if not existing_solve:
        # Create solve record
        user_solve = UserSolve(user_id=current_user.id, challenge_id=chall_id)
        db.add(user_solve)
        
        # Increment solve count
        chall.solves = (chall.solves or 0) + 1 # type: ignore
        db.commit()
    
    return {"id": chall_id, "solves": chall.solves, "already_solved": bool(existing_solve)}

# I forgot but we probably should authenticate to prevent mass spam?
@app.post("/challenges/{chall_id}/like")
def like_challenge(chall_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chall = db.query(Challenges).filter(Challenges.id == chall_id, Challenges.flagged == False).first()  # noqa: E712
    if not chall:
        raise HTTPException(404, detail="No such challenge")
    
    existing_like = db.query(UserLike).filter(
        UserLike.user_id == current_user.id,
        UserLike.challenge_id == chall_id
    ).first()
    
    if existing_like:
        raise HTTPException(400, detail="Already liked this challenge")
    
    user_like = UserLike(user_id=current_user.id, challenge_id=chall_id)
    db.add(user_like)
    
    chall.likes = (chall.likes or 0) + 1 # type: ignore
    db.commit()
    
    return {"id": chall_id, "likes": chall.likes}

@app.delete("/challenges/{chall_id}/unlike")
def unlike_challenge(chall_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chall = db.query(Challenges).filter(Challenges.id == chall_id, Challenges.flagged == False).first()  # noqa: E712
    if not chall:
        raise HTTPException(404, detail="No such challenge")
    existing_like = db.query(UserLike).filter(
        UserLike.user_id == current_user.id,
        UserLike.challenge_id == chall_id
    ).first()

    if not existing_like:
        raise HTTPException(400, detail="User has not liked challenge")
    
    if chall.likes == 0 or None: # type: ignore
        raise HTTPException(500, detail="No likes on challenge")

    user_like = UserLike(user_id=current_user.id, challenge_id=chall_id)
    db.delete(user_like)
    
    chall.likes = (chall.likes)-1 # type: ignore
    db.commit()

    return {"id": chall_id, "likes": chall.likes}

@app.post("/challenges/create")
def create_challenge(challenge_data: dict, jwt: str, db: Session = Depends(get_db)):
    pass

@app.get("/")
def return_index_page():
    with open("static/index.html") as f:
        html_data = f.read()
    return HTMLResponse(html_data)

app.mount(
    "/static",
    StaticFiles(directory="static", html=True),
    name="static-root",
)