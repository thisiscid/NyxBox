import os, random
import json
import sys
import time
from plugins import challenge_view, challenge_loader
from textual.screen import Screen
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static, TextArea, Label, Button
from textual.containers import *

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
            with Vertical():
                yield Button("Price: $0.00")
                yield Button("Search for item", variant="primary")
                yield Button.success("Vend item")
        yield Header()
        yield Footer()

    def chall_view(self):
        """Return the challenge view widget."""
        return challenge_view.UserChallView()
    
    def action_vend_challenge(self) -> None:
        """Output a challenge"""
        self.has_vended=True
        challenge = challenge_loader.vend_random_chall()
        # Update the challenge view with the new challenge
        self.challenge_widget.update_chall(challenge)
    def action_edit_solution(self) -> None:
        """Allow the user to edit the challenge."""
        if self.has_vended:
            pass
            
        

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
    


