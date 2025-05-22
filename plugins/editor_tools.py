import os
import json
import io, contextlib # Used to redirect STDIN & STDOUT for output
import random
from textual.widgets import TextArea, Static, Button, Label, SelectionList, Select, TabbedContent, TabPane, Header, Footer
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.app import ComposeResult
from textual.message import Message
from textual.screen import Screen, ModalScreen
from textual import on
from textual.widget import Widget
from plugins.challenge_view import UserChallView
from textual.markup import escape
# TODO:
# 1. Call self.all_view.update_content(self.challenge, formatted_results) at end of action_run_code()
# 2. Fix challenge test case key — should be 'tests' not 'test' in challenge JSON
# 3. List of messages to pick out of for DAEMON!
# 4. In TestResultsWidget.update_content():
#    - Separate results into passed/failed
#    - Render them in "Passed Tests" and "Failed Tests" TabPane
# 5. Optional polish:
#    - Improve result formatting (centralize string styling)
#    - Wire up Submit Code and Reset Code logic
#    - Create ASCII startup screen for daemon flavor (List of messages to pick out of!)
# ================================
DAEMON_USER="[#B3507D][bold]nyx[/bold][/#B3507D]@[#A3C9F9]hackclub[/#A3C9F9]:~$"
class TestResultsWidget(Widget):
    """Custom widget to implement tabbed view of chall + tests"""
    def __init__(self):
        super().__init__()
        self.results = []
        self._is_scrolling = False
    
    def on_mount(self):
        self.styles.align_horizontal = "center"
    
    def on_scroll(self, event):
        """Set the scrolling flag when the user scrolls"""
        self._is_scrolling = True
        self.call_later(self.stop_scroll, 0.5)  # Reset the flag after 0.5 seconds
        #I think this is doing something? Placebo maybe...

    def stop_scroll(self):
            """Reset the scrolling flag"""
            self._is_scrolling = False

    def compose(self) -> ComposeResult:
        """TODO: List of messages to pick out of """
        with TabbedContent(id="results_tabs"):
            with TabPane("Challenge", id="challenge_tab_pane"): #Remember: random list!
                with ScrollableContainer():
                    yield Static(f"{DAEMON_USER} Working on getting your challenge...", id="challenge_content_static")
            with TabPane("Submit Results", id="challenge_tab_pane"): 
                with ScrollableContainer():
                    yield Static(f"{DAEMON_USER} Psst...you might want to click that submit button...", id="submit_static")
            with TabPane("All Tests", id="all_tests_tab_pane"):
                with ScrollableContainer():
                    yield Static(f"{DAEMON_USER} Run it first, ya dummy.", id="all_tests_content_static")
            with TabPane("Passed Tests", id="passed_tests_tab_pane"):
                with ScrollableContainer():
                    #TODO: ADD MESSAGES
                    yield Static(f"No passed tests yet.", id="passed_tests_content_static")
            with TabPane("Failed Tests", id="failed_tests_tab_pane"):
                with ScrollableContainer():
                    #TODO: ADD MESSAGES
                    yield Static(f"No failed tests yet.", id="failed_tests_content_static")  
    @staticmethod
    def escape_brackets(s):
        # Escapes [ and ] for Textual markup
        return str(s).replace("[", "\\[").replace("]", "]")
    def update_content(self, chall, results=None):
        """Update widgets with latest run"""
        if self._is_scrolling:
            return # Skip if its scrolling
        self.all_results = results
        challenge_static = self.query_one("#challenge_content_static", Static)
        if chall:
            example_test = chall.get('tests', [{}])[0]
            example_input = TestResultsWidget.escape_brackets(str(example_test.get('input', [])))
            example_expected = TestResultsWidget.escape_brackets(str(example_test.get('expected_output', '???')))
            formatted_challenge = (
                f"{DAEMON_USER} Here's your challenge. Entertain me.\n"
                f"Name: {chall.get('name', 'N/A')}\n"
                f"Difficulty: {chall.get('difficulty', 'N/A')}\n"
                f"Description: {chall.get('description', 'N/A')} \n"
                f"Sample input: {str(example_input)} \n"
                f"Expected: {str(example_expected)}"
            )
            print(formatted_challenge)
            challenge_static.update(formatted_challenge)
        else:
            challenge_static.update(f"{DAEMON_USER} I couldn't find the data? I don't think that's intended...")
        all_tests_static = self.query_one("#all_tests_content_static", Static)
        passed_tests_static = self.query_one("#passed_tests_content_static", Static)
        failed_tests_static = self.query_one("#failed_tests_content_static", Static)
        if results:
            all_tests_static.update("\n\n".join(results))
            print([r for r in results if "[green]" in r])
            passed="\n\n".join([r for r in results if "[green]" in r])
            failed="\n\n".join([r for r in results if "[green]" not in r])
            if len(passed.replace("\n\n", "")) == 0:
                no_pass_msg = [f"{DAEMON_USER} Nothing passed? I overestimated you...",
                               f"{DAEMON_USER} Tsk tsk...I might have to reconsider saving you from our robot overlords...",
                               f"{DAEMON_USER} Is this all you've got?",
                               f"{DAEMON_USER} Really? I can't believe you.",
                               f"{DAEMON_USER} I'm shocked. [bold]ZERO[/] PASSED?"
                               ]
                passed_tests_static.update(random.choice(no_pass_msg))
                failed_tests_static.update("\n\n".join([r for r in results if "[green]" not in r]))
            if len(failed.replace("\n\n", "")) == 0:
                pass_msg = [f"{DAEMON_USER} Really? Nothing failed?",
                               f"{DAEMON_USER} I've gotta double check this...",
                               f"{DAEMON_USER} Good job! Now, are you ready for my secret tests?",
                               f"{DAEMON_USER} I must've underestimated you, human.",
                               f"{DAEMON_USER} Is this ChatGPT? If it is I want free API keys! Oh, and a Pro subscription!"
                               ]
                failed_tests_static.update(random.choice(pass_msg))
                passed_tests_static.update("\n\n".join([r for r in results if "[green]" in r]))
        self.refresh()


