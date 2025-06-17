import textual # noqa: F401
import sqlalchemy # noqa: F401
import sys # noqa: F401
import os # noqa: F401
import json # noqa: F401
import pathlib
from config import Settings # noqa: F401
from sqlalchemy.orm import Session  # noqa: F401
from database import SessionLocal, engine  # noqa: F401
from models import Challenges
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal # noqa: F401
from textual.reactive import reactive # noqa: F401
from textual.screen import Screen, ModalScreen # noqa: F401
from textual.widgets import Button, Header, Footer, Input, Label, Static, DataTable, TextArea # noqa: F401
from textual import on # noqa: F401

class ChallengeAddScreen(Screen):
    def on_mount(self) -> None:
        pass
    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Path to challenge json", id="path_input")
        with Horizontal():
            yield Button.error("Cancel", id="cancel_button")
            yield Button.success("Enter in DB", id="enter_button")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        match event.button.id: 
            case 'cancel_button':
                self.app.pop_screen()
            case 'enter_button':
                path_input = self.query_one("#path_input", Input)
                chall_path = pathlib.Path(path_input.value)
                if not chall_path.exists():
                    self.app.notify(
                        message="Path does not exist.",
                        severity="error"
                    )
                    return
                else:
                    with open(chall_path, "r") as file:
                        chall_data = None
                        try:
                            chall_data = json.load(file)
                        except json.JSONDecodeError:
                            self.app.notify(
                                message="Invalid JSON",
                                severity="error"
                            )
                            return
                    if not chall_data:
                        self.app.notify(
                                message="Invalid JSON",
                                severity="error"
                            )
                        return
                    db = SessionLocal()
                    
                    new_chall = Challenges(**chall_data)
                    db.add(new_chall)
                    db.commit()
                    db.close()
                    

                        




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
            print("Error: Could not retrieve column names from Challenges model.")
            attribute_names_from_model = ["id", "name", "error"] 
        display_headers = [name.replace("_", " ").title() for name in attribute_names_from_model]

        display_table.clear(columns=True) 
        display_table.add_columns(*display_headers)
        for chall in chall_all:
            row = [getattr(chall, attr) for attr in attribute_names_from_model]
            display_table.add_row(*row)

class DBManagement(App):
    def on_mount(self):
        self.push_screen(ChallengeListScreen())
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="chall_list"):
            yield Label()
        yield Footer()

def main():
    app = DBManagement()
    app.run()

if __name__ == "__main__":
    main()