import textual
import sqlalchemy
import sys
import os
import json 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from sqlalchemy.orm import Session
from backend.database import SessionLocal, engine 
from backend.models import Challenges
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.reactive import reactive
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, Header, Footer, Input, Label, Static, DataTable, TextArea
from textual import on

class ChallengeListScreen(Screen):
    def on_mount(self) -> None:
        # display_table = self.query_one("#challenge_table", DataTable)
        # db = SessionLocal()
        self.load_challenges()

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="challenge_table", cursor_type="row")
        yield Footer()
    def load_challenges(self):
        display_table = self.query_one("#challenge_table", DataTable)
        display_table.clear()
        db = SessionLocal()
        chall_all = db.query(Challenges).all()
        try:
            attribute_names_from_model = Challenges.__mapper__.columns.keys()
        except AttributeError:
            # Fallback or error handling if Challenges model or __mapper__ is not as expected
            # This might happen if the Challenges model isn't a standard SQLAlchemy mapped class
            # or if there are no challenges to infer from (though __mapper__ is on the class)
            print("Error: Could not retrieve column names from Challenges model.")
            # You might want to add some default columns or raise an error
            attribute_names_from_model = ["id", "name", "error"] # Example fallback

        # --- Create display headers (optional, for nicer looking column titles) ---
        # Example: "function_name" becomes "Function Name"
        display_headers = [name.replace("_", " ").title() for name in attribute_names_from_model]
        
        # --- Add these dynamically generated columns to the DataTable ---
        # Make sure to clear old columns if you are re-adding them each time
        display_table.clear(columns=True) 
        display_table.add_columns(*display_headers)

class DBManagement(App):
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="chall_list"):
            yield Label()
        yield Footer()