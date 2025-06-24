import os
import random
import json
import sys
import time
import pathlib
import re
import requests
import secrets
import webbrowser
# import qrcode
from .plugins import challenge_view, challenge_loader
from .plugins.editor_tools import Editor, EditorClosed, LanguageSelected, CustomPathSelected, TestResultsWidget
from .plugins.code_runners.java_runner import run_java_code
from .plugins.utils import create_log, make_qr_pixels, DAEMON_USER, SERVER_URL
from .plugins.auth_utils import read_user_data, read_auth_data, ValidateAuth, LoginPage, AuthComplete
from rich.text import Text
from textual import on
from textual.screen import Screen, ModalScreen
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static, TextArea, Label, Button, Digits, Input, ListView, DataTable, Rule
from textual.containers import Horizontal, Vertical
from textual.message import Message
from importlib.resources import files
from importlib.metadata import version, PackageNotFoundError
from datetime import datetime
#TODO: Make sure the auth flow works since we're importing from a diff file
try:
    nyxbox_version = version("nyxbox")
except PackageNotFoundError:
    nyxbox_version = None
class VendAnimation(Static):
    pass # I don't think this is getting done for a good while
#TODO: Move most of this auth stuff to a seperate file (auth_utils.py)
# class AuthComplete(Message):
#     def __init__(self, auth_data, user_data):
#         super().__init__()
#         self.auth_data = auth_data
#         self.user_data = user_data

class ProfileDetailsScreen(ModalScreen):
    def __init__(self) -> None:
        super().__init__()
        self.user_data = read_user_data()

    def compose(self) -> ComposeResult:
        with Vertical(id="profile_details_container"):
            MESSAGE_CHOICES=[
                f"{DAEMON_USER} Let's see what I have on you...",
                f"{DAEMON_USER} What have we got here?",
                f"{DAEMON_USER} Maybe theres something juicy in here?",
                f"{DAEMON_USER} Pulling up your information now!"
            ]
            if self.user_data and not self.user_data.get('error', None):
                # user_info = self.user_data.get('user_data', {})
                yield Label(random.choice(MESSAGE_CHOICES))
                yield Rule()
                yield Label(f"Name: {self.user_data.get('name', 'N/A')}")
                yield Label(f"Email: {self.user_data.get('email', 'N/A')}")
                # yield Label(f"Provider: {user_info.get('provider', 'N/A')}")
            else:
                yield Label(f"{DAEMON_USER} Uh oh, failed to get user data!")
            # Add more fields as needed
            yield Rule()
            yield Button("Close", id="close_profile")
    
    def on_button_pressed(self, event: Button.Pressed):
        match event.button.id:
            case "close_profile":
                self.app.pop_screen()
    
class SearchComplete(Message):
    """Message passed upon the user selecting a challenge in SearchForProblem"""
    def __init__(self, challenge):
        super().__init__()
        self.challenge = challenge

