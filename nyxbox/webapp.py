# server.py
import os
import json
import uuid
import pathlib

SESSION_DIR = pathlib.Path.home() / ".config" / "nyxbox" / "sessions"
SESSION_JSON = SESSION_DIR / "sessions.json"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
if not SESSION_JSON.exists():
    with open(SESSION_JSON, "w") as f:
        json.dump({}, f)
# from aiohttp import web
# from textual_serve.server import Server

# SESSION_DIR   = Path("/etc/nyxbox/sessions")
# SESSION_JSON  = SESSION_DIR / "sessions.json"
# SESSION_DIR.mkdir(exist_ok=True)
# if not SESSION_JSON.exists():
#     SESSION_JSON.write_text("{}")

def load_sessions() -> dict:
    return json.loads(SESSION_JSON.read_text())

def save_sessions(session: dict) -> None:
    with open(SESSION_JSON, "rw") as f:
        json.dump(session, f)

# @web.middleware
# async def attach_or_issue_token(request, handler):
#     # Load or mint a token
#     sessions = load_sessions()
#     token = request.cookies.get("session")
#     if token in sessions:
#         fn = sessions[token]
#         if fn:
#             path = SESSION_DIR / fn
#             if path.exists():
#                 request["auth_filepath"] = str(path)
#     else:
#         token = uuid.uuid4().hex
#         sessions[token] = ""  # not yet tied to a file
#         save_sessions(sessions)
#         request["new_session_token"] = token

#     resp = await handler(request)

#     # Set cookie if we issued a new token
#     new_tok = request.get("new_session_token")
#     if new_tok:
#         resp.set_cookie(
#             "session", new_tok,
#             httponly=True, secure=True, samesite="Strict",
#         )
#     return resp

# class JsonSessionServer(Server):
#     # Note the async signature
#     async def _make_app(self):
#         # await the parent to get the real app
#         app = await super()._make_app()
#         app.middlewares.insert(0, attach_or_issue_token)
#         return app

#     # _ws_handler is already async, so this stays the same
#     async def _ws_handler(self, request):
#         auth_file = request.get("auth_filepath", "")
#         env       = os.environ.copy()
#         env["NYXBOX_AUTH_FILE"] = auth_file
#         return await super()._ws_handler(request, proc_env=env)

# if __name__ == "__main__":
#     server = JsonSessionServer("python -m nyxbox.main", host="0.0.0.0", port=8000)
#     server.serve()
