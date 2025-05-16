import os, random
import json
from plugins import challenge_view, challenge_loader
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static

class VendAnimation(Static):
    pass
class VendingMachine(App):
    BINDINGS = [("v", "vend_challenge", "Vend a new challenge!"), ("q", "")]
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        self.challenge_widget = self.chall_view()
        yield self.challenge_widget

    def chall_view(self):
        """Return the challenge view widget."""
        return challenge_view.UserChallView()
    
    def action_vend_challenge(self) -> None:
        """Output a challenge"""
        challenge = challenge_loader.vend_random_chall()
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
if __name__ == "__main__":
    app=VendingMachine()
    app.run()
    


