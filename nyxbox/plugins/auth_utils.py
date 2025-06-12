import pathlib
from datetime import datetime, timezone
import json
import base64
import httpx
import requests
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
    async def check_refresh_token(self):
        refresh_url = SERVER_URL + "/auth/refresh"
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



