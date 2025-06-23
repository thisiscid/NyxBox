# Built in libs
from __future__ import annotations
import datetime
import json  # noqa: F401
import os  # noqa: F401
import pathlib
import sys  # noqa: F401
import random

# Third party libs
from sqlalchemy import delete # noqa: F401
from textual import work
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

# Misc stuff
DAEMON_USER="[#B3507D][bold]nyx[/bold][/#B3507D]@[#A3C9F9]hackclub[/#A3C9F9]:~$"
class LabelItem(ListItem):
    def __init__(self, label: str, *, id: str = "") -> None:
        super().__init__(id=id)
        self.label = label
    def compose( self ) -> ComposeResult:
        yield Label(self.label)

class UpdatedDict(): # Call this class, pass it into DictEditScreen, have it modify
    def __init__(self, dict_or_list: "dict | list"):
        self.new_data = dict_or_list
        
class UserChallView(Static):
    def on_mount(self):
        self.styles.align_horizontal = "center"
        NO_CHALL_TEXT=[
            f"{DAEMON_USER} Hm, what an interesting app. Why don't you try pressing something? Maybe 'v'?",
            f"{DAEMON_USER} This better be good since you woke me up. Maybe vend a challenge and see what happens?",
            f"{DAEMON_USER} Welcome Hack Clubbers! (and welcome to everyone else ig). Try vending a challenge!",
            f"{DAEMON_USER} I'm bored...vend a challenge please?"]
        self.update(random.choice(NO_CHALL_TEXT))
    def update_chall(self, chall: dict):
        # Format the profile info
        CHALL_TEXT=[
            f"{DAEMON_USER} Here's your challenge. I hope it's not too hard~",
            f"{DAEMON_USER} Another day, another challenge. You've got this!",
            f"{DAEMON_USER} Let's do this and hopefully learn something. Also, don't fail!",
            f"{DAEMON_USER} Good luck!"
            ]
        if chall.get('difficulty', "N/A").lower() in ["medium", "hard"]:
            CHALL_TEXT=[
            f"{DAEMON_USER} This one might be tough.",
            f"{DAEMON_USER} It's okay to fail! (unless you're a hack clubber of course (im joking!))",
            f"{DAEMON_USER} Bringing on the heat? Let's do it.",
            f"{DAEMON_USER} Good luck! You'll need it."
            ]
        formatted = (
            random.choice(CHALL_TEXT)+"\n"
            f"Name: {chall.get('name', 'N/A')}\n"
            f"Difficulty: {chall.get('difficulty', 'N/A')}\n"
            f"Description: {chall.get('description', 'N/A')}"
        )
        self.update(formatted)
