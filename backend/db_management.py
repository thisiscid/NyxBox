from __future__ import annotations 
import textual # noqa: F401
import sqlalchemy # noqa: F401
from sqlalchemy.sql.sqltypes import Integer, String, JSON, DateTime
import sys # noqa: F401
import os # noqa: F401
import json # noqa: F401
import pathlib
import datetime
from config import Settings # noqa: F401
from sqlalchemy.orm import Session  # noqa: F401
from sqlalchemy import or_
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
    def __init__(self, label: str, *, id: str = None) -> None:
        super().__init__(id=id)
        self.label = label
    def compose( self ) -> ComposeResult:
        yield Label(self.label)

class ChallengeAddScreen(Screen):
    def __init__(self, main_instance: ChallengeListScreen) -> None:
        super().__init__()
        self.main_instance = main_instance
    
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
                                            message=f"{chall_data["name"]} already exists, not inserting",
                                            severity="error"
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
                    self.main_instance.load_challenges() # Gotta reload the thing so that we can see the challenges


class ChallengeEditScreen(Screen):
    def __init__(self, chall_id, main_instance: ChallengeListScreen) -> None:
        super().__init__()
        self.type_mappings = {
            Integer: int,
            String: str,
            JSON: dict,
            DateTime: datetime.datetime
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
        for param in self.attribute_names_from_model:
            if str(param) in self.restricted_vals:
                continue
            else:
                self.last_highlighted_param = str(param)
                break
        self.main_instance = main_instance


    def compose(self) -> ComposeResult:
        self.challenge = self.db.query(Challenges).filter(Challenges.id == self.chall_id).first()
        with Horizontal():
            yield ListView(
                *[LabelItem(str(attribute), id=str(attribute)) for attribute in self.attribute_names_from_model if attribute not in self.restricted_vals],
                 id="params_list" # Yields a LabelItem (see above) for each parameter
            )
            with Vertical():
                yield Input(placeholder="Select something!", id="input_edit") #This is just a placeholder that gets updated on change
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
                    self.main_instance.load_cha
                    return
                else:
                    self.notify("Chall doesn't seem to exist?")
                    self.app.pop_screen()
                    self.db.rollback()
                    self.db.close()
                    return
                # for attribute in self.attribute_names_from_model:
                #     attr_value = self.query_one(f"#{str(attribute)}", Input)
    def on_list_view_highlighted(self, event:ListView.Highlighted): # We actually have to change this so that it updates the last parameter and then gets the new one instead of updating the current one
        if event:
            selected_item = event.item # We eventually need to use this to update last_highlighted_param
            label_value = self.query_one("#input_edit", Input).value
            if hasattr(self.chall, self.last_highlighted_param):
                #self.chall.last_highlighted_param = label_value # Need to use setattr here bcs its trying to literally set a param called last_highlighted_param
                try:
                    attr_type = self.types_from_model.get(self.last_highlighted_param)
                    new_attr_type = self.type_mappings.get(attr_type, None)
                    if new_attr_type:
                        if new_attr_type is dict:
                            try:
                                label_value = json.loads(label_value)
                            except json.JSONDecodeError:
                                list_view = self.query_one("#params_list", ListView)
                                list_view.highlight(self.query_one(f"#{self.last_highlighted_param}", LabelItem))
                                self.app.notify("Invalid json!", severity="error")
                                return
                        elif new_attr_type is datetime.datetime:
                            try:
                                label_value=datetime.datetime.fromisoformat(label_value)
                            except ValueError:
                                list_view = self.query_one("#params_list", ListView)
                                list_view.highlight(self.query_one(f"#{self.last_highlighted_param}", LabelItem))
                                self.app.notify("Invalid time!", severity="error")
                                return
                        else:
                            label_value = new_attr_type(label_value)
                except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                    list_view = self.query_one("#params_list", ListView)
                    list_view.highlight(self.query_one(f"#{self.last_highlighted_param}", LabelItem))
                    self.app.notify("Attribute doesn't seem to exist?")
                    # self.last_highlighted_param = selected_item.label
                    return
                setattr(self.chall, self.last_highlighted_param, label_value)
                self.last_highlighted_param = selected_item.id
                label_value = getattr(self.chall, selected_item.label)
            else:
                self.app.notify("Attribute doesn't seem to exist?")
                self.last_highlighted_param = selected_item.label
                return

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
                            message="Uh oh, the chall doesn't seem to exist in the DB?",
                            severity="error"
                        )
                        return
                self.app.push_screen(ChallengeEditScreen(chall_id, self)) 

class DBManagement(App):
    def on_mount(self):
        self.push_screen(ChallengeListScreen())
        
def main():
    app = DBManagement()
    app.run()

if __name__ == "__main__":
    main()