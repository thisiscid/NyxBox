import textual # noqa: F401
import sqlalchemy # noqa: F401
import sys # noqa: F401
import os # noqa: F401
import json # noqa: F401
import pathlib
import datetime
from config import Settings # noqa: F401
from sqlalchemy.orm import Session  # noqa: F401
from database import SessionLocal, engine  # noqa: F401
from models import Challenges
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer # noqa: F401
from textual.reactive import reactive# noqa: F401
from textual.screen import Screen, ModalScreen # noqa: F401
from textual.widget import Widget
from textual.widgets import ListView, ListItem, Button, Header, Footer, Input, Label, Static, DataTable, TextArea # noqa: F401
from textual import on # noqa: F401

class LabelItem(ListItem):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label
    def compose( self ) -> ComposeResult:
        yield Label(self.label)

class ChallengeAddScreen(Screen):
    def on_mount(self) -> None:
        pass
    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Path to challenge json or folder", id="path_input")
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
                    if os.path.isdir(chall_path):
                        for chall in os.listdir(chall_path):
                            with open(chall_path / chall, "r") as file:
                                #TODO: Validate that the given chall doesn't already exist
                                chall_data = None
                                try:
                                    chall_data = json.load(file)
                                    db = SessionLocal()
                                    chall_exists = db.query(Challenges).filter(
                                        or_(
                                            Challenges.name == chall_data["name"],
                                            Challenges.description == chall_data["description"]
                                            )).first()
                                    if chall_exists:
                                        self.app.notify(
                                            message=f"{chall_data["name"]} already exists, not inserting"
                                        )
                                        continue
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
                            attribute_names_from_model = Challenges.__mapper__.columns.keys()
                            filtered_data = {k: v for k, v in chall_data.items() if k in attribute_names_from_model}
                            new_chall = Challenges(**filtered_data)
                            db.add(new_chall)
                            db.commit()
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
                        attribute_names_from_model = Challenges.__mapper__.columns.keys()
                        filtered_data = {k: v for k, v in chall_data.items() if k in attribute_names_from_model}
                        new_chall = Challenges(**filtered_data)
                        db.add(new_chall)
                        db.commit()
                    db.close()
                    self.app.notify(
                        message="Successfully updated DB",
                        severity="information"
                    )


class ChallengeEditScreen(Screen):
    def __init__(self, chall_id) -> None:
        super().__init__()
        self.type_mappings = {
            "INTEGER": int,
            "STRING": str,
            "JSON": dict,
            "DATETIME": datetime.datetime
        }
        self.restricted_vals = [
            "id",
            "created_at",
            # "likes",
            # "solves",
            # Temporarily commenting these bcs they'll be important for testing
            "flagged",
            "submitted_by"
        ]
        self.chall_id = chall_id
        self.attribute_names_from_model = Challenges.__mapper__.columns.keys()
        self.types_from_model = {
            name: column.type.__class__
            for name, column in Challenges.__mapper__.columns.items()}        
        self.db = SessionLocal()
        self.chall=self.db.query(Challenges).filter(Challenges.id == self.chall_id).first()
        self.last_highlighted_param = None


    def compose(self) -> ComposeResult:
        self.challenge = self.db.query(Challenges).filter(Challenges.id == self.chall_id).first()
        with Horizontal():
            yield ListView(
                *[LabelItem(str(attribute)) for attribute in self.attribute_names_from_model if attribute not in self.restricted_vals]
            )
            with Vertical():
                yield Input(placeholder="Select something!", id="input_edit")
        # with ScrollableContainer():
        #     for attribute in self.attribute_names_from_model:
        #         if str(attribute) in self.restricted_vals:
        #             continue
        #         value = getattr(self.challenge, attribute, "")
        #         yield Input(value=str(value), id=str(attribute))
        yield Button.success("Update attributes", id="update_attrs")
    def on_button_pressed(self, event:Button.Pressed):
        match event.button.id:
            case "update_attrs":
                if self.chall:
                    self.notify(f"Updated challenge {self.chall.name}")
                    self.app.pop_screen()
                    self.db.commit()
                    self.db.close()
                    return
                else:
                    self.notify("Chall doesn't seem to exist?")
                    self.app.pop_screen()
                    self.db.rollback()
                    self.db.close()
                    return
                # for attribute in self.attribute_names_from_model:
                #     attr_value = self.query_one(f"#{str(attribute)}", Input)
    def on_list_view_highlighted(self, event:ListView.Highlighted):
        # Get the attribute name from the ListItem's Label
        
        if event: # Why am I doing this to myself
            selected_item = event.item
            attr_name = None
            if isinstance(selected_item, LabelItem):
                attr_name = selected_item.label
            input_label = self.query_one("#input_edit", Input)
            label_value = input_label.value
            if hasattr(self.chall, attr_name):
                self.chall.attr_name = label_value
                return
            self.app.notify("Attribute doesn't seem to exist?")

                # self.db.commit()
    # def on_list_view_highlighted(self, event:ListView.Highlighted):
    #     # Get the attribute name from the ListItem's Label
    #     if event:
    #         selected_item = event.item
    #         attr_name = None
    #         if isinstance(selected_item, LabelItem):
    #             attr_name = selected_item.label
    #         input_label = self.query_one("#input_edit", Input)
    #         input_val = input_label.value
    #         if self.chall and attr_name and hasattr(self.chall, attr_name):
    #             setattr(self.chall, attr_name, input_val)
    #             # self.db.commit()


class ChallengeListScreen(Screen):
    def on_mount(self) -> None:
        # display_table = self.query_one("#challenge_table", DataTable)
        # db = SessionLocal()
        self.load_challenges()

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield DataTable(id="challenge_table", cursor_type="row")
            with Horizontal():
                yield Button(id="add_chall", label="Add challenge")
                yield Button(id="edit_chall", label="Edit Challenge")
        yield Footer()
    def load_challenges(self):
        display_table = self.query_one("#challenge_table", DataTable)
        display_table.clear()
        with SessionLocal() as db:
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
    def on_button_pressed(self, event: Button.Pressed):
        match event.button.id:
            case "add_chall":
                self.app.push_screen(ChallengeAddScreen())
            case "edit_chall":
                datatable = self.query_one("#challenge_table", DataTable)
                current_row = datatable.get_row_at(datatable.cursor_row)
                with SessionLocal() as db:
                    chall = db.query(Challenges).filter(Challenges.id == current_row[0]).first()
                    if chall:
                        chall_id = chall.id
                    else:
                        self.app.notify(
                            "Uh oh, the chall doesn't seem to exist in the DB?"
                        )
                        return
                self.app.push_screen(ChallengeEditScreen(chall_id)) 

class DBManagement(App):
    def on_mount(self):
        self.push_screen(ChallengeListScreen())
        
def main():
    app = DBManagement()
    app.run()

if __name__ == "__main__":
    main()