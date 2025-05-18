from textual.widgets import TextArea, Static, Button, Label
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult
import json
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
                yield Button("Save Code", variant='warning')
                yield Button("Run Code", variant='primary')
                yield Button("Submit Code", variant='success')
        
    
    def on_mount(self):
        """Initialize editor state when it's first created"""
        pass
    
    def load_challenge(self, challenge):
        """Handle loading a challenge into the editor
        - Extract function name and parameters
        - Generate template code
        - Update the editor content
        """
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
        return py_template
    
    def get_solution_code(self):
        """Return the current code from the editor"""
        pass
    
    def run_code(self):
        """Execute the current code and show results"""
        pass
    
    def submit_solution(self):
        """Submit solution for evaluation against test cases"""
        pass
    
    def reset_editor(self):
        """Reset the editor to initial state or template"""
        pass
    
    # Consider adding these helper methods:
    # - _generate_template()
    # - _handle_execution_result()
    # - _display_feedback()