class ConfirmExit(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="quit_screen"):
            yield Label("Are you sure you want to quit?", id="quit_text")
            with Horizontal(id="quit_buttons"):
                yield Button.success("Yes", id="yes_button")
                yield Button.error("No", id="no_button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "yes_button":
                self.app.exit()
            case "no_button":
                self.app.pop_screen()

class SearchForProblem(Screen):
    def on_mount(self) -> None:
        self.added_columns=False
        challenges=self.query_one("#chall_list", DataTable)
        if not self.added_columns:
            challenges.add_column("Name")
            challenges.add_column("Description")
            challenges.add_column("Difficulty")
        self.added_columns=True
        challenge_dir = files("nyxbox.challenges")
        files_list = [f for f in challenge_dir.iterdir() if f.is_file()]
        self.files_list = files_list
        self.placeholder = ["Start typing to search for a challenge."]
        
        terminal_width = self.app.size.width
        reserved_space = 45
        available_description_space = max(20, terminal_width - reserved_space)
        
        for file in files_list:
            file_dict = self.grab_metadata(file)
            name = file_dict.get("name") or ""
            description = file_dict.get("description") or ""
            difficulty = file_dict.get("difficulty") or ""
            if len(description) > available_description_space:
                truncated_description = description[:available_description_space-3] + "..."
            else:
                truncated_description = description
#             
            challenges.add_row(name, truncated_description, difficulty)
            # rows.append((str(name).title(), str(description), str(difficulty)))
        self.refresh()
        
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Input(placeholder="Search...", id="search_bar")
            # self.challenges = DataTable(id="chall_list")
            # self.challenges.loading=True
            yield DataTable(id="chall_list", cursor_type="row")
            self.challenge_widget = challenge_view.UserChallView()
            self.challenge_widget.id = "challengeview"
            yield self.challenge_widget
            with Horizontal():
                yield Button("Quit", variant="error", id="search_quit")
                yield Button("Select Challenge", variant="success", id="search_select")
        yield Footer()

    def grab_metadata(self, file) -> dict:
        with file.open("r") as file_content:
            return json.load(file_content)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "search_quit":
                self.app.pop_screen()
            case "search_select":
                datatable = self.query_one("#chall_list", DataTable)
                current_row = datatable.get_row_at(datatable.cursor_row)
                challenge_name = current_row[0]
                if current_row:
                    for file in self.files_list:
                        try:
                            file_dict = self.grab_metadata(file)
                            if file_dict.get("name") == challenge_name:
                                self.app.pop_screen()
                                self.notify(
                                title="I got you!",
                                message=f"{DAEMON_USER} [b]Successfully selected {challenge_name}![/b]",
                                severity="information",
                                timeout=5,
                                markup=True
                            )
                                self.post_message(SearchComplete(file_dict))
                        except Exception:
                            pass

    def on_data_table_row_highlighted(self, Message) -> None:
        datatable = self.query_one("#chall_list", DataTable)
        if datatable.cursor_row is not None:
            selected_data = datatable.get_row_at(datatable.cursor_row)
            challenge_name = selected_data[0]
            for file in self.files_list:
                file_dict = self.grab_metadata(file)
                if file_dict.get("name") == challenge_name:
                    self.challenge_widget.update_chall(file_dict)
                    break
        return
    
    def on_input_changed(self, Message) -> None:
        datatable = self.query_one("#chall_list", DataTable)
        search_input = self.query_one("#search_bar", Input)
        query = search_input.value
        datatable.clear()
        item_found=False
        
        terminal_width = self.app.size.width
        reserved_space = 45
        available_description_space = max(20, terminal_width - reserved_space)
        
        for file in self.files_list:
            file_dict = self.grab_metadata(file)
            name = file_dict.get("name", "")
            description = file_dict.get("description", "")
            difficulty = file_dict.get("difficulty", "")
            
            if len(description) > available_description_space:
                truncated_description = description[:available_description_space-3] + "..."
            else:
                truncated_description = description
            
            if query.lower() in name.lower():
                datatable.add_row(name, truncated_description, difficulty)
                item_found=True
        if not item_found:
            datatable.add_row("No challenges found matching your search.")
class NyxBox(App):
    CSS_PATH = str(files("nyxbox").joinpath("styles.tcss"))
    BINDINGS = [("v", "vend_challenge", "Vend a new challenge!"), 
                ("e", "edit_solution", "Edit solution"), 
                ("s", "search_button", "Search"), 
                ("ctrl+q", "quit_app", "Quit app"),
                ("p", "view_profile", "View Profile")]
    TITLE = f"NyxBox {nyxbox_version}" if nyxbox_version else "NyxBox"
    # Define some consts so we don't have to do this every time we want to show or hide a widget
    BUTTON_PANEL_ID = "button_panel"
    CHALLENGE_VIEW_ID = "challengeview"
    EDITOR_ID = "editor"

    def on_mount(self) -> None:
        """Initialize variables to be used later and other stuff"""
        self.editor_opened = False
        self.has_vended = False
        self.current_challenge = None
        self.nyx_path = pathlib.Path.home() / ".nyxbox"
        try: #TODO: Implement checking for 1. if JWT expired, 2. if refresh token is expired, 3. force reauth if both of those two are met
            # I think the above is done
            auth_validator = ValidateAuth(self, self.nyx_path)
            self.run_worker(auth_validator.perform_auth_check(), exclusive=True)
            # if pathlib.Path.exists(pathlib.Path.home() / ".nyxbox" / "auth.json"):
            #     nyx_path = pathlib.Path.home() / ".nyxbox"
            #     auth_path = nyx_path / "auth.json"
            #     user_path = nyx_path / "user.json"
            #     with open(auth_path) as f:
            #         self.auth_data = json.load(f)
            #     with open(user_path) as f:
            #         self.user_data = json.load(f)
            #     self.notify(
            #     f"{DAEMON_USER} Welcome, {self.user_data.get('name', 'User')}!", 
            #     severity="information")
            # else:
            #     self.app.push_screen(LoginPage()) 
        except Exception as e:
            log=create_log(self.nyx_path / f"nyxbox-{datetime.today().strftime('%Y-%m-%d')}", severity = "error", message=e)
            if log:
                self.notify(
                    title="Uh oh!",
                    message=f"{DAEMON_USER} [b]Encountered critical error reading auth files: {log}[/b]",
                    severity="information",
                    timeout=5,
                    markup=True
                )
            else:
                self.notify(
                    title="Uh oh!",
                    message=f"{DAEMON_USER} [b]Encountered critical error reading auth files: {e}[/b]",
                    severity="information",
                    timeout=5,
                    markup=True
                )
            self.app.push_screen(LoginPage())
        try: 
            if pathlib.Path.exists(pathlib.Path.home() / ".nyxbox" / ".config"):
                config_path = pathlib.Path.home() / ".nyxbox" / ".config"
                with open(config_path, 'r') as config_file:
                    self.config_items = config_file.readlines()
        except Exception as e:
            log=create_log(self.nyx_path / f"nyxbox-{datetime.today().strftime('%Y-%m-%d')}", severity = "error", message=e)
            if log:
                self.notify(
                    title="Uh oh!",
                    message=f"{DAEMON_USER} [b]Encountered critical error reading config files: {log}[/b]",
                    severity="information",
                    timeout=5,
                    markup=True
                )
            else:
                self.notify(
                    title="Uh oh!",
                    message=f"{DAEMON_USER} [b]Encountered critical error reading config files: {e}[/b]",
                    severity="information",
                    timeout=5,
                    markup=True
                )
            self.app.push_screen(LoginPage())
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        with Horizontal():
            self.challenge_widget = challenge_view.UserChallView()
            self.challenge_widget.id = "challengeview"
            yield self.challenge_widget
            with Vertical(id="button_panel") as panel:
                panel.border_title = "buttons!"
                yield Label("Price (in brownie points):")
                yield Digits("0.00")
                yield Button.warning("Search for item", id="search_button")
                yield Button("View Profile", id="profile_button")
                yield Button.success("Vend item", id="vend_button")
                button_edit = Button.success("Begin coding!", id="edit_button")
                button_edit.display = False
                yield button_edit
                yield Button.error("Quit", id="quit_button")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "quit_button":
                self.action_quit_app()
            case "search_button":
                self.action_search_button()
            case "vend_button":
                self.action_vend_challenge()
            case "edit_button":
                self.action_edit_solution()
            case "profile_button":
                self.action_view_profile()


    def on_editor_closed(self, message: EditorClosed) -> None:
        self.pop_screen()
        self.get_widget_by_id('button_panel').display = True
        self.editor_opened = False

    def action_view_profile(self) -> None:
        self.push_screen(ProfileDetailsScreen())

    def action_quit_app(self) -> None:
        self.push_screen(ConfirmExit())

    def action_search_button(self) -> None:
        self.push_screen(SearchForProblem())
    def action_edit_solution(self) -> None:
        """Allows user to edit a challenge, loads instance then displays"""
        self.editor_instance = Editor()
        self.editor_instance.get_and_update_chall(self.current_challenge)
        if not self.has_vended:
            self.notify(
                    title="Theres no challenge...",
                    message=f"{DAEMON_USER} [b]Please vend a challenge before trying to open the editor![/b]",
                    severity="warning",
                    timeout=5,
                    markup=True
                )
            return
        if not self.editor_opened:
            if hasattr(self, 'current_challenge'):
                self.editor_opened=True
                #editor_instance.load_challenge(self.current_challenge)
                self.editor_instance.id = "editor"
                #editor_instance.challenge_view.update_chall(self.current_challenge)
                self.push_screen(self.editor_instance)
                #self.get_widget_by_id('button_panel').display = False
            else:
                self.notify(
                    title="Theres no challenge...",
                    message=f"{DAEMON_USER} [b]Please vend a challenge before trying to open the editor![/b]",
                    severity="warning",
                    timeout=5,
                    markup=True
                )
        else:
            self.notify(
                    title="Really?",
                    message=f"{DAEMON_USER} [b]Can't open editor twice! Quit first! Also, something probably wen't wrong, open an issue![/b]",
                    severity="error",
                    timeout=5,
                    markup=True
                )
            # This was back when the editor buttons were there always. If this happens, something went terribly wrong.
    @on(AuthComplete)
    def authentication_complete(self, message: AuthComplete):
        self.auth_data = message.auth_data
        self.user_data = message.user_data

    @on(LanguageSelected)
    def handle_language_selection(self, message: LanguageSelected):
        print(f"Language selected: {message.language}")
        if self.editor_instance:
            self.editor_instance.load_challenge(message)
        
    @on(SearchComplete)
    def handle_search(self, message: SearchComplete):
        self.has_vended = True
        self.challenge=message.challenge
        self.current_challenge=message.challenge
        self.challenge_widget.update_chall(self.current_challenge)
        btn = self.query_one("#edit_button")
        btn.display = True
  
    def action_vend_challenge(self) -> None:
        """Output a challenge"""
        self.has_vended = True
        challenge = challenge_loader.vend_random_chall()
        self.challenge = challenge
        self.current_challenge = challenge
        self.challenge_widget.update_chall(challenge)
        # Show edit button after vending
        btn = self.query_one("#edit_button")
        btn.display = True # IT WORKS!!!! :D

def main():
    if "--version" in sys.argv:
        print(f"NyxBox {nyxbox_version}")
        return
    elif "--test-login" in sys.argv: # TODO: REMOVE FOR PROD
        try:
            os.remove(pathlib.Path.joinpath(pathlib.Path.home() / ".nyxbox" / "auth.json"))
            os.remove(pathlib.Path.joinpath(pathlib.Path.home() / ".nyxbox" / "user.json"))
        except Exception as e:
            print(f"{datetime.today().strftime('%Y-%m-%d')} ERROR: {str(e)}")
    app = NyxBox()
    app.run()

if __name__ == "__main__":
    main()