#Screens where we actually manipulate the db
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
        # Do we have to unpack it later? 
        # If yes, we set self.single to True (since we have to take the dict out of the list)
        if isinstance(edit_json_target, dict):
            self.single = True
            self.json_target = [edit_json_target]
        elif isinstance(edit_json_target, list) and not all(isinstance(d, dict) for d in edit_json_target):
            self.dismiss(None)
            self.notify("Not JSON, is a list! Manually edit please!")
            self.app.pop_screen()
        else:
            self.single = False
            self.json_target = edit_json_target
        

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
        else:
            self.dismiss(None)
            self.app.notify(message="Invalid type!", severity="error")

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted): 
        # legit don't even know what class event is supposed to be so lets hope and pray textual did it right
        update_input = self.query_one("#edit_cell", Input)
        update_input.value = str(event.value)
        self.current_row = event.cell_key

    def on_input_submitted(self, event: Input.Submitted):
        data_table = self.query_one("#dicts_table", DataTable)
        data_table.update_cell(*self.current_row, event.value, update_width = True)
        self.refresh()

    def on_button_pressed(self, event: Button.Pressed):
        match event.button.id:
            case "save_dict_edits":
                table=self.query_one("#dicts_table", DataTable)
                updated_list = []
                for row in table.ordered_rows:
                    updated_dict = {}
                    for column in table.ordered_columns:
                        cell_val = table.get_cell(row.key, column.key)
                        if cell_val == "" or cell_val is None:
                            continue
                        updated_dict[str(column.label)] = cell_val
                    updated_list.append(updated_dict)
                self.shared_class.new_data = updated_list
                result = updated_list[0] if self.single else updated_list
                self.shared_class.new_data = result
                self.dismiss(result)
            case "discard_dict_edits":
                self.dismiss(None)

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
                self.json_edit_btn.display = True
                yield self.json_edit_btn
        # with ScrollableContainer():
        #     for attribute in self.attribute_names_from_model:
        #         if str(attribute) in self.restricted_vals:
        #             continue
        #         value = getattr(self.challenge, attribute, "")
        #         yield Input(value=str(value), id=str(attribute))
        yield Button.success("Update attributes", id="update_attrs")
        yield Button.error("Discard changes", id="discard_edit")

    @work
    async def open_json_editor(self):
        try:
            json_val = json.loads(self.query_one("#input_edit", Input).value)
        except json.JSONDecodeError:
            self.app.notify("Not a JSON field!") # Lits just not going to bother
            return
        screen = DictEditScreen(json_val, UpdatedDict(json_val))
        result = await self.app.push_screen_wait(screen)
        if result is not None:
            self.query_one("#input_edit", Input).value = json.dumps(result)
            setattr(self.chall, self.last_highlighted_param, result) # type: ignore

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
                self.open_json_editor()

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
                    # self.json_edit_btn.display = True
                    self.json_edit_btn.refresh()
                else:
                    label.value = str(next_val)
                    # self.json_edit_btn.display = False
                return
            if hasattr(self.chall, self.last_highlighted_param): # type: ignore
                #self.chall.last_highlighted_param = label_value # Need to use setattr here bcs its trying to literally set a param called last_highlighted_param
                try:
                    attr_type = self.types_from_model.get(self.last_highlighted_param)
                    new_attr_type = self.type_mappings.get(attr_type, None)
                    if new_attr_type:
                        if new_attr_type is dict:
                            # self.json_edit_btn.display=True
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
                        else:
                            pass
                            # self.json_edit_btn.display=False
                        if (isinstance(label_value, list) and all(isinstance(d, dict) for d in label_value)) or isinstance(label_value, list):
                            new_attr_type = list
                            # self.json_edit_btn.display=True
                        elif isinstance(label_value, dict):
                            new_attr_type = dict
                            # self.json_edit_btn.display=True

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
                    label.value = json.dumps(val)
                else:
                    label.value = str(val)
            else:
                self.app.notify("Attribute doesn't seem to exist?")
                self.last_highlighted_param = selected_item.id # type: ignore
                return

