from textual.widgets import Static
import plugins.challenge_loader as chall_load
class UserChallView(Static):
    def on_mount(self):
        self.update("No user profile loaded.")

    def update_chall(self, chall: dict):
        # Format the profile info
        formatted = (
            f"You open the bag to see whats inside...\n"
            f"Name: {chall.get('name', 'N/A')}\n"
            f"Difficulty: {chall.get('difficulty', 'N/A')}\n"
            f"Description: {chall.get('description', 'N/A')}"
        )
        self.update(formatted)
