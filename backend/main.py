from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import session, Session
import sqlalchemy
from database import create_tables, get_db
from models import User, Challenges
from contextlib import asynccontextmanager
import typing
from authlib.integrations.requests_client import OAuth2Session
from jose import JWTError, jwt
import httpx
from datetime import datetime, timedelta, timezone
from config import settings
import os
from typing import Optional
import secrets
import redis
import json

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
            # This is a server configuration error
            raise HTTPException(status_code=500, detail="JWT_SECRET not configured on server")
        
        payload = jwt.decode(token, settings.JWT_SECRET)
        user_id_from_payload: Optional[int] = payload.get("user_id")
        if user_id_from_payload is None:
            raise credentials_exception
    except JWTError: # Handles expired tokens, invalid signatures, etc.
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id_from_payload).first()
    if user is None:
        # User ID from a valid token not found in DB (e.g., user deleted after token issuance)
        raise credentials_exception
    return user

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_tables()
    yield

app = FastAPI(title="NyxBox API", lifespan=lifespan)

# @app.post('/redirect') # Create a link for redirect
# def set_redirect_link(link: str, session_id: str):
#     redis_client.setex(
#         "redirect_url:{session_id}",
#         600,  # expires in 10 minutes
#         json.dumps({
#             "url": link,
#         })
#         )
#     return

