import pathlib
from datetime import datetime, timezone
import json
import base64
import httpx
import requests
import asyncio
from .utils import create_log, SERVER_URL

def read_user_data() -> dict:
    auth_dir = pathlib.Path.home() / ".nyxbox"
    try:
        auth_dir = pathlib.Path.home() / ".nyxbox"
        if pathlib.Path.is_dir(auth_dir):
            with open(auth_dir / "auth.json", "r") as f:
                return json.load(f)
        else:
            return {"error": "Auth directory not found"}
    except Exception as e:
        create_log(auth_dir / f"nyxbox-{datetime.today().strftime('%Y-%m-%d')}.log", severity = "error", message=e)
        return {"error": e}
class ValidateAuth():
    def __init__(self, token, app_instance, root_path):
        self.token = token
        self.app_instance = app_instance
        self.root_path = root_path
    async def check_refresh_token(self, refresh_token) -> dict:
        refresh_url = SERVER_URL + "/auth/refresh"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(refresh_url, data={'refresh_jwt': refresh_token})
            except Exception as e:
                return {"access_token": None,
                "jwt": None,
                "error": e,
                "failed": True}
            if response.status_code == 200:
                response_data = response.json()
                return {"access_token": response_data.get("refresh_jwt"), 
                        "jwt": response_data.get("user_jwt"), 
                        "failed": False}
            else:
                log_path = self.root_path / f"nyxbox-{datetime.today().strftime('%Y-%m-%d')}.log"
                create_log(log_path, 
                           message=f"Server returned {response.status_code} while refreshing token",
                           severity="error")
                return {"access_token": None,
                "jwt": None,
                "failed": True,
                "error": response}
    async def perform_auth_check(self, app_instance, root_path):
        """Check whether the user is authenticated or not"""
        auth_path = root_path / "auth.json"
        user_path = root_path / "user.json"
        if pathlib.Path.exists(auth_path) and pathlib.Path.exists(user_path):
            try:
                with open(auth_path, 'r') as f:
                    auth_data = json.load(auth_path)
            except Exception as e:
                return {"error": e}
            jwt_payload = auth_data.get("access_token").split(".")[1]
            while (len(jwt_payload) % 4) != 0:
                jwt_payload=jwt_payload+"="
            jwt_decoded_payload = base64.urlsafe_b64decode(jwt_payload)
            jwt_data = json.loads(jwt_decoded_payload)
            expiration = jwt_data.get("exp", 0)
            current_time = datetime.now(timezone.utc).timestamp()
            if expiration <= current_time:
                valid_refresh = await self.check_refresh_token(auth_data.get('refresh_token'))
                return valid_refresh