class ApprovalScreen(Screen): 
    # This screen is going to be mostly identical to ChallengeListScreen
    # Except we're gonna steal something from the main app >:3 (aka the frontend/tui app/client/idek)
    # This is more admin specific so that we can approve user submitted challenges

    def __init__(self, main_instance: ChallengeListScreen) -> None:
        super().__init__()
        self.main_instance = main_instance

    def on_mount(self) -> None:
        # display_table = self.query_one("#challenge_table", DataTable)
        # db = SessionLocal()
        self.load_challenges()
        self.second_pass_approve = None
        self.second_pass_deny = None
        self.attempted_row = None
        # self.main_instance

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield DataTable(id="approval_table", cursor_type="row")
            with Horizontal():
                yield Button(id="approve_chall_approval", label="Approve challenge")
                yield Button(id="deny_chall_approval", label="Deny challenge")
                yield Button.error(id="exit_approval", label="Exit")
            yield UserChallView(id="user_chall_view_approve")
        yield Footer()

    def load_challenges(self):
        display_table = self.query_one("#approval_table", DataTable)
        display_table.clear()
        with SessionLocal() as db:
            chall_query = db.query(Challenges).filter(
                or_(
                    Challenges.is_approved == 0,
                    Challenges.flagged == 1,))
            chall_all = chall_query.all()
            if len(chall_all) == 0:
                self.app.pop_screen()
                self.app.notify("No flagged or non-approved challenges left!")                
            try:
                attribute_names_from_model = Challenges.__mapper__.columns.keys()
            except AttributeError:
                print("Error: Could not retrieve column names from Challenges model.")
                self.app.notify("Error: Could not retrieve column names from Challenges model.")
                attribute_names_from_model = ["id", "name", "error"] 
            display_headers = [name.replace("_", " ").title() for name in attribute_names_from_model]
            display_table.clear(columns=True) 
            display_table.add_columns(*display_headers)
            for chall in chall_all:
                row = [getattr(chall, attr) for attr in attribute_names_from_model]
                display_table.add_row(*row)

    def unset_param(self, param):
        param = False

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted):
        table = self.query_one("#approval_table", DataTable)
        chall_info_display = self.query_one("#user_chall_view_approve", UserChallView)
        # chall = event.row_key
        chall = table.get_row(event.row_key)
        chall_dict = {"name": chall[1], "difficulty": chall[7], "description": chall[2]}
        chall_info_display.update_chall(chall_dict)
        # update_input = self.query_one("#edit_cell", Input)
        # update_input.value = str(event.value)

    def on_button_pressed(self, event: Button.Pressed):
        match event.button.id:
            case "approve_chall_approval":
                table = self.query_one("#approval_table", DataTable)
                row = table.get_row_at(table.cursor_row)
                if self.second_pass_approve and self.attempted_row == row:
                    with SessionLocal() as db:
                        chall = db.query(Challenges).filter(
                            Challenges.id == row[0], Challenges.is_approved != 1, Challenges.name == row[1]
                        ).first()
                        chall.is_active = 1 #type: ignore
                        chall.is_approved = 1 #type: ignore
                        chall.is_reviewed = 1 #type: ignore
                        db.commit()
                        # db.close()
                    self.app.notify(f"Challenge {row[1]}, id {row[0]} has been approved.")
                    self.load_challenges()
                else:
                    self.attempted_row = row
                    self.app.notify(f"Are you sure you want to approve {row[1]}, id {row[0]}? Click again if yes")
                    self.second_pass_approve = True
                    self.set_timer(3, self.unset_param(self.second_pass_approve))
            case "deny_chall_approval":
                table = self.query_one("#approval_table", DataTable)
                row = table.get_row_at(table.cursor_row)
                if self.second_pass_deny and self.attempted_row == row:
                    with SessionLocal() as db:
                        chall = db.query(Challenges).filter(
                            Challenges.id == row[0], Challenges.name == row[1]
                        ).first()
                        chall.is_approved = 0 #type:ignore just in case it wasn't alr 0
                        chall.is_reviewed = 1 #type: ignore
                        chall.is_active = 0 #type: ignore js in case :3
                        db.commit()
                        # db.close()
                    self.app.notify(f"Challenge {row[1]}, id {row[0]} has been denied.")
                    self.load_challenges()
                else:
                    self.attempted_row = row
                    self.app.notify(f"Are you sure you want to deny {row[1]}, id {row[0]}? Click again if yes")
                    self.second_pass_deny = True
                    self.set_timer(3, self.unset_param(self.second_pass_approve))
            case "exit_approval":
                self.app.pop_screen()
                self.main_instance.load_challenges()
                

class ChallengeListScreen(Screen):
    def on_mount(self) -> None:
        # display_table = self.query_one("#challenge_table", DataTable)
        # db = SessionLocal()
        self.load_challenges()
        self.second_pass = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield DataTable(id="challenge_table", cursor_type="row")
            with Horizontal():
                yield Button(id="add_chall", label="Add challenge")
                yield Button(id="edit_chall", label="Edit challenge")
                yield Button(id="remove_chall", label="Remove challenge")
                yield Button(id="approve_chall", label="Approve Challenges")
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
                self.app.notify("Error: Could not retrieve column names from Challenges model.")
                attribute_names_from_model = ["id", "name", "error"] 
            display_headers = [name.replace("_", " ").title() for name in attribute_names_from_model]
            display_table.clear(columns=True) 
            display_table.add_columns(*display_headers)
            for chall in chall_all:
                row = [getattr(chall, attr) for attr in attribute_names_from_model]
                display_table.add_row(*row)

    def unset_second_pass(self):
        # This is literally only necessary because textual
        # won't let you run raw python in the set_timer func
        self.second_pass = False

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

            case "remove_chall":
                table = self.query_one("#challenge_table", DataTable)
                row = table.get_row_at(table.cursor_row)
                if self.second_pass:
                    with SessionLocal() as db:
                        chall = db.query(Challenges).filter(
                                row[0] == Challenges.id
                        ).first()
                        db.delete(chall)
                        db.commit()
                        self.app.notify(f"Challenge {row[1]} with id {row[0]} successfuly deleted!")
                        self.second_pass = False
                        self.load_challenges()
                    # delete_query = delete(Challenges).where(row[0] == Challenges.id)
                else:
                    self.notify(f"Are you sure you want to delete {row[1]} with id {row[0]}? Click again if yes.", timeout=3)
                    self.second_pass = True
                    self.set_timer(10, self.unset_second_pass)
            case "approve_chall":
                self.app.push_screen(ApprovalScreen(self))
    
class DBManagement(App):
    def on_mount(self):
        self.push_screen(ChallengeListScreen())
        
def main():
    app = DBManagement()
    app.run()

if __name__ == "__main__":
    main()