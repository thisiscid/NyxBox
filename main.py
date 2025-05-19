import os, random
import json
import sys
import time
from plugins import challenge_view, challenge_loader
from plugins.editor_tools import Editor
from textual.screen import Screen
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static, TextArea, Label, Button, Digits
from textual.containers import Horizontal, Vertical

class VendAnimation(Static):
    pass

class VendingMachine(App):
    CSS_PATH = "./styles.tcss"
    BINDINGS = [("v", "vend_challenge", "Vend a new challenge!"), ("e", "edit_solution", "Edit solution")]
    
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
            with Vertical(id="button_panel"): # THIS DOESN'T EVEN SHOW UP ANYMORE WHYY????
                yield Label("Price (in brownie points):")
                yield Digits("0.00")
                yield Button.warning("Search for item", id="search_button")
                yield Button.success("Vend item", id="vend_button")
                button_edit = Button.success("Begin coding!", id="edit_button")
                button_edit.display = False
                yield button_edit

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "vend_button":
            self.action_vend_challenge()
        elif event.button.id == "edit_button":
            self.action_edit_solution()

    def action_edit_solution(self) -> None:
        """Allows user to edit a challenge, loads instance then displays"""
        editor_instance = Editor()
        if not self.editor_opened:
            if hasattr(self, 'current_challenge'):
                self.editor_opened=True
                editor_instance.load_challenge(self.current_challenge)
                editor_instance.id = "editor"
                self.mount(editor_instance)
                self.get_widget_by_id('button_panel').display = False
            else:
                self.notify(
                    title="Theres no challenge...",
                    message="[b]Please vend a challenge before trying to open the editor![/b]",
                    severity="warning",
                    timeout=5,
                    markup=True
                )
        else:
            self.notify(
                    title="Really?",
                    message="[b]Can't open editor twice! Quit first![/b]",
                    severity="error",
                    timeout=5,
                    markup=True
                )

        
        
    def chall_view(self):
        """Return the challenge view widget."""
        return challenge_view.UserChallView()
    
    def action_vend_challenge(self) -> None:
        """Output a challenge"""
        self.has_vended=True
        challenge = challenge_loader.vend_random_chall()
        self.current_challenge=challenge
        # Update the challenge view with the new challenge
        self.challenge_widget.update_chall(challenge)
        # Show edit button after vending
        btn = self.query_one("#edit_button")
        btn.display = True # IT WORKS!!!! :D

         
        

if __name__ == "__main__":
    app = VendingMachine()
    app.run()

    
#def main():
#    random_challenge=get_and_return_challenge()
#    print(f"Welcome to the vending machine! Here's your random challenge: {random_challenge['name']} \n")
#    print(f"You find details inside of your package! \n")
#    print(f"Difficulty: {random_challenge['difficulty'].title()}")
#    print(f"Description: {random_challenge['description']}")
    
#def get_and_return_challenge() -> dict:
#    with open(os.path.join("challenges", random.choice(os.listdir("challenges"))), 'r') as file:
#            data = json.load(file)
#            return data

#def evaluate_challenge() -> list:
#    solution_file=input("Input the location of your file! ")
#    with open(os.path.abspath(solution_file), 'r') as solution:
#          user_code="".join(solution.readlines())
#    local_scope={}
#    exec(user_code, {"__builtins__": __builtins__}, local_scope)	
#    pass
#if __name__ == "__main__":
    #app=VendingMachine()
    #app.run()
    