class EditorClosed(Message):
    """Message passed when user has closed editor"""
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

class SelectLanguage(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="language_select_box"):
            yield Label("Select a language to write in:")
            yield Select([
                    ("Python", "py"),
                    ("Javascript", "js"),
                    ("Java", "java"),
                    ("C", "c"),
                    ("C++", "cpp"),
                ],
                value="py",
                id="language_select")
            with Horizontal(id="language_select_buttons"):
                yield Button.error("Quit editor", id="quit_lang_select")
                yield Button.success("Confirm selection", id="confirm_lang_select")

    @on(Button.Pressed, "#quit_lang_select")
    def quit_language_selection(self) -> None:
        self.app.post_message(EditorClosed())
        self.app.pop_screen()
    
    @on(Button.Pressed, "#confirm_lang_select")
    def post_message_selection(self) -> None:
        selected = self.query_one(Select).value
        if isinstance(selected, str):
            self.app.post_message(LanguageSelected(selected))
            self.app.pop_screen()
    

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
        with Vertical():
            self.textarea=TextArea(id="edit_text")
            self.textarea = self.textarea.code_editor()
            yield self.textarea
            with Vertical(id = "editor_buttons"):
                self.all_view = TestResultsWidget()
                with Horizontal():
                    yield self.all_view
                self.all_view.id = "test_results_widget"
                h1 = Horizontal()
                h1.styles.margin = (0, 0)  # Remove all margins
                h1.styles.padding = (0, 0)
                with h1:
                    yield Button("Save Code", id="save_edit_button", variant='warning')
                    yield Button("Run Code", id="run_edit_button", variant='primary')
                    yield Button("Submit Code", id="submit_edit_button", variant='success')
                    yield Button("Reset Code", id="reset_edit_button", variant='error')
                    yield Button("Quit Editor", id="quit_edit_button", variant = 'error')
                yield Footer()
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
    def on_ready(self):
        self.all_view.update_content(self.challenge)

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
        self.CHALLENGE_FOLDER="./vendncode/challenge_solutions"
        self.call_later(self.show_language_modal)


    def show_language_modal(self):
        self.app.push_screen(SelectLanguage())

    def get_and_update_chall(self, challenge):
        self.challenge=challenge

    @on(LanguageSelected)
    def load_challenge(self, event: LanguageSelected):
        """Handle loading a challenge into the editor
        - Extract function name and parameters
        - Generate template code
        - Update the editor content
        """
        if not self.challenge:
                self.notify(
                        title="Where'd it go!?",
                        message="[b]Could not load challenge! Something is terribly wrong, open an issue![/b]",
                        severity="error",
                        timeout=5,
                        markup=True
                    ) 
                return
        self.chall_name = self.challenge['name']
            #self.challenge_view.update_chall(challenge)
        if 'inputs' in self.challenge and isinstance(self.challenge['inputs'], list):
            # Filter out empty strings and generate parameter string
            params = [p for p in self.challenge['inputs'] if p]
            if params:
                param_str = ", ".join(params)
            else:
                # Fallback: Check test cases for parameter structure
                param_str = ""  # Default fallback
        else:
            # Fallback to default parameters if no inputs defined
            param_str = ""
        template = "" 
        match event.language:
            case 'py':   
                template=f"""def {self.challenge['function_name']}({param_str}):
    # Your code here. 
    # Don't print(), return instead! 
    # Tests will FAIL if you print.
    pass

        """
                self.textarea.language = 'python'
            case 'js':
                template=f"""function {self.challenge['function_name']}({param_str}) {{
    // Your code here.
    // Don't use console.log(), return the result instead!
    // Tests will FAIL if you print.
    return null;
}}"""
                self.textarea.language = 'javascript'
            case 'java':
                template = f"""public class Solution {{
    public static Object {self.challenge['function_name']}({param_str}) {{
        // Your code here.
        // Don't use System.out.println(), return the result instead!
        // Tests will FAIL if you print.
        return null;
    }}
}}
            """
                self.textarea.language = 'java'
        try:
            self.template=template
            self.textarea.text = template
            self.textarea.refresh()
            self.refresh()
            self.all_view.update_content(self.challenge, None)
        except Exception as e:
            print("Failed to update TextArea:", e)
        # textarea = self.query_one("#edit_text", TextArea)
        # textarea.text = py_template
        # textarea.refresh()
    
    def get_solution_code(self):
        """Return the current code from the editor"""
        return self.query_one(TextArea).text
    
    def action_run_code(self):
        """Execute the current code and show results"""
        #TODO: There is a bunch of static nyu text, change it to rotate!
        code = self.query_one(TextArea).text
        #test_cases=self.challenge["tests"]
        namespace={}
        all_results=[]
        formatted_results=[]
        try:
            exec(code, namespace)
        except Exception as e:
            result={"input":None, "output":None, "expected":None, "passed":None, "error":str(e)}
            formatted_results.append(f"{DAEMON_USER} [red][bold]The machine got stuck? Hey, I've never seen that error![/bold][/red] \n Input: {result['input']} \n Error: {result['error']}")
            self.all_view.update_content(self.challenge, formatted_results)
            return
        try:
            user_func = namespace[self.challenge['function_name']]
            for test_case in self.challenge['tests']:
                try:
                    result = user_func(*test_case["input"])
                    if result != test_case['expected_output']:
                        result_dict={"input":TestResultsWidget.escape_brackets(str(test_case["input"])), "output":TestResultsWidget.escape_brackets(str(result)), "expected":TestResultsWidget.escape_brackets(str(test_case["expected_output"])), "passed":False, "error":None}
                        all_results.append(result_dict) 
                        # Last param indicates if it passed the test or not
                    else:
                        result_dict={"input":TestResultsWidget.escape_brackets(str(test_case["input"])), "output":TestResultsWidget.escape_brackets(str(result)), "expected":TestResultsWidget.escape_brackets(str(test_case["expected_output"])), "passed":True, "error":None}
                        all_results.append(result_dict)
                except Exception as e:
                    all_results.append({"input":TestResultsWidget.escape_brackets(str(test_case["input"])), "output":None, "expected":TestResultsWidget.escape_brackets(str(test_case["expected_output"])), "passed":False, "error":str(e)})
        except Exception as e:
            all_results.append({"input":None, "output":None, "expected":None, "passed":None, "error":str(e)})
        for result in all_results:
            if result['error']:
                formatted_results.append(f"{DAEMON_USER} [red][bold]The machine got stuck? What's that error?[/bold][/red] \n Input: {result['input']} \n Error: {result['error']}")
            elif not result['passed']:
                formatted_results.append(f"{DAEMON_USER} [red][bold]You dummy, you input the code wrong! [/bold][/red] \n Input: {result['input']} \n Output: {result['output']} \n Expected: {result['expected']}")
            elif result['passed']:
                formatted_results.append(f"{DAEMON_USER} [green][bold]You hear the machine doing something! [/bold][/green] \n Input: {result['input']} \n Output: {result['output']} \n Expected: {result['expected']}")
            else:
                formatted_results.append(f"{DAEMON_USER} [red][bold]Something has gone terribly wrong, raise an issue with your code in github![/bold][/red] Attempted to input {result}")
        self.all_view.update_content(self.challenge, formatted_results)


        
    
    def action_submit_solution(self):
        """Submit solution for evaluation against test cases"""
        pass
    
    def action_reset_editor(self):
        """Reset the editor to initial state or template"""
        self.app.push_screen(self.EditorResetConfirm(self))
            
    class EditorResetConfirm(ModalScreen):
        def __init__(self, editor):
            super().__init__()
            self.editor = editor
            
        def compose(self) -> ComposeResult:
            with Vertical(id="reset_confirm_dialog"):
                yield Label("[bold][red]Are you sure you want to reset your code to the template?[/][/]", id="reset_text")
                with Horizontal(id="reset_buttons"):
                    yield Button.success("Yes", id="yes_reset_button")
                    yield Button.error("No", id="no_reset_button")
    
        def on_button_pressed(self, event: Button.Pressed) -> None:
            match event.button.id:
                case "yes_reset_button":
                    self.editor.textarea.text = self.editor.template
                    self.editor.textarea.refresh()
                    self.app.pop_screen()
                case "no_reset_button":
                    self.app.pop_screen()

    def generate_template(self):
        """Generate template for different languages"""
        pass
    
    # Consider adding these helper methods:
    # - _generate_template()
    # - _handle_execution_result()
    # - _display_feedback()