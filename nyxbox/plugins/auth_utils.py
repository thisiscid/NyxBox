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
from .utils import create_log, return_log_path, DAEMON_USER, SERVER_URL, USER_AGENT
import hashlib

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
    def __init__(self, auth_data, user_data, is_guest=False):
        super().__init__()
        self.auth_data = auth_data
        self.user_data = user_data
        self.is_guest = is_guest

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
            response = requests.get(f"{SERVER_URL}/auth/check-status/{self.session_id}", headers={ "User-Agent": USER_AGENT }).json()
            if response["status"] == "completed":
                self.polling = False
                self.save_tokens(
                    response["access_token"], 
                    response["user_data"], 
                    response["refresh_token"],
                    response["access_exp"],
                    response["refresh_exp"])
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

class LoginPage(ModalScreen):
    BINDINGS = [
        ("ctrl+q", "quit", "Quit")]
    def on_mount(self):
        self.is_login = False
        self.session_id = secrets.token_hex(16)
        self.brute_forcing = True
    
    def compose(self) -> ComposeResult:
        with Vertical(id="login_screen"):
            yield Label(f"{DAEMON_USER} Heya, welcome back!\n{DAEMON_USER} Click a button to sign in \n(preferably with the same account as last time!)", id="log_quit_text")
            with Vertical(id="switch_choice"):
                yield Rule()
                with Vertical():
                    with Horizontal(id="sign_up_buttons"):
                        yield Button.success("Sign up with Google", id="google_button")
                        yield Button.warning("Sign up with Github", id="github_button")
                        slack_button = Button.error("Sign in with slack", id="slack_button")
                        slack_button.styles.align_horizontal = "center"
                        # slack_button.styles.margin = "auto"  # vertically 1, horizontally centered
                        yield slack_button
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
                    data=requests.get(f"{SERVER_URL}/auth/google?session_id={self.session_id}", headers={ "User-Agent": USER_AGENT }).json()
                    if data.get("detail", None):
                        self.notify(
                            title="Uh oh, something went wrong!",
                            message=f"{DAEMON_USER} [b]There was a backend error! Error has been written to nyxbox-{datetime.today().strftime('%Y-%m-%d')}.log in ~/.nyxbox[/b]. Try again in a few seconds or contact Rainger on slack!",
                            severity="error",
                            timeout=5,
                            markup=True
                        )
                        log_dir = pathlib.Path.home() / ".nyxbox"
                        log_dir.mkdir(exist_ok=True)
                        # log_path = log_dir / "login.log"
                        create_log(return_log_path(), severity = "error", message=f"Backend failed, details: {data.get('detail')}")
                        return
                except Exception as e:
                    self.notify(
                        title="Uh oh, something went wrong!",
                        message=f"{DAEMON_USER} [b]There was an error! Error has been written to nyxbox-{datetime.today().strftime('%Y-%m-%d')}.log in ~/.nyxbox[/b]. Try again in a few seconds!",
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
                    data=requests.get(f"{SERVER_URL}/auth/github?session_id={self.session_id}", headers={ "User-Agent": USER_AGENT }).json()
                    if data.get("detail", None):
                        self.notify(
                            title="Uh oh, something went wrong!",
                            message=f"{DAEMON_USER} [b]There was a backend error! Error has been written to nyxbox-{datetime.today().strftime('%Y-%m-%d')}.log in ~/.nyxbox[/b]. Try again in a few seconds or contact Rainger on slack!",
                            severity="error",
                            timeout=5,
                            markup=True
                        )
                        log_dir = pathlib.Path.home() / ".nyxbox"
                        log_dir.mkdir(exist_ok=True)
                        create_log(return_log_path(), severity = "error", message=f"Backend failed, details: {data.get('detail')}")
                        return
                except Exception as e:
                    self.notify(
                        title="Uh oh, something went wrong!",
                        message=f"{DAEMON_USER} [b]There was an error! Error has been written to nyxbox-{datetime.today().strftime('%Y-%m-%d')}.log in ~/.nyxbox[/b]. Try again in a few seconds!",
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
            case 'slack_button':
                try:
                    data=requests.get(f"{SERVER_URL}/auth/slack?session_id={self.session_id}", headers={ "User-Agent": USER_AGENT }).json()
                    if data.get("detail", None):
                        self.notify(
                            title="Uh oh, something went wrong!",
                            message=f"{DAEMON_USER} [b]There was a backend error! Error has been written to nyxbox-{datetime.today().strftime('%Y-%m-%d')}.log in ~/.nyxbox[/b]. Try again in a few seconds or contact Rainger on slack!",
                            severity="error",
                            timeout=5,
                            markup=True
                        )
                        log_dir = pathlib.Path.home() / ".nyxbox"
                        log_dir.mkdir(exist_ok=True)
                        create_log(return_log_path(), severity = "error", message=f"Backend failed, details: {data.get('detail')}")
                        return
                except Exception as e:
                    self.notify(
                        title="Uh oh, something went wrong!",
                        message=f"{DAEMON_USER} [b]There was an error! Error has been written to nyxbox-{datetime.today().strftime('%Y-%m-%d')}.log in ~/.nyxbox[/b]. Try again in a few seconds!",
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
                slack_link = data.get("auth_url")
                state=webbrowser.open(slack_link)
                if not state or os.environ.get("CODESPACES"):
                    qr_pixels_obj = make_qr_pixels(slack_link)
                    if qr_pixels_obj:
                        self.app.push_screen(WaitingForAuthScreen(self.session_id, True, qr_pixels_obj)) # type: ignore
                    else:
                        self.notify(title="QR Error", message="Could not generate QR code.", severity="error")
                        self.app.push_screen(WaitingForAuthScreen(self.session_id, False)) 
                else:
                    self.app.push_screen(WaitingForAuthScreen(self.session_id))
            case 'guest_button': #TODO: is this even needed? Like the endpoint is unauthed
                # Ehhh its okay
                try:
                    data=requests.get(f"{SERVER_URL}/auth/guest", headers={"User-Agent": USER_AGENT}).json()
                    if data.get("detail", None):
                        self.notify(
                            title="Uh oh, something went wrong!",
                            message=f"{DAEMON_USER} [b]There was a backend error! Error has been written to nyxbox-{datetime.today().strftime('%Y-%m-%d')}.log in ~/.nyxbox[/b]. Try again in a few seconds or contact Rainger on slack!",
                            severity="error",
                            timeout=5,
                            markup=True
                        )
                        log_dir = pathlib.Path.home() / ".nyxbox"
                        log_dir.mkdir(exist_ok=True)
                        # log_path = log_dir / "login.log"
                        create_log(return_log_path(), severity = "error", message=f"Backend failed, details: {data.get('detail')}")
                        return
                except Exception as e:
                    self.notify(
                        title="Uh oh, something went wrong!",
                        message=f"{DAEMON_USER} [b]There was an error! Error has been written to nyxbox-{datetime.today().strftime('%Y-%m-%d')}.log in ~/.nyxbox[/b]. Try again in a few seconds!",
                        severity="error",
                        timeout=5,
                        markup=True
                    )
                    log_dir = pathlib.Path.home() / ".nyxbox"
                    log_dir.mkdir(exist_ok=True)
                    create_log(return_log_path(), severity = "error", message=e)
                    return
                # self.notify(f"Successfully got challenge. Details: {data}")
                self.brute_forcing = True
                i=0
                while self.brute_forcing:
                    attempt=hashlib.sha256((data["nonce"] + str(i)).encode()).digest()
                    bit_str = ''.join(f"{byte:08b}" for byte in attempt)
                    leading_zeros = len(bit_str) - len(bit_str.lstrip('0'))
                    if leading_zeros < data["difficulty"]:
                        i+=1
                    else:
                        self.brute_forcing = False
                        # self.notify(f"Successfully brute forced. Found {i} for {data["nonce"]}. Difficulty={data["difficulty"]}, result={bit_str}")
                        break

                try:
                    result=requests.post(f"{SERVER_URL}/auth/guest", json={"nonce": data["nonce"], "solution": i}, headers={"User-Agent": USER_AGENT}).json()
                    # self.notify(f"Successfuly brute forced. Server returned {result}")
                except Exception as e:
                    self.notify(
                        title="Uh oh, something went wrong!",
                        message=f"{DAEMON_USER} [b]There was an error! Error has been written to nyxbox-{datetime.today().strftime('%Y-%m-%d')}.log in ~/.nyxbox[/b]. Try again in a few seconds!",
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
                # jwt_response = result["jwt"] # What is this even supposed to do
                # We should have special handling. Why don't we write it to a special file?
                # Nvm thats stupid
                auth_dir = pathlib.Path.home() / ".nyxbox"
                auth_dir.mkdir(exist_ok=True)
                guest_save_tokens(result["access_token"], result["guest_id"], result["access_exp"])
                self.app.pop_screen()
                # with open(auth_dir / "auth.json", "w") as file:
                #     json.dump(result, file)
                # self.app.guest = True

    def action_quit(self):
        self.app.exit()

def read_user_data() -> dict:
    auth_dir = pathlib.Path.home() / ".nyxbox"
    try:
        auth_dir = pathlib.Path.home() / ".nyxbox"
        if pathlib.Path.is_dir(auth_dir):
            if pathlib.Path.exists(auth_dir / "user.json"):
                with open(auth_dir / "user.json", "r") as f:
                    user_data = json.load(f)
                    return user_data
            else:
                return {}
        else:
            return {"error": "Auth directory not found"}
    except Exception as e:
        create_log(auth_dir / f"nyxbox-{datetime.today().strftime('%Y-%m-%d')}.log", severity = "error", message=e)
        return {"error": e}

def read_auth_data() -> dict:
    auth_dir = pathlib.Path.home() / ".nyxbox"
    try:
        if pathlib.Path.is_dir(auth_dir):
            with open(auth_dir / "auth.json", "r") as f:
                auth_data=json.load(f)
                if auth_data.get("is_guest", False):
                    auth_data["access_expiry"] = datetime.fromisoformat(auth_data["access_expiry"])
                else:
                    auth_data["access_expiry"] = datetime.fromisoformat(auth_data["access_expiry"])
                    auth_data["refresh_expiry"] = datetime.fromisoformat(auth_data["refresh_expiry"])
                return auth_data
        else:
            return {"error": "Auth directory not found"}
    except Exception as e:
        create_log(auth_dir / f"nyxbox-{datetime.today().strftime('%Y-%m-%d')}", severity = "error", message=e)
        return {"error": e}

class ValidateAuth():
    def __init__(self, app_instance: App, root_path):
        # self.token = token
        self.app_instance = app_instance
        self.root_path = root_path
        # self.is_server = is_server

    async def check_refresh_token(self, refresh_token) -> dict:
        refresh_url = SERVER_URL + "/auth/refresh"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(refresh_url, json={'refresh_token': refresh_token}, headers={ "User-Agent": USER_AGENT })
            except Exception as e:
                return {"access_token": None,
                "jwt": None,
                "error": e,
                "failed": True}
            if response.status_code == 200:
                response_data = response.json()
                return {"access_token": response_data.get("user_jwt"),
                        "refresh_token": response_data.get("refresh_jwt"), 
                        "access_expiry": response_data.get("access_exp"),
                        "refresh_expiry": response_data.get("refresh_exp"), 
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
        auth_file = self.root_path / "auth.json"
        user_file = self.root_path / "user.json"
        if not auth_file.exists() or not user_file.exists():
            create_log(return_log_path(), severity="info", message="auth.json or user.json not found. Pushing LoginPage.")
            self.app_instance.push_screen(LoginPage())
            return 
        with open(user_file, 'r') as f:
            user_data = json.load(f)
        with open(auth_file, 'r') as f:
            auth_data = json.load(f)
            if auth_data.get("is_guest", None):
                try:
                    os.remove(auth_file)
                    os.remove(user_file)
                    self.app_instance.push_screen(LoginPage())
                except Exception as e:
                    create_log(return_log_path, severity="error", message=f"Error: {e}")
                    self.app_instance.notify(
                        title="Uh oh!",
                        message=f"{DAEMON_USER} [b]Couldn't remove old guest data![/]",
                        severity="error",
                        timeout=5,
                        markup=True
                    )
                    self.app_instance.push_screen(LoginPage())
        if pathlib.Path.exists(auth_file) and pathlib.Path.exists(user_file):
            try:
                with open(auth_file, 'r') as f:
                    auth_data = json.load(f)
                    auth_data["access_expiry"] = datetime.fromisoformat(auth_data["access_expiry"])
                    auth_data["refresh_expiry"] = datetime.fromisoformat(auth_data["refresh_expiry"])
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
                create_log(return_log_path, severity="error", message=f"Error: {e}")
                try:
                    os.remove(self.root_path / "auth.json")
                    os.remove(self.root_path / "auth.json")
                except Exception as e:
                    create_log(return_log_path, severity="error", message=f"Error: {e}")
                self.app_instance.push_screen(LoginPage())
                return
            expiration = auth_data.get("access_expiry")
            current_time = datetime.now(timezone.utc).timestamp()
            if expiration.timestamp() <= current_time:
                valid_refresh = await self.check_refresh_token(auth_data.get('refresh_token'))
                if valid_refresh.get("failed", True):
                    self.app_instance.notify(
                    title="Hello!",
                    message=f"{DAEMON_USER} [b]For your security, you've been logged out. Log in again![/]",
                    severity="error",
                    timeout=5,
                    markup=True
                )
                    try:
                        os.remove(self.root_path / "auth.json")
                        os.remove(self.root_path / "user.json")
                    except Exception as e:
                        create_log(return_log_path, severity="error", message=f"Error: {e}")
                    self.app_instance.push_screen(LoginPage())
                else:
                    # self.app_instance.
                    self.app_instance.notify(
                    f"{DAEMON_USER} Welcome, {user_data.get('name', 'User')}!", 
                    severity="information")
                    self.save_tokens(
                        valid_refresh.get("access_token") or "",
                        valid_refresh.get("user_data") or user_data,
                        valid_refresh.get("refresh_jwt") or "",
                        valid_refresh.get("user_jwt_expiry") or 0,
                        valid_refresh.get("refresh_expiry") or 0
                    )
    
    def save_tokens(self, access_token: str, user_data: dict, refresh_token: str, access_exp: int, refresh_exp: int):
        auth_dir = pathlib.Path.home() / ".nyxbox"
        auth_dir.mkdir(exist_ok=True)
        
        auth_data = {
            "access_token": access_token,
            "user_data": user_data,
            "refresh_token": refresh_token,
            "timestamp": datetime.now().timestamp(),
            "access_expiry": access_exp,
            "refresh_expiry": refresh_exp
        }
        
        with open(auth_dir / "auth.json", "w") as f:
            json.dump(auth_data, f)
        with open(auth_dir / "user.json", "w") as f:
            json.dump(user_data, f)
        self.app_instance.notify(
            f"{DAEMON_USER} Welcome, {user_data.get('name', 'User')}!", 
            severity="information")
        self.app_instance.post_message(AuthComplete(auth_data, user_data))

# not technically authentication related but its config so yknow what we ball
class GetConfig():
    def __init__(self, root_path):
        self.root_path = root_path

def guest_save_tokens(guest_token: str, guest_id: str, exp: str):
        try:
            auth_dir = pathlib.Path.home() / ".nyxbox"
            auth_dir.mkdir(exist_ok=True)
            
            auth_data = {
                "access_token": guest_token,
                "user_data": None,
                "refresh_token": None,
                "timestamp": datetime.now().timestamp(),
                "access_expiry": exp,
                "refresh_expiry": None,
                "is_guest": True,
            }
            with open(auth_dir / "auth.json", "w") as f:
                json.dump(auth_data, f)
            with open(auth_dir / "user.json", "w") as f:
                json.dump({"id": guest_id, "name": "Guest", "email": None}, f)
            return True
        except Exception as e:
            create_log(return_log_path, severity="error", message=e)
            return False