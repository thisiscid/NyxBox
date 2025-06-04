import os, random
import json
import sys
import time
import pathlib
import re
from .plugins import challenge_view, challenge_loader
from .plugins.editor_tools import Editor, EditorClosed, LanguageSelected, TestResultsWidget
from textual import on
from textual.screen import Screen, ModalScreen
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static, TextArea, Label, Button, Digits
from textual.containers import Horizontal, Vertical
from textual.message import Message
from importlib.resources import files

DAEMON_USER="[#B3507D][bold]nyx[/bold][/#B3507D]@[#A3C9F9]hackclub[/#A3C9F9]:~$"

class VendAnimation(Static):
    pass

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


class VendingMachine(App):
    CSS_PATH = str(files("nyxbox").joinpath("styles.tcss"))
    BINDINGS = [("v", "vend_challenge", "Vend a new challenge!"), ("e", "edit_solution", "Edit solution"), ("ctrl+q", "quit_app", "Quit app")]
    
    #Define some consts so we don't have to do this every time we want to show or hide a widget
    BUTTON_PANEL_ID = "button_panel"
    CHALLENGE_VIEW_ID = "challengeview"
    EDITOR_ID = "editor"

    def on_mount(self) -> None:
        """Initialize variables to be used later and other stuff"""
        self.editor_opened = False
        self.has_vended = False

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        with Horizontal():
            self.challenge_widget = self.chall_view()
            self.challenge_widget.id = "challengeview"
            yield self.challenge_widget
            with Vertical(id="button_panel"):
                yield Label("Price (in brownie points):")
                yield Digits("0.00")
                yield Button.warning("Search for item", id="search_button")
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

    def on_editor_closed(self, message: EditorClosed) -> None:
        self.pop_screen()
        self.get_widget_by_id('button_panel').display = True
        self.editor_opened = False
        
    def action_quit_app(self) -> None:
        self.push_screen(ConfirmExit())

    def action_search_button(self) -> None:

        pass
    def action_edit_solution(self) -> None:
        """Allows user to edit a challenge, loads instance then displays"""
        self.editor_instance = Editor()
        self.editor_instance.get_and_update_chall(self.current_challenge)
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
            # This was back when the editor buttons were still there. If this happens, something went terribly wrong.

    @on(LanguageSelected)
    def handle_language_selection(self, message: LanguageSelected):
        print(f"Language selected: {message.language}")
        # Get the editor screen
        if self.editor_instance:
            # Update the editor with the selected language
            self.editor_instance.load_challenge(message)
        
    def chall_view(self):
        """Return the challenge view widget."""
        return challenge_view.UserChallView()
    
    def action_vend_challenge(self) -> None:
        """Output a challenge"""
        self.has_vended = True
        challenge = challenge_loader.vend_random_chall()
        self.challenge = challenge
        self.current_challenge = challenge  # Set current_challenge attribute
        # Update the challenge view with the new challenge
        self.challenge_widget.update_chall(challenge)
        # Show edit button after vending
        btn = self.query_one("#edit_button")
        btn.display = True # IT WORKS!!!! :D

def main():
    app = VendingMachine()
    app.run()