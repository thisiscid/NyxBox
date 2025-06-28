# Built in libs
import hashlib
import json
import os
import secrets
import typing
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional
import requests
import socket

# Third party libs
# import redis
import redis.asyncio as redis
from redis.exceptions import RedisError # We're going to implement a function that allows funcs to retrieve safely
from authlib.integrations.requests_client import OAuth2Session
from config import settings
from database import create_tables, get_db
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from models import Challenges, User, UserLike, UserSolve
from schemas import ChallengeDetailSchema, ChallengeListItemSchema, RefreshTokensRequest
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx
# import slack


# oauth_state = {}
# pending_auth: dict[str, dict] = {}
ALLOWED_UA_PREFIX = "NyxBoxClient"
ALLOWED_PATHS = ["/", 
                 "/favicon.ico", 
                 "/auth/google", 
                 "/auth/google/callback", 
                 "/auth/github",
                 "/auth/github/callback",
                 "/auth/slack",
                 "/auth/slack/callback",
                 "/redirect",
                 ]

RATE_LIMIT = 15
POLLING_RATE_LIMIT = 60 # Client sends 1 req/min so if they send more than that something is probably wrong af
TIME_WINDOW = 60
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

#Pydantic stuff
class PowSubmission(BaseModel):
    nonce: str
    solution: int

# Filters out user agents EXCEPT if the user is accessing a static page that they need to access for authsla
class UserAgentFilter(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/static/") or path in ALLOWED_PATHS:
            return await call_next(request)
        ip = request.client.host  # type: ignore
        user_agent = request.headers.get("User-Agent", "").strip()
        if not user_agent.startswith(ALLOWED_UA_PREFIX):
            return JSONResponse(status_code=403, content={"detail": "Invalid User-Agent"})
        key = f"ip:{ip}"
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, 60)
        if path.startswith("/auth/check-status/"):
            if count >= POLLING_RATE_LIMIT:
                return JSONResponse(status_code=403, content={"detail": "Hit rate limit"})
        if count >= RATE_LIMIT:
            return JSONResponse(status_code=403, content={"detail": "Hit rate limit"})
        return await call_next(request)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User | dict:
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
    if payload.get("is_guest", False):
        return payload
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
app.add_middleware(UserAgentFilter)

@app.get('/redirect')
async def redirect_user(token: str):
    try:
        url_data = await redis_client.get(f"redirect_url:{token}")
        if url_data:
            return RedirectResponse(url_data) #type: ignore
        else:
            raise HTTPException(status_code=404, detail="URL not found for this session")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Account related things
@app.get("/auth/google") # Start Google OAuth flow
async def begin_google_oauth(session_id: str):
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
    await redis_client.setex(f"oauth_state:{random_state_value}", 120, session_id)
    redirect_token = secrets.token_urlsafe(12)
    await redis_client.setex(f"redirect_url:{redirect_token}", 180, auth_url)
    redirect_url = f"{settings.API_BASE_URL}/redirect?token={redirect_token}"
    return {"auth_url": redirect_url}

