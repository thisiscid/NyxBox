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
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        with Horizontal():
            self.challenge_widget = self.chall_view()
            self.challenge_widget.id = "challengeview"
            yield self.challenge_widget
            with Vertical(id="button_panel"):
                yield Label("Price (in brownie points):")
                yield Digits("0.00")
                yield Button.warning("Search for item")
                yield Button.success("Vend item", id="vend_button")
        yield Header()
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "vend_button":
            self.action_vend_challenge()

    def action_edit_solution(self) -> None:
        """Allows user to edit a challenge, loads instance then displays"""
        editor_instance = Editor()
        if hasattr(self, 'current_challenge'):
            
            editor_instance.load_challenge(self.current_challenge)
            self.mount(editor_instance)
        else:
            self.notify(
                title="Theres no challenge...",
                message="[b]Please vend a challenge before trying to open the editor![/b]",
                severity="warning",
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
    


