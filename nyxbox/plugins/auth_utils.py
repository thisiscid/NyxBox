from textual.screen import ModalScreen
from textual.app import App, ComposeResult
from textual.widgets import Static, Label, Button, Rule
from textual.containers import Horizontal, Vertical
from textual.message import Message
import pathlib
from datetime import datetime, timezone
import json
import base64
import httpx
import requests
import secrets
import webbrowser
from qrcode.image.pil import PilImage
import qrcode
from rich_pixels import Pixels
import os
from .utils import create_log, return_log_path, DAEMON_USER, SERVER_URL
# Screens used to actually auth a user
def make_qr_pixels(data: str) -> Pixels | None:
    """
    Generates a QR code for the given data and returns it as a rich_pixels.Pixels object.
    Returns None if QR code generation fails.
    """
    try:
        qr = qrcode.QRCode(
            box_size=1,
            border=1,   
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(image_factory=PilImage)
        pil_img = img.get_image()  # Convert PilImage to PIL.Image.Image
        return Pixels.from_image(pil_img) 
    except Exception as e:
        # Optionally log the error e
        print(f"Error generating QR pixels: {e}")
        return None
    
class AuthComplete(Message):
    def __init__(self, auth_data, user_data):
        super().__init__()
        self.auth_data = auth_data
        self.user_data = user_data

class WaitingForAuthScreen(ModalScreen):
    def __init__(self, session_id: str, is_qr: bool = False, qr_image: str = ""):
        super().__init__()
        self.session_id = session_id
        self.polling = True
        self.has_notified=False
        self.is_qr = is_qr
        if qr_image: # Check for the new parameter name
            self.qr_image = qr_image
        else:
            self.qr_image = None 
        
    BINDINGS = [
            ("ctrl+q", "quit", "Quit")]
    def compose(self) -> ComposeResult:
        if not self.is_qr:
            with Vertical(id="waiting_for_login_container"):
                yield Label(f"{DAEMON_USER} Waiting for authentication...", id="log_auth_wait_text")
                yield Label(f"{DAEMON_USER} Complete logging in in your browser!", id="log_auth_wait_text2")
                yield Button("Cancel", id="cancel_auth")
        else:
            with Vertical(id="waiting_for_login_container"):
                yield Label(f"{DAEMON_USER} Waiting for authentication...", id="log_auth_wait_text")
                yield Label(f"{DAEMON_USER} Complete logging in by scanning the QR code!", id="log_auth_wait_text2")
                if self.is_qr and self.qr_image:
                    yield Static(self.qr_image) #TODO: Switch to using rich-pixels
                else:
                    yield Label(f"{DAEMON_USER} Failed to generate QR code! Try cancelling!")
                yield Button("Cancel", id="cancel_auth")


    def on_button_pressed(self, event: Button.Pressed):
        match event.button.id:
            case "quit_app_login":
                self.action_quit()
            case "cancel_auth":
                self.polling = False
                self.dismiss()
    def action_quit(self):
        self.app.exit()
    def on_mount(self):
        self.set_timer(2.0, self.check_auth_status)

    async def check_auth_status(self):
        if not self.polling:
            return
        try:
            response = requests.get(f"{SERVER_URL}/auth/check-status/{self.session_id}").json()
            if response["status"] == "completed":
                self.polling = False
                self.save_tokens(
                    response["access_token"], 
                    response["user_data"], 
                    response["refresh_token"],
                    response["user_jwt_expiry"],
                    response["refresh_expiry"])
                self.app.pop_screen()
                self.app.pop_screen()
                return
            else:
                self.set_timer(2.0, self.check_auth_status)
        except Exception as e:
            if not self.has_notified:
                self.notify(
                        title="Uh oh, something went wrong!",
                        message=f"{DAEMON_USER} [b]There was an error! Error has been written to login.log in ~/.nyxbox[/b]",
                        severity="warning",
                        timeout=5,
                        markup=True
                    )
            else:
                pass
            self.has_notified=True
            create_log(return_log_path(), severity="error", message=e)
            if self.polling:
                self.set_timer(2.0, self.check_auth_status)

    def save_tokens(self, access_token: str, user_data: dict, refresh_token: str, access_exp: int, refresh_exp: int):
        # Save to local storage
        auth_dir = pathlib.Path.home() / ".nyxbox"
        auth_dir.mkdir(exist_ok=True)
        
        auth_data = {
            "access_token": access_token,
            "user_data": user_data,
            "refresh_token": refresh_token,
            # "timestamp": time.time(),
            "access_expiry": access_exp,
            "refresh_expiry": refresh_exp
        }
        
        with open(auth_dir / "auth.json", "w") as f:
            json.dump(auth_data, f)
        with open(auth_dir / "user.json", "w") as f:
            json.dump(user_data, f)
        self.notify(
            f"{DAEMON_USER} Welcome, {user_data.get('name', 'User')}!", 
            severity="information")
        self.app.post_message(AuthComplete(auth_data, user_data))
    
#TODO: Remember to send a session id! Check your API for what you need to send!
class LoginPage(ModalScreen):
    BINDINGS = [
        ("ctrl+q", "quit", "Quit")]
    def on_mount(self):
        self.is_login = False
        self.session_id = secrets.token_hex(16)
    def compose(self) -> ComposeResult:
        with Vertical(id="login_screen"):
            yield Label(f"{DAEMON_USER} Heya, welcome back!\n{DAEMON_USER} Click a button to sign in \n(preferably with the same account as last time!)", id="log_quit_text")
            with Vertical(id="switch_choice"):
                yield Rule()
                with Horizontal(id="sign_up_buttons"):
                    yield Button.success("Sign up with Google", id="google_button")
                    yield Button.warning("Sign up with Github", id="github_button")
                yield Rule()
                yield Label(f"{DAEMON_USER} Have an account?", id="have_account")
                with Vertical(id="login_buttons"):
                    yield Button("Switch to Login", id="switch_button")
                    yield Button("Use as guest", id="guest_button")
                    yield Button("Quit app", id="quit_app_login")

    def on_button_pressed(self, event: Button.Pressed):
        match event.button.id:
            case "quit_app_login":
                self.action_quit()
            case 'switch_button':
                google_button = self.query_one("#google_button", Button)
                github_button = self.query_one("#github_button", Button)
                switch_button = self.query_one("#switch_button", Button)
                have_account = self.query_one("#have_account", Label)
                top_label = self.query_one("#log_quit_text", Label)
                if not self.is_login:
                    google_button.label = "Log in with Google"
                    github_button.label = "Log in with Github"
                    switch_button.label = "Switch to Signup"
                    have_account.update(f"{DAEMON_USER} Need an account?")
                    top_label.update(f"{DAEMON_USER} Heya, welcome back!\n{DAEMON_USER} Click a button to sign in (preferably with the same account as last time!)")
                    self.is_login = True
                else:
                    google_button.label = "Sign up with Google"
                    github_button.label = "Sign up with Github"
                    switch_button.label = "Switch to Login"
                    have_account.update(f"{DAEMON_USER} Have an account?")
                    top_label.update(f"{DAEMON_USER} Heya, I'm nyx, welcome to NyxBox!\n{DAEMON_USER} Click an option to sign in!")
                    self.is_login = False
            case 'google_button':
                try:
                    data=requests.get(f"{SERVER_URL}/auth/google?session_id={self.session_id}").json()
                except Exception as e:
                    self.notify(
                        title="Uh oh, something went wrong!",
                        message=f"{DAEMON_USER} [b]There was an error! Error has been written to login.log in ~/.nyxbox[/b]",
                        severity="error",
                        timeout=5,
                        markup=True
                    )
                    log_dir = pathlib.Path.home() / ".nyxbox"
                    log_dir.mkdir(exist_ok=True)
                    # log_path = log_dir / "login.log"
                    create_log(return_log_path(), severity = "error", message=e)
                    return
                google_link = data.get("auth_url")
                state=webbrowser.open(google_link)
                if not state or os.environ.get("CODESPACES"): 
                    qr_pixels_obj = make_qr_pixels(google_link)
                    if qr_pixels_obj:
                        self.app.push_screen(WaitingForAuthScreen(self.session_id, True, qr_pixels_obj)) # type: ignore
                    else:
                        self.notify(title="Shoot...", 
                            message=f"{DAEMON_USER} Could not generate QR code.", 
                            severity="error")
                        self.app.push_screen(WaitingForAuthScreen(self.session_id, False)) # Show without QR
                else:
                    self.app.push_screen(WaitingForAuthScreen(self.session_id))
            case 'github_button':
                try:
                    data=requests.get(f"{SERVER_URL}/auth/github?session_id={self.session_id}").json()
                except Exception as e:
                    self.notify(
                        title="Uh oh, something went wrong!",
                        message=f"{DAEMON_USER} [b]There was an error! Error has been written to login.log in ~/.nyxbox[/b]. Try again in a few seconds!",
                        severity="error",
                        timeout=5,
                        markup=True
                    )
                    log_dir = pathlib.Path.home() / ".nyxbox"
                    log_dir.mkdir(exist_ok=True)
                    create_log(return_log_path(), severity = "error", message=e)
                    # log_path = log_dir / "login.log"
                    # with log_path.open("a") as f:
                    #     f.write(f"ERROR: {e}\n")
                    return
                github_link = data.get("auth_url")
                state=webbrowser.open(github_link)
                if not state or os.environ.get("CODESPACES"): # Simplified condition
                    qr_pixels_obj = make_qr_pixels(github_link)
                    if qr_pixels_obj:
                        self.app.push_screen(WaitingForAuthScreen(self.session_id, True, qr_pixels_obj)) # type: ignore
                    else:
                        self.notify(title="QR Error", message="Could not generate QR code.", severity="error")
                        self.app.push_screen(WaitingForAuthScreen(self.session_id, False)) # Show without QR
                else:
                    self.app.push_screen(WaitingForAuthScreen(self.session_id))
    def action_quit(self):
        self.app.exit()

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
    def __init__(self, app_instance: App, root_path):
        # self.token = token
        self.app_instance = app_instance
        self.root_path = root_path
    async def check_refresh_token(self, refresh_token) -> dict:
        refresh_url = SERVER_URL + "/auth/refresh"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(refresh_url, json={'refresh_token': refresh_token})
            except Exception as e:
                return {"access_token": None,
                "jwt": None,
                "error": e,
                "failed": True}
            if response.status_code == 200:
                response_data = response.json()
                return {"access_token": response_data.get("refresh_jwt"), 
                        "jwt": response_data.get("user_jwt"), 
                        "access_exp": response_data.get("refresh_expiry"),
                        "jwt_exp": response_data.get("user_jwt_expiry"),
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

    async def perform_auth_check(self):
        """Check whether the user is authenticated or not"""
        auth_path = self.root_path / "auth.json"
        user_path = self.root_path / "user.json"
        if pathlib.Path.exists(auth_path) and pathlib.Path.exists(user_path):
            try:
                with open(auth_path, 'r') as f:
                    auth_data = json.load(f)
            except Exception as e:
                return {"error": e}
            jwt_payload = auth_data.get("access_token").split(".")[1]
            # make sure that we can actually decode the jwt_payload
            try:
                while (len(jwt_payload) % 4) != 0:
                    jwt_payload=jwt_payload+"="
                jwt_decoded_payload = base64.urlsafe_b64decode(jwt_payload)
                jwt_data = json.loads(jwt_decoded_payload)
            except Exception as e:
                self.app_instance.notify(
                    title="Uh oh!",
                    message=f"{DAEMON_USER} [b]Current login data is corrupted. Log in again please![/]",
                    severity="error",
                    timeout=5,
                    markup=True
                )
                self.app_instance.push_screen(LoginPage())
                return
            expiration = auth_data.get("access_exp")
            current_time = datetime.now(timezone.utc).timestamp()
            if expiration <= current_time:
                valid_refresh = await self.check_refresh_token(auth_data.get('refresh_token'))
                if valid_refresh.get("failed", True):
                    pass
                    # self.app_instance.push_screen()
                # return valid_refresh

