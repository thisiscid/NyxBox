import os
import json
import io, contextlib # Used to redirect STDIN & STDOUT for output
from textual.widgets import TextArea, Static, Button, Label
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult
from textual.message import Message
from textual.screen import Screen, ModalScreen
from plugins.challenge_view import UserChallView
class EditorClosed(Message):
    pass

class LanguageSelected(Message):
    """Message sent when a language is selected."""
    def __init__(self, language: str) -> None:
        self.language = language
        super().__init__()

class UserCodeError(Exception):
    """Custom exception for user code errors."""
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
#class SelectLanguage(ModalScreen):
    #def compose(self) -> ComposeResult:
        #yield 
class Editor(Screen):
    BINDINGS = [
        ("ctrl+s", "save_code", "Save"),
        ("ctrl+r", "run_code", "Run"),
        ("ctrl+q", "quit_editor", "Quit Editor"),
    ]
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
                self.challenge_view = UserChallView()  # <--- store reference
                yield self.challenge_view
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
                self.action_run_code()
    def action_quit_editor(self):
        self.app.push_screen(EditorClosePrompt())

    def action_save_code(self):
        """Handle saving the code
        - Get the current code from the editor
        - Save it to a file or variable
        """
        # Assuming you have a method to get the current code
        if not os.path.exists(self.CHALLENGE_FOLDER):
            os.makedirs(self.CHALLENGE_FOLDER)
        else:
            with open(os.path.join(self.CHALLENGE_FOLDER, f'{self.chall_name}.py'), 'w') as f:
                f.write(self.get_solution_code())
        
    def on_mount(self):
        """Initialize editor state when it's first created"""
        self.CHALLENGE_FOLDER="./vendncode/challenges"
    
    def load_challenge(self, challenge):
        """Handle loading a challenge into the editor
        - Extract function name and parameters
        - Generate template code
        - Update the editor content
        """
        self.chall_name = challenge['name']
        self.challenge = challenge
        #self.challenge_view.update_chall(challenge)
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
        code = self.query_one(TextArea).text
        test_cases=self.challenge["tests"]
        namespace={}
        all_results=[]
        try:
            exec(code, namespace)
        except Exception as e:
            return {"input":None, "output":None, "expected":None, "passed":None, "error":str(e)}
        try:
            user_func = namespace[self.challenge['function_name']]
            for test_case in self.challenge['test']:
                try:
                    result = user_func(*test_case["input"])
                    if result != test_case['expected_output']:
                        result_dict={"input":test_case["input"], "output":result, "expected":test_case["expected_output"], "passed":False, "error":None}
                        all_results.append(result_dict) 
                        # Last param indicates if it passed the test or not
                    else:
                        result_dict={"input":test_case["input"], "output":result, "expected":test_case["expected_output"], "passed":True, "error":None}
                        all_results.append(result_dict)
                except Exception as e:
                    all_results.append({"input":test_case["input"], "output":None, "expected":test_case["expected_output"], "passed":False, "error":str(e)})
        except Exception as e:
            all_results.append({"input":None, "output":None, "expected":None, "passed":None, "error":str(e)})
        return all_results
        
    
    def action_submit_solution(self):
        """Submit solution for evaluation against test cases"""
        pass
    
    def action_reset_editor(self):
        """Reset the editor to initial state or template"""
        pass

    def generate_template(self):
        """Generate template for different languages"""
        pass
    
    # Consider adding these helper methods:
    # - _generate_template()
    # - _handle_execution_result()
    # - _display_feedback()