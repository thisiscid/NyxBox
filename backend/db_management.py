from __future__ import annotations

import datetime
import json  # noqa: F401
import os  # noqa: F401
import pathlib
import sys  # noqa: F401

import sqlalchemy  # noqa: F401
import textual  # noqa: F401
from config import Settings  # noqa: F401
from database import SessionLocal, engine  # noqa: F401
from models import Challenges
from sqlalchemy import or_
from sqlalchemy.orm import Session  # noqa: F401
from sqlalchemy.sql.sqltypes import JSON, DateTime, Integer, String
from textual import on  # noqa: F401
from textual.app import App, ComposeResult
from textual.containers import (  # noqa: F401
    Container,
    Horizontal,
    ScrollableContainer,
    Vertical,
)
from textual.reactive import reactive  # noqa: F401
from textual.screen import ModalScreen, Screen  # noqa: F401
from textual.widget import Widget
from textual.widgets import (  # noqa: F401
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Rule,
    Static,
    TextArea,
)


class LabelItem(ListItem):
    def __init__(self, label: str, *, id: str = "") -> None:
        super().__init__(id=id)
        self.label = label
    def compose( self ) -> ComposeResult:
        yield Label(self.label)

class UpdatedDict(): # Call this class, pass it into DictEditScreen, have it modify
    def __init__(self, dict_or_list: "dict | list"):
        self.new_data = dict_or_list

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
                db = SessionLocal()
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
                        # db = SessionLocal()
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

