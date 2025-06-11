import pathlib
from datetime import datetime
import json
from .utils import create_log

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

async def perform_auth_check(app_instance, path):
    """Check whether the user is authenticated or not"""
    pass