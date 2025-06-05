from textual.widgets import Static
from . import challenge_loader as chall_load
DAEMON_USER="[#B3507D][bold]nyx[/bold][/#B3507D]@[#A3C9F9]hackclub[/#A3C9F9]:~$"
class UserChallView(Static):
    def on_mount(self):
        self.styles.align_horizontal = "center"
        self.update(f"{DAEMON_USER} Hm, what an interesting app. Why don't you try pressing something? Maybe 'v'?")

    def update_chall(self, chall: dict):
        # Format the profile info
        formatted = (
            f"{DAEMON_USER} Here's your challenge. I hope it's not too hard~\n"
            f"Name: {chall.get('name', 'N/A')}\n"
            f"Difficulty: {chall.get('difficulty', 'N/A')}\n"
            f"Description: {chall.get('description', 'N/A')}"
        )
        self.update(formatted)
    
    # def custom_message(self, msg: str):
    #     # Print custom message when required (check editor_tools.py)
    #     self.update(msg)
    # This is completely unnecessary, its already been implemented in other places