class DictEditScreen(Screen):
    def __init__(self, edit_json_target: "list | dict", shared_class: UpdatedDict):
        super().__init__()
        self.json_target = edit_json_target
        self.shared_class = shared_class

    def compose(self) -> ComposeResult:
        if isinstance(self.json_target, list):
            all_keys = sorted({k for d in self.json_target for k in d})
            table = DataTable(id="dicts_table")
            table.cursor_type="cell"
            table.add_columns(*all_keys)
            for entry in self.json_target:
                row = [str(entry.get(k, "")) for k in all_keys]
                table.add_row(*row)
            yield table
            yield Input(placeholder="Empty cell", id="edit_cell")
            with Horizontal():
                yield Button("Save Changes", id="save_dict_edits")
                yield Button("Discard Changes", id="discard_dict_edits")
        elif isinstance(self.json_target, dict):
            with Horizontal():
                for key, val in self.json_target.items():
                    yield Input(value=str(key), id=f"key_{key}")
                    yield Input(value=str(val), id=f"value_{key}") # Use a different format for the id since later onwards we can just check isinstance again
                yield Button("Save Changes", id="save_dict_edits")
                yield Button("Discard Changes", id="discard_dict_edits")
        else:
            self.dismiss(None)
            self.app.notify(message="Invalid type!", severity="error")

    def on_button_pressed(self, event: Button.Pressed):
        match event.button.id:
            case "save_dict_edits":
                if isinstance(self.json_target, list):
                    updated_list = []
                    for i, entry in enumerate(self.json_target):
                        updated_dict = {}
                        for key, val in entry.items():
                            updated_dict[self.query_one(f"#key_{i}_{key}", Input).value] = self.query_one(f"#value_{i}_{key}", Input).value
                        updated_list.append(updated_dict)
                    self.shared_class.new_data = updated_list
                    self.dismiss(updated_list)
                elif isinstance(self.json_target, dict):
                    updated_dict = {} 
                    for key, val in self.json_target.items():
                        updated_dict[self.query_one(f"#key_{key}")] = self.query_one(f"#value_{key}")
                    self.dismiss(updated_dict)


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
            "submitted_by",
            "updated_at"
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
        self.list_view_list = [LabelItem(str(attribute), id=str(attribute)) for attribute in self.attribute_names_from_model if attribute not in self.restricted_vals]
        with Horizontal():
            yield ListView(
                *self.list_view_list,
                 id="params_list" # Yields a LabelItem (see above) for each parameter
            )
            with Vertical():
                val = getattr(self.chall, self.last_highlighted_param or "")
                if val is None:
                    val = ""
                if isinstance(val, (dict, list)):
                    val = json.dumps(val, indent=2)
                yield Label(f"Expected type: {self.types_from_model[self.last_highlighted_param]}", id="edit_expected")
                yield Input(value=val, placeholder="Empty field, input something...", id="input_edit") #This is just a placeholder that gets updated on change
                self.json_edit_btn = Button("Edit in JSON editor", id="json_edit")
                self.json_edit_btn.display = False
                yield self.json_edit_btn
        # with ScrollableContainer():
        #     for attribute in self.attribute_names_from_model:
        #         if str(attribute) in self.restricted_vals:
        #             continue
        #         value = getattr(self.challenge, attribute, "")
        #         yield Input(value=str(value), id=str(attribute))
        yield Button.success("Update attributes", id="update_attrs")
        yield Button.error("Discard changes", id="discard_edit")
    async def on_button_pressed(self, event:Button.Pressed):
        match event.button.id:
            case "update_attrs":
                if self.chall:
                    self.notify(f"Updated challenge {self.chall.name}")
                    self.app.pop_screen()
                    self.db.commit()
                    self.db.close()
                    self.main_instance.load_challenges()
                    return
                else:
                    self.notify("Chall doesn't seem to exist?")
                    self.app.pop_screen()
                    self.db.rollback()
                    self.db.close()
                    return
            case "discard_edit":
                self.db.rollback()
                self.db.close()
                self.app.pop_screen()
                # for attribute in self.attribute_names_from_model:
                #     attr_value = self.query_one(f"#{str(attribute)}", Input)
            case "json_edit":
                await self.app.push_screen(DictEditScreen((json.loads(self.query_one("#input_edit", Input).value)), UpdatedDict(json.loads(self.query_one("#input_edit", Input).value))))
    # async def on_input_changed(self, event: Input.Changed) -> None:
    #     self.json_edit_btn.visible = False
    #     if self.types_from_model[self.last_highlighted_param] is JSON:
    #         try:
    #             json.loads(event.value)
    #             self.json_edit_btn.visible=True
    #             return
    #         except json.JSONDecodeError:
    #             self.json_edit_btn.visible = False

    def on_list_view_highlighted(self, event:ListView.Highlighted): # We actually have to change this so that it updates the last parameter and then gets the new one instead of updating the current one
        if event:
            # self.json_edit_btn.display = False
            selected_item = event.item # We eventually need to use this to update last_highlighted_param
            label_value = (self.query_one("#input_edit", Input).value)
            label=self.query_one("#input_edit", Input)
            expected_type = self.query_one("#edit_expected", Label)
            expected_type.update(f"Expected type: {self.types_from_model[selected_item.id]}") # type: ignore
            if label_value is None or label_value.strip() == "" or label_value.strip() == "None":
                new_attr_type = None
                setattr(self.chall, self.last_highlighted_param or "", None)
                self.last_highlighted_param = selected_item.id # type: ignore
                label.value = ""
                next_val = getattr(self.chall, selected_item.id) # type: ignore
                if next_val is None:
                    label.value = ""
                elif isinstance(next_val, (dict, list)):
                    label.value = json.dumps(next_val, indent=2)
                    self.json_edit_btn.display = True
                    self.json_edit_btn.refresh()
                else:
                    label.value = str(next_val)
                return
            if hasattr(self.chall, self.last_highlighted_param): # type: ignore
                #self.chall.last_highlighted_param = label_value # Need to use setattr here bcs its trying to literally set a param called last_highlighted_param
                try:
                    attr_type = self.types_from_model.get(self.last_highlighted_param)
                    new_attr_type = self.type_mappings.get(attr_type, None)
                    if new_attr_type:
                        if new_attr_type is dict:
                            self.json_edit_btn.display=True
                            if isinstance(label_value, str):
                                try:
                                    label_value = json.loads(label_value)
                                except json.JSONDecodeError:
                                    list_view = self.query_one("#params_list", ListView)
                                    list_view.index  = next(
                                        i for i, item in enumerate(self.list_view_list)
                                        if item.id == self.last_highlighted_param
                                    )
                                    self.app.notify("Invalid JSON!", severity="error")
                                    return
                        if (isinstance(label_value, list) and all(isinstance(d, dict) for d in label_value)) or isinstance(label_value, list):
                            new_attr_type = list
                            self.json_edit_btn.display=True
                        elif isinstance(label_value, dict):
                            new_attr_type = dict
                            self.json_edit_btn.display=True

                        # else:
                        #     self.app.notify(
                        #         message="The type is wrong?", 
                        #         severity="error")
                        elif isinstance(new_attr_type, datetime.datetime):
                            try:
                                label_value=datetime.datetime.fromisoformat(label_value)
                            except ValueError:
                                list_view = self.query_one("#params_list", ListView)
                                list_view.index  = next(
                                    i for i, item in enumerate(self.list_view_list)
                                    if item.id == self.last_highlighted_param
                                )
                                self.app.notify("Invalid time!", severity="error")
                                return
                        else:
                            label_value = new_attr_type(label_value) # type: ignore
                except (ValueError, KeyError, TypeError):
                    list_view = self.query_one("#params_list", ListView)
                    list_view.index  = next(
                        i for i, item in enumerate(self.list_view_list)
                        if item.id == self.last_highlighted_param
                    )
                    self.app.notify("Attribute doesn't seem to exist or conversion failed", severity="error")
                    # self.last_highlighted_param = selected_item.label
                    return
                setattr(self.chall, self.last_highlighted_param, label_value) # type: ignore
                self.last_highlighted_param = selected_item.id # type: ignore
                val = getattr(self.chall, selected_item.id) # type: ignore
                if isinstance(val, (dict, list)):
                    label.value = json.dumps(val, indent=2)
                else:
                    label.value = str(val)
            else:
                self.app.notify("Attribute doesn't seem to exist?")
                self.last_highlighted_param = selected_item.id # type: ignore
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
                self.app.push_screen(ChallengeAddScreen(self)) # type: ignore
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