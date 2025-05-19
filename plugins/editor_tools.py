from textual.widgets import TextArea, Static, Button, Label

from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult
from textual.message import Message
import json
from textual.screen import Screen, ModalScreen

class EditorClosed(Message):
    pass

class EditorClosePrompt(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="quit_screen"):
            yield Label("Exit back to the vending machine?", id="quit_text")
            with Horizontal(id="quit_buttons"):
                yield Button.success("Yes", id="yes_editor_button")
                yield Button.error("No", id="no_editor_button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "yes_editor_button":
                self.app.pop_screen()
                self.app.post_message(EditorClosed())
            case "no_editor_button":
                self.app.pop_screen() 

class Editor(Static):
    
    def compose(self) -> ComposeResult:
        """Define the editor layout here
        Consider including:
        - Text editing area
        - Run/Submit buttons
        - Status indicators
        """
        with Horizontal():
            yield TextArea(self.template_code, language="python", tab_behavior='indent')
            with Vertical():
                yield Button("Save Code", id="save_edit_button", variant='warning')
                yield Button("Run Code", id="run_edit_button", variant='primary')
                yield Button("Submit Code", id="submit_edit_button", variant='success')
                yield Button("Reset Code", id="reset_edit_button", variant='error')
                yield Button("Quit Editor", id="quit_edit_button", variant = 'error')
    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "save_edit_button":
                self.action_save_code()
            case "quit_edit_button":
                self.app.push_screen(EditorClosePrompt())
            case "reset_edit_button":
                self.action_reset_editor()
            case "submit_edit_button":
                self.action_submit_solution()
            case "run_edit_button":
                self.action_run_code
    def action_quit_editor(self):
        """Handle quitting the editor
        - Hide the editor
        - Show the main app screen
        """
        """self.get_widget_by_id('button_panel').display = True
        self.remove()"""

    def action_save_code(self):
        """Handle saving the code
        - Get the current code from the editor
        - Save it to a file or variable
        """
        # Assuming you have a method to get the current code
        with open(f'{self.chall_name}.py', 'w') as f:
            f.write(self.get_solution_code())
        
    def on_mount(self):
        """Initialize editor state when it's first created"""
        pass
    
    def load_challenge(self, challenge):
        """Handle loading a challenge into the editor
        - Extract function name and parameters
        - Generate template code
        - Update the editor content
        """
        self.chall_name = challenge['name']
        self.challenge = challenge
        if 'inputs' in challenge and isinstance(challenge['inputs'], list):
            # Filter out empty strings and generate parameter string
            params = [p for p in challenge['inputs'] if p]
            if params:
                param_str = ", ".join(params)
            else:
                # Fallback: Check test cases for parameter structure
                param_str = ""  # Default fallback
        else:
            # Fallback to default parameters if no inputs defined
            param_str = ""
        
        py_template=f"""def {challenge['function_name']}({param_str}): \n \t

"""
        self.template_code=py_template
        return self.template_code
    
    def get_solution_code(self):
        """Return the current code from the editor"""
        return self.query_one(TextArea).text
    
    def action_run_code(self):
        """Execute the current code and show results"""
        pass
    
    def action_submit_solution(self):
        """Submit solution for evaluation against test cases"""
        pass
    
    def action_reset_editor(self):
        """Reset the editor to initial state or template"""
        
    
    # Consider adding these helper methods:
    # - _generate_template()
    # - _handle_execution_result()
    # - _display_feedback()