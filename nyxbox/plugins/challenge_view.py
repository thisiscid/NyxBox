from textual.widgets import Static
from . import challenge_loader as chall_load
import random
DAEMON_USER="[#B3507D][bold]nyx[/bold][/#B3507D]@[#A3C9F9]hackclub[/#A3C9F9]:~$"
class UserChallView(Static):
    def on_mount(self):
        self.border_title = "vending slot :3"
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
    
    # def custom_message(self, msg: str):
    #     # Print custom message when required (check editor_tools.py)
    #     self.update(msg)
    # This is completely unnecessary, its already been implemented in other places with diff widgets