@app.get('/redirect')
def redirect_user(redirect_token: str):
    try:
        url_data = redis_client.get(f"redirect_url:{redirect_token}")
        if url_data:
            url = json.loads(str(url_data)).get("url")
            return RedirectResponse(url)
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
    redirect_token = secrets.token_urlsafe(16)
    redis_client.setex(f"redirect_url:{redirect_token}", 180, auth_url)
    qr_redirect_url = f"{settings.API_BASE_URL}/redirect?token={redirect_token}"
    return {"auth_url": qr_redirect_url}

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
    if not original_session_id:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    redis_client.setex(
    f"pending_auth:{original_session_id}",
    600,  # expires in 10 minutes
    json.dumps({
        "completed": True,
        "access_token": user_jwt,
        "refresh_token": refresh_jwt,
        "user_data": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    })
)

    return HTMLResponse(f"""
    <html>
        <head>
            <title>Authentication Successful</title>
            <style>
                body {{
                    display: flex;
                    justify-content: center; /* Horizontally center the .terminal-window */
                    align-items: center;    /* Vertically center the .terminal-window */
                    min-height: 100vh;
                    margin: 0;
                    background-color: #282c34; /* A slightly different page background */
                    font-family: 'Menlo', 'Monaco', 'Consolas', 'Courier New', monospace;
                    color: #d0d0d0; /* Default light text color for the page */
                }}
                .terminal-window {{
                    background-color: #1e1e1e; /* Dark terminal background */
                    border: 1px solid #000;
                    border-radius: 6px;
                    padding: 25px;
                    width: 90%;
                    max-width: 650px;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.4);
                    /* The content inside will be block, text-align left handles the rest */
                }}
                .terminal-window .checkmark {{
                    font-size: 2.5em; /* Adjusted size */
                    color: #98c379;
                    margin-bottom: 15px;
                    text-align: left; /* Checkmark also to the left */
                }}
                .terminal-window h1 {{
                    color: #61afef;
                    margin-top: 0;
                    margin-bottom: 15px;
                    font-size: 1.4em;
                    text-align: left;
                }}
                .terminal-window p {{
                    font-size: 1em;
                    line-height: 1.6;
                    text-align: left;
                    margin-bottom: 10px;
                }}
                .terminal-window p.small-text {{
                    font-size: 0.85em;
                    color: #888; /* Dimmer color for the auto-close message */
                    text-align: left;
                }}
                .daemon-user-nyx {{
                    color: #B3507D;
                    font-weight: bold;
                }}
                .daemon-user-hackclub {{
                    color: #A3C9F9;
                }}
            </style>
        </head>
        <body>
            <div class="terminal-window">
                <div class="checkmark">✓</div>
                <h1>
                    <span class="daemon-user-nyx">nyx</span>@<span class="daemon-user-hackclub">hackclub</span>:~&#36; 
                    Authentication Successful!
                </h1>
                <p>
                    <span class="daemon-user-nyx">nyx</span>@<span class="daemon-user-hackclub">hackclub</span>:~&#36; 
                    You can now close this window and return to NyxBox.
                </p>
                <p class="small-text">(This window should close automatically shortly.)</p>
            </div>
            <script>
                setTimeout(function() {{
                    window.close();
                }}, 4000); // Slightly longer delay
            </script>
        </body>
    </html>
    """)
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
    original_session_id = redis_client.get(f"oauth_state:{state}")
    if original_session_id:
        redis_client.delete(f"oauth_state:{state}") 

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
    if not original_session_id:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    redis_client.setex(
        f"pending_auth:{original_session_id}",
        600,  # expires in 10 minutes
        json.dumps({
            "completed": True,
            "access_token": user_jwt,
            "refresh_token": refresh_jwt,
            "user_data": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        })
    )
    return HTMLResponse(f"""
    <html>
        <head>
            <title>Authentication Successful</title>
            <style>
                body {{
                    display: flex;
                    justify-content: center; /* Horizontally center the .terminal-window */
                    align-items: center;    /* Vertically center the .terminal-window */
                    min-height: 100vh;
                    margin: 0;
                    background-color: #282c34; /* A slightly different page background */
                    font-family: 'Menlo', 'Monaco', 'Consolas', 'Courier New', monospace;
                    color: #d0d0d0; /* Default light text color for the page */
                }}
                .terminal-window {{
                    background-color: #1e1e1e; /* Dark terminal background */
                    border: 1px solid #000;
                    border-radius: 6px;
                    padding: 25px;
                    width: 90%;
                    max-width: 650px;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.4);
                    /* The content inside will be block, text-align left handles the rest */
                }}
                .terminal-window .checkmark {{
                    font-size: 2.5em; /* Adjusted size */
                    color: #98c379;
                    margin-bottom: 15px;
                    text-align: left; /* Checkmark also to the left */
                }}
                .terminal-window h1 {{
                    color: #61afef;
                    margin-top: 0;
                    margin-bottom: 15px;
                    font-size: 1.4em;
                    text-align: left;
                }}
                .terminal-window p {{
                    font-size: 1em;
                    line-height: 1.6;
                    text-align: left;
                    margin-bottom: 10px;
                }}
                .terminal-window p.small-text {{
                    font-size: 0.85em;
                    color: #888; /* Dimmer color for the auto-close message */
                    text-align: left;
                }}
                .daemon-user-nyx {{
                    color: #B3507D;
                    font-weight: bold;
                }}
                .daemon-user-hackclub {{
                    color: #A3C9F9;
                }}
            </style>
        </head>
        <body>
            <div class="terminal-window">
                <div class="checkmark">✓</div>
                <h1>
                    <span class="daemon-user-nyx">nyx</span>@<span class="daemon-user-hackclub">hackclub</span>:~&#36; 
                    Authentication Successful!
                </h1>
                <p>
                    <span class="daemon-user-nyx">nyx</span>@<span class="daemon-user-hackclub">hackclub</span>:~&#36; 
                    You can now close this window and return to NyxBox.
                </p>
                <p class="small-text">(This window should close automatically shortly.)</p>
            </div>
            <script>
                setTimeout(function() {{
                    window.close();
                }}, 4000); // Slightly longer delay
            </script>
        </body>
    </html>
    """)
# ...existing code...
    # return {"message": "Github login successful", "jwt": user_jwt, "refresh_jwt": refresh_jwt, "id": user.id, "name": user.name, "email": user.email}

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
                "status": "completed",
                "access_token": auth_data["access_token"],
                "user_data": auth_data["user_data"],
                "refresh_token": auth_data.get("refresh_token")
            }
            redis_client.delete(f"pending_auth:{session_id}")  # Clean up
            return result
        else:
            return {"status": "pending"}
    else:
        return {"status": "expired"}

#Challenge related things
@app.get("/challenges") # List challenges  
def list_available_challs():
    pass

@app.get("/challenges/{id}") # Get challenge
def get_chall_by_id():
    pass

@app.get("/challenges/{id}/approve")

@app.post("/challenges/{id}/submit") # Submit solution
def submit_solution_by_id():
    pass