@app.get("/auth/google/callback")
async def redirect_google_oauth(request: Request, code: str, state: Optional[str] = None, db: Session = Depends(get_db), session_id: str = ""): 
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
    original_session_id = await redis_client.get(f"oauth_state:{state}")
    if original_session_id:
        await redis_client.delete(f"oauth_state:{state}")    
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
    await redis_client.setex(
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
async def begin_github_auth(session_id: str):
    # global oauth_state
    random_state_value = secrets.token_urlsafe(32)
    oauth = OAuth2Session(
        client_id=settings.GITHUB_CLIENT_ID,
        redirect_uri=settings.GITHUB_REDIRECT_URI,
        scope=['user:email', 'user:user'])
    auth_url, state = oauth.create_authorization_url(
        'https://github.com/login/oauth/authorize',
        state=random_state_value)
    await redis_client.setex(f"oauth_state:{random_state_value}", 120, session_id)
    redirect_token = secrets.token_urlsafe(12)
    await redis_client.setex(f"redirect_url:{redirect_token}", 180, auth_url)
    redirect_url = f"{settings.API_BASE_URL}/redirect?token={redirect_token}"
    return {"auth_url": redirect_url}

@app.get("/auth/github/callback")
async def redirect_github_auth(request: Request, code: str, state: Optional[str] = None, db: Session = Depends(get_db)): 
    # global oauth_state
    oauth = OAuth2Session(
        client_id=settings.GITHUB_CLIENT_ID,
        redirect_uri=settings.GITHUB_REDIRECT_URI,
        state=state 
    )
    original_session_id = await redis_client.get(f"oauth_state:{state}")
    if original_session_id:
        await redis_client.delete(f"oauth_state:{state}") 

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
    await redis_client.setex(
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

@app.get("/auth/slack") # Start Slack OAuth flow
async def begin_slack_auth(session_id: str):
    random_state_value = secrets.token_urlsafe(32)
    oauth = OAuth2Session(
        client_id=settings.SLACK_CLIENT_ID,
        client_secret=settings.SLACK_CLIENT_SECRET,
        redirect_uri=settings.SLACK_REDIRECT_URI,
        state=session_id,
        scope=["openid","email","profile"],
        token_endpoint_auth_method="client_secret_post",
    )
    auth_url, state = oauth.create_authorization_url(
        'https://slack.com/openid/connect/authorize',
        state=session_id)
    await redis_client.setex(f"oauth_state:{random_state_value}", 120, session_id)
    # redirect_token = secrets.token_urlsafe(12)
    await redis_client.setex(f"redirect_url:{session_id}", 180, auth_url)
    redirect_url = f"{settings.API_BASE_URL}/redirect?token={session_id}"
    return {"auth_url": redirect_url}

@app.get("/auth/slack/callback")
async def redirect_slack_auth(request: Request, code: str, state: Optional[str] = None, db: Session = Depends(get_db)): 
    oauth = OAuth2Session(
        client_id=settings.SLACK_CLIENT_ID,
        redirect_uri=settings.SLACK_REDIRECT_URI,
        state=state 
    )
    # original_session_id = await redis_client.get(f"oauth_state:{state}")
    original_session_id = state
    if original_session_id:
        await redis_client.delete(f"oauth_state:{original_session_id}") 

    if not state:
        raise HTTPException(status_code=400, detail="State parameter missing from callback")
    if not original_session_id:
        raise HTTPException(status_code=400, 
        detail="Invalid or expired state")
    try:
        # DO NOT REMOVE, THIS ACTUALLY DOES SOMETHING
        token = oauth.fetch_token(  # noqa: F841
            'https://slack.com/api/openid.connect.token',
            client_secret=settings.SLACK_CLIENT_SECRET,
            authorization_response=str(request.url)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch token: {str(e)}")
    try:
        user_info_resp = oauth.get('https://slack.com/api/openid.connect.userInfo')
        user_info_resp.raise_for_status()
        user_info = user_info_resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user info: {str(e)}")
    refresh_jwt=str(secrets.token_hex(32))
    refresh_jwt_expiry = datetime.now(timezone.utc) + timedelta(days=30)
    existing_user = db.query(User).filter(
        (User.slack_id == str(user_info['sub'])) | 
        (User.email == user_info['email'])
    ).first()
    if existing_user:
        if existing_user.slack_id is None:
            setattr(existing_user, 'slack_id', str(user_info['sub']))
            db.commit()
        user = existing_user
        user.refresh_jwt=refresh_jwt # type: ignore
        user.refresh_jwt_expiry = refresh_jwt_expiry # type: ignore
        db.commit()
    else:
        user = User(
            email=user_info['email'],
            name=user_info.get('name') or user_info['login'],  
            slack_id=str(user_info['sub']),
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
    await redis_client.setex(
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
async def provide_pow_for_guest(request: Request): # GET a PoW in order to access guest credentials
    nonce = secrets.token_hex(16)
    challenge = {
        "nonce": nonce, 
        "difficulty": 16 # Set this higher, takes too fast currently
        }
    await redis_client.setex(f"nonce:{request.client.host}",  # type: ignore
                             60, 
                             json.dumps(challenge))
    return JSONResponse(challenge)

@app.post("/auth/guest")
async def check_and_provide_guest_cred(request: Request, submission: PowSubmission):
    ip = request.client.host # type: ignore
    nonce = str(submission.nonce)
    solution = str(submission.solution)

    raw = await redis_client.get(f"nonce:{ip}")
    if not raw:
        raise HTTPException(403, detail="No active challenge; please retry")
    try:
        cached_challenge = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(500, detail="Server error reading challenge")
    hash_input = (nonce + solution).encode()
    digest = hashlib.sha256(hash_input).digest()
    bit_str = ''.join(f"{byte:08b}" for byte in digest)
    leading_zeros = len(bit_str) - len(bit_str.lstrip('0'))
    if leading_zeros >= cached_challenge["difficulty"]:
        #TODO: Implement JWT stuff here
        guest_id = f"guest:{secrets.token_urlsafe(8)}"
        jwt_params = {
            "user_id": guest_id,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=2)).timestamp()),
            "is_guest": True # this is used to tell the client/backend "Hey! This is a guest user, limit their access"
        }
        if settings.JWT_SECRET:
            jwt_response=jwt.encode(claims=jwt_params, key=settings.JWT_SECRET) # type: ignore
        else:
            raise HTTPException(500, detail="JWT_SECRET not configured")
        # await redis_client.setex(f"guest_access:{request.client.host}", timedelta(hours=2), jwt_response) # type: ignore
        await redis_client.delete(f"nonce:{ip}")
        return JSONResponse({
            "access_token": jwt_response,
            "guest_id":     guest_id,
            "access_exp":   jwt_params["exp"] 
        })
    else:
        raise HTTPException(403, detail="Invalid challenge response")


    

@app.get("/auth/me") # Get user info
#TODO: On frontend, if using offline/guest mode, prevent accessing profile page/input dummy data
async def user_info(current_user: User | dict = Depends(get_current_user)): # Changed signature
    if isinstance(current_user, dict):
        if current_user.get("is_guest", False):
            raise HTTPException(403, detail="Invalid token")
    else:
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
async def check_auth_status(session_id: str):
    auth_data_raw = await redis_client.get(f"pending_auth:{session_id}")
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
            await redis_client.delete(f"pending_auth:{session_id}")  # Clean up
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
def submit_solution_by_id(chall_id: int, db: Session = Depends(get_db), current_user: User | dict = Depends(get_current_user)):
    # We dont need to evaluate code locally bcs:
    # 1. We already have the user evaluate code
    # 2. It's very hard to secure
    # 3. So we'll just trust the user bcs fradulent submits are better than evaluating code locally and blowing up the computer
    if isinstance(current_user, dict):
        if current_user.get("is_guest", False):
            raise HTTPException(403, detail="Invalid token")
    else:
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
def like_challenge(chall_id: int, current_user: User | dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if isinstance(current_user, dict):
        if current_user.get("is_guest", False):
            raise HTTPException(403, detail="Invalid token")
        else:
            raise HTTPException(500, detail="Recieved invalid format on backend.")
    else:
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
    if isinstance(current_user, dict):
        if current_user.get("is_guest", False):
            raise HTTPException(403, detail="Invalid token")
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

# Misc Functions
@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):    
    hostname = socket.gethostname()
    try:
        ip_address = socket.gethostbyname(hostname)
    except socket.gaierror:
        ip_address = "127.0.0.1"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
    try:
        client = request.client
        if request.client:
            inbound_ip = request.client.host
        else:
            inbound_ip = "N/A"
    except Exception:
        inbound_ip = "N/A"
    async with httpx.AsyncClient() as client:
        await client.post(
            url=settings.SLACK_DMS_WEBHOOK_URL, # type: ignore
            json={"text": f"A critical error occurred in the app!\nHost: {ip_address}:{hostname}\nOutgoing IP: {ip}\nCalled by: {inbound_ip}\nInvoked on endpoint: {request.url}\nInvoked by: {type(exc).__name__}.{type(exc).__module__}\nError: {exc}"},
            headers={"Content-type": "application/json"}
        )
        await client.post(
            url=settings.SLACK_CHANNEL_WEBHOOK_URL, # type: ignore
            json={"text": "A critical error occurred in the app! Check DMs"},
            headers={"Content-type": "application/json"}
        )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# def create_log(path, severity, message):
#     with open(path, 'a') as f:
#         if severity == "error":
#             f.write(f"{datetime.now().isoformat()} ERROR: {message}\n")
#             requests.post(json={"text":"Hello, World!"}, headers=["Content-type: application/json"], url=settings.SLACK_WEBHOOK_URL) # type:ignore
#         elif severity == "warning":
#             f.write(f"{datetime.now().isoformat()} WARNING: {message}\n")
#         else:
#             f.write(f"{datetime.now().isoformat()} INFO: {message}\n")

app.mount(
    "/static",
    StaticFiles(directory="static", html=True),
    name="static-root",
)