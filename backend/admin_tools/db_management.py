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
    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="challenge_table", cursor_type="row")
        yield Footer()

class DBManagement(App):
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="chall_list"):
            yield Label()
        yield Footer()