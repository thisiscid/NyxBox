import os
import json
import io, contextlib # Used to redirect STDIN & STDOUT for output
import random
import subprocess
import tempfile
import asyncio
from pathlib import Path
from tree_sitter_languages import get_language
from textual.widgets import TextArea, Static, Button, Label, SelectionList, Select, TabbedContent, TabPane, Header, Footer
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.app import ComposeResult
from textual.message import Message
from textual.screen import Screen, ModalScreen
from textual import on
from textual.widget import Widget
from plugins.challenge_view import UserChallView
from plugins.code_runners.cpp_runner import run_cpp_code
import tree_sitter_cpp
from tree_sitter import Language
# TODO:
# 1. Call self.all_view.update_content(self.challenge, formatted_results) at end of action_run_code()
# 2. Fix challenge test case key — should be 'tests' not 'test' in challenge JSON
# 3. List of messages to pick out of for Nyx!
# 4. In TestResultsWidget.update_content():
#    - Separate results into passed/failed
#    - Render them in "Passed Tests" and "Failed Tests" TabPane
# 5. Optional polish:
#    - Improve result formatting (centralize string styling)
#    - Wire up Submit Code and Reset Code logic
#    - Create ASCII startup screen for daemon flavor (List of messages to pick out of!)
# ================================

DAEMON_USER="[#B3507D][bold]nyx[/bold][/#B3507D]@[#A3C9F9]hackclub[/#A3C9F9]:~$"

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
            with TabPane("Submit Results", id="submit_tabs"): 
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
    def reset_content(self):
        # Called when template is reset in order to reset code results
        if self._is_scrolling:
            return # Skip if its scrolling
        # challenge_static = self.query_one("#challenge_content_static", Static)
        # if chall:
        #     example_test = chall.get('tests', [{}])[0]
        #     example_input = TestResultsWidget.escape_brackets(str(example_test.get('input', [])))
        #     example_expected = TestResultsWidget.escape_brackets(str(example_test.get('expected_output', '???')))
        #     formatted_challenge = (
        #         f"{DAEMON_USER} Here's your challenge. Entertain me.\n"
        #         f"Name: {chall.get('name', 'N/A')}\n"
        #         f"Difficulty: {chall.get('difficulty', 'N/A')}\n"
        #         f"Description: {chall.get('description', 'N/A')} \n"
        #         f"Sample input: {str(example_input)} \n"
        #         f"Expected: {str(example_expected)}"
        #     )
        #     print(formatted_challenge)
        #     challenge_static.update(formatted_challenge)
        # else:
        #     challenge_static.update(f"{DAEMON_USER} I couldn't find the data? I don't think that's intended...")
        # I don't think we actually need to refresh the challenge on reset
        all_tests_static = self.query_one("#all_tests_content_static", Static)
        passed_tests_static = self.query_one("#passed_tests_content_static", Static)
        failed_tests_static = self.query_one("#failed_tests_content_static", Static)
        submit_results_static = self.query_one("#submit_static", Static)
        all_tests_static.update(f"{DAEMON_USER} Run it first, ya dummy.")
        failed_tests_static.update(f"{DAEMON_USER} You can't fail if you don't try, I guess?")
        submit_results_static.update(f"{DAEMON_USER} Psst...you might want to click that submit button...")
        passed_tests_static.update(f"{DAEMON_USER} You don't get a win unless you play in the game! /ref")

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
                self.refresh()
                return
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
                return
            failed_tests_static.update("\n\n".join([r for r in results if "[green]" not in r]))
            passed_tests_static.update("\n\n".join([r for r in results if "[green]" in r]))

        self.refresh()
    def update_submit_content(self, chall, results=None):
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
                    ("C++", "cpp"),
                    ("Java (coming soon)", "java"),
                    ("C (coming soon)", "c")
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

class Editor(Screen):

    BINDINGS = [
        ("ctrl+s", "save_code", "Save"),
        ("ctrl+r", "run_code", "Run"),
        ("ctrl+q", "quit_editor", "Quit Editor"),
        ("v", "", ""),
        ("e", "", "")
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
            with Vertical(id = "editor_interface"):
                self.all_view = TestResultsWidget()
                with Horizontal():
                    yield self.all_view
                self.all_view.id = "test_results_widget"
                h1 = Horizontal()
                h1.id = "editor_buttons"
                h1.styles.margin = (0, 0)  # Remove all margins
                h1.styles.padding = (0, 0)
                with h1:
                    yield Button("Save Code", id="save_edit_button", variant='warning')
                    yield Button("Run Code", id="run_edit_button", variant='primary')
                    yield Button("Submit Code", id="submit_edit_button", variant='success')
                h2 = Horizontal()
                h2.id = "editor_buttons2"
                h2.styles.margin = (0, 0)  # Remove all margins
                h2.styles.padding = (0, 0)
                with h2:
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
                asyncio.create_task(self.action_submit_solution())
            case "run_edit_button":
                asyncio.create_task(self.action_run_code())
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
        cpp_lang = Language(tree_sitter_cpp.language())
        cpp_highlight_query = (Path(__file__).parent.parent / "language-support/highlights-cpp.scm").read_text()
        self.textarea.register_language("cpp", cpp_lang, cpp_highlight_query)
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
        self.func_name = self.challenge['function_name']
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
        self.language=event.language
        match event.language:
            case 'py':   
                template=f"""def {self.challenge['function_name']}({param_str}):
    # Your code here. 
    # Don't print(), return instead! 
    # Tests will FAIL if you print.
    pass

        """
                self.textarea.language = 'python'
                self.all_view.update_content(self.challenge, None)
                self.app.pop_screen()
            case 'js':
                template=f"""function {self.challenge['function_name']}({param_str}) {{
    // Your code here.
    // Don't use console.log(), return the result instead!
    // Tests will FAIL if you print.
    return null;
}}"""
                self.textarea.language = 'javascript'
                self.all_view.update_content(self.challenge, None)
                self.app.pop_screen()
            case 'cpp':
                example_test = self.challenge.get('tests', [{}])[0]
                inputs = example_test.get("input", [])
                expected_output = example_test.get("expected_output", None)
                def infer_cpp_type(value):
                    """Infer C++ type from a Python value."""
                    if isinstance(value, bool):
                        return "bool" 
                    if isinstance(value, int):
                        return "int"
                    elif isinstance(value, dict):
                        if not value:
                            return "map<string, int>"  # Default for empty dict
                        key_type = infer_cpp_type(next(iter(value.keys())))
                        val_type = infer_cpp_type(next(iter(value.values())))
                        return f"map<{key_type}, {val_type}>"
                    elif isinstance(value, float):
                        return "double"
                    elif isinstance(value, str):
                        return "string"
                    elif isinstance(value, list):
                        # Check if the list is empty
                        if not value:
                            return "vector<int>"
                        
                        # Check if all elements are same type
                        first_type = type(value[0])
                        if all(isinstance(x, first_type) for x in value):
                            element_type = infer_cpp_type(value[0])
                        else:
                            # Mixed types - use most general type or auto
                            return "vector<auto>"  # This isn't valid C++ but signals a type issue
                        
                        return f"vector<{element_type}>"
                    else:
                        return "auto"  # Fallback for unknown types
                def default_return_value_cpp(cpp_type):
                    """Provide a default return value for a given C++ type."""
                    if cpp_type == "bool":
                        return "false"
                    elif cpp_type == "int":
                        return "0"
                    elif cpp_type == "double":
                        return "0.0"
                    elif cpp_type == "string":
                        return "\"\""
                    elif cpp_type.startswith("vector"):
                        return "{}"
                    elif cpp_type.startswith("map<"):
                        return "{}"
                    else:
                        return "0"  # Fallback for unknown types
                param_types = [infer_cpp_type(param) for param in inputs]
                param_str = ", ".join(f"{ptype} param{i}" for i, ptype in enumerate(param_types))
                return_type = infer_cpp_type(expected_output)

                template = f"""#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <unordered_map>  
#include <algorithm>
using namespace std;
// DO NOT REMOVE THE ABOVE!
// Add extra libraries if necessary.
// Only minimal syntax highlighting present, sorry!

{return_type} {self.challenge['function_name']}({param_str}) {{
    // Your code here.
    // Do NOT use cout/printf, return the result instead!
    // Tests will FAIL if you print.
    return {default_return_value_cpp(return_type)};
}}
"""
                self.all_view.update_content(self.challenge, None)
                self.textarea.language="cpp"
                self.app.pop_screen()
            case 'c': # I removed C support because its hard to handle dicts, i'll try when the main stuff is done
#                 example_test = self.challenge.get('tests', [{}])[0]
#                 inputs = example_test.get("input", [])
#                 expected_output = example_test.get("expected_output", None)
#                 def infer_c_type(value):
#                     """Infer C type from a Python value."""
#                     if isinstance(value, bool):
#                         return "bool" 
#                     if isinstance(value, int):
#                         return "int"
#                     elif isinstance(value, dict):
#                         return "/* No built in map/dict in C */ void*"
#                     elif isinstance(value, float):
#                         return "double"
#                     elif isinstance(value, str):
#                         return "char*"
#                     elif isinstance(value, list):
#                         # Check if the list is empty
#                         if not value:
#                             return "int arr[]"
#                         # Check if all elements are same type
#                         first_type = type(value[0])
#                         if all(isinstance(x, first_type) for x in value):
#                             element_type = infer_cpp_type(value[0])
#                         else:
#                             # Mixed types - use most general type or auto
#                             return "int*"  # This isn't valid C but signals a type issue
#                         return f"{element_type}*"
#                     else:
#                         return "void* /*Mixed lists not fully supported*/"  # Fallback for unknown types
#                 def default_return_value_c(c_type):
#                     """Provide a default return value for a given C type."""
#                     if c_type == "bool":
#                         return "false"
#                     elif c_type == "int":
#                         return "0"
#                     elif c_type == "double":
#                         return "0.0"
#                     elif c_type == "char*":
#                         return "\"\""
#                     elif c_type.startswith("void*"):
#                         return "NULL"
#                     elif c_type.startswith("int*"):
#                         return "NULL"
#                     else:
#                         return "NULL"  # Fallback for unknown types
#                 param_types = [infer_c_type(param) for param in inputs]
#                 param_str = ", ".join(f"{ptype} param{i}" for i, ptype in enumerate(param_types))
#                 return_type = infer_c_type(expected_output)
#                 c_template = """#include <stdio.h>
# #include <stdbool.h>
# #include <stddef.h>

# // DO NOT REMOVE THE ABOVE!
# // Add extra libraries if necessary.
# // There won't be any syntax highlighting, sorry!

# // Example function signature (edit as needed):
# // int my_function(int* arr, int arr_size) {{

# {return_type} {function_name}({param_str}) {{
#     // Your code here.
#     // Do NOT use printf, return the result instead!
#     // Tests will FAIL if you print.
#     return {default_return_value};
# }}
# """
#                 template = c_template.format(
#                 return_type=return_type,
#                 function_name=self.challenge['function_name'],
#                 param_str=param_str,
#                 default_return_value=default_return_value_c(return_type)
#                 )
                self.notify(
                    title="I'm working on it!",
                    message=f"{DAEMON_USER} C is so hard... Come back later maybe?",
                    severity="error",
                    timeout=3,
                    markup=True
                    )
            case 'java':
                self.notify(
                    title="I'm working on it!",
                    message=f"{DAEMON_USER} Hey, I haven't implemented Java yet! Come back later...",
                    severity="error",
                    timeout=3,
                    markup=True
                    )

        try:
            self.template=template
            self.textarea.text = template
            # Do we really need to refresh it?
            # self.textarea.refresh()
            # self.refresh()
            #self.all_view.update_content(self.challenge, None) We want to update only when the user chooses a supported language
        except Exception as e:
            print("Failed to update TextArea:", e)
        # textarea = self.query_one("#edit_text", TextArea)
        # textarea.text = py_template
        # textarea.refresh()
    
    def get_solution_code(self):
        """Return the current code from the editor"""
        return self.query_one(TextArea).text
    
    async def action_run_code(self) -> None:
        """Execute the current code and show results"""
        #TODO: There is a bunch of static nyu text, change it to rotate!
        #Python and JS are in this file because they're easy to implement and not that long.
        #Since C++, C, and Java are compiled, we will need to fix it later.
        code = self.query_one(TextArea).text
        #test_cases=self.challenge["tests"]
        namespace={}
        all_results=[]
        formatted_results=[]
        match self.language:
            case 'py':
                try:
                    exec(code, namespace)
                except Exception as e:
                    result={"input":None, "output":None, "expected":None, "passed":None, "error":str(e)}
                    formatted_results.append(f"{DAEMON_USER} [red][bold]The machine got stuck? Hey, I've never seen that error![/bold][/red] \n Input: {result['input']} \n Error: {result['error']}")
                    self.notify(
                    title="Hey mortal...I finished running your code!",
                    message=f"{DAEMON_USER} I don't think your code works though... check the 'All Tests' or failed tests tab...",
                    severity="error",
                    timeout=3,
                    markup=True
                    )
                    self.all_view.update_content(self.challenge, formatted_results)
                    return
                try:
                    user_func = namespace[self.challenge['function_name']]
                    for test_case in self.challenge['tests']:
                        if test_case.get("hidden", False):
                            continue
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
                self.notify(
                    title="Hey mortal...I finished running your code!",
                    message=f"{DAEMON_USER} Check your 'All Tests' tab, or check the specific tabs for passes/fails! See ya~",
                    severity="information",
                    timeout=3,
                    markup=True
                    )
                self.all_view.update_content(self.challenge, formatted_results)
            case 'js':
                for test_case in self.challenge['tests']:
                    if test_case.get("hidden", False):
                        continue
                    args = ", ".join(json.dumps(arg) for arg in test_case["input"])
                    wrapped_code = f"""
// --- USER CODE START ---
{code}
// --- USER CODE END ---

try {{
    const result = {self.func_name}({args});
    console.log(JSON.stringify(result));
}} catch (err) {{
    console.error("ERROR:", err.message);
    process.exit(1);
}}
"""
                    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".js") as f:
                        f.write(wrapped_code)
                        js_file = f.name

                    try:
                        proc = await asyncio.create_subprocess_exec(
                        "node", js_file,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )

                        stdout, stderr = await proc.communicate()
                        if proc.returncode != 0:
                            # formatted_results.append(f"{DAEMON_USER} [red][bold]The machine got stuck? What's that error?[/bold][/red] \n Input: {result['input']} \n Error: {result['error']}")
                            # all_results.append({
                            #     "input": TestResultsWidget.escape_brackets(str(test_case["input"])),
                            #     "output": None,
                            #     "expected": TestResultsWidget.escape_brackets(str(test_case["expected_output"])),
                            #     "passed": False,
                            #     "error": stderr.decode().strip()
                            # })
                            formatted_results.append(f"{DAEMON_USER} [red][bold]The machine got stuck? What's that error?[/bold][/red] \n Input: {TestResultsWidget.escape_brackets(str(test_case["input"]))} \n Error: {stderr.decode().strip()}")
                            self.all_view.update_content(self.challenge, formatted_results)
                            return

                        else:
                            result = json.loads(stdout.decode().strip())
                            all_results.append({
                                "input": TestResultsWidget.escape_brackets(str(test_case["input"])),
                                "output": TestResultsWidget.escape_brackets(str(result)),
                                "expected": TestResultsWidget.escape_brackets(str(test_case["expected_output"])),
                                "passed": result == test_case["expected_output"],
                                "error": None
                            })
                    except subprocess.TimeoutExpired:
                        all_results.append({
                            "input": TestResultsWidget.escape_brackets(str(test_case["input"])),
                            "output": None,
                            "expected": TestResultsWidget.escape_brackets(str(test_case["expected_output"])),
                            "passed": False,
                            "error": "Execution timed out"
                        })
                for result in all_results:
                    if result['error']:
                        formatted_results.append(f"{DAEMON_USER} [red][bold]The machine got stuck? What's that error?[/bold][/red] \n Input: {result['input']} \n Error: {result['error']}")
                    elif not result['passed']:
                        formatted_results.append(f"{DAEMON_USER} [red][bold]You dummy, you input the code wrong! [/bold][/red] \n Input: {result['input']} \n Output: {result['output']} \n Expected: {result['expected']}")
                    elif result['passed']:
                        formatted_results.append(f"{DAEMON_USER} [green][bold]You hear the machine doing something! [/bold][/green] \n Input: {result['input']} \n Output: {result['output']} \n Expected: {result['expected']}")
                    else:
                        formatted_results.append(f"{DAEMON_USER} [red][bold]Something has gone terribly wrong, raise an issue with your code in github![/bold][/red] Attempted to input {result}")
                self.notify(
                    title="Hey mortal...I finished running your code!",
                    message=f"{DAEMON_USER} Check your 'All Tests' tab, or check the specific tabs for passes/fails! See ya~",
                    severity="information",
                    timeout=3,
                    markup=True
                )
                self.all_view.update_content(self.challenge, formatted_results)
            case 'cpp':
                self.app.push_screen(self.CompilationStandardPopup(self.challenge, self.textarea.text, self.challenge['function_name'], [test for test in self.challenge['tests'] if not test.get("hidden", False)], self.language, self.textarea, self.all_view))



        
    
    async def action_submit_solution(self):
        """Submit solution for evaluation against test cases"""
        #TODO: There is a bunch of static nyu text, change it to rotate!
        #Python and JS are in this file because they're easy to implement and not that long.
        #Since C++, C, and Java are compiled, we will need to fix it later.
        code = self.query_one(TextArea).text
        #test_cases=self.challenge["tests"]
        namespace={}
        all_results=[]
        formatted_results=[]
        match self.language:
            case 'py':
                try:
                    exec(code, namespace)
                except Exception as e:
                    result={"input":None, "output":None, "expected":None, "passed":None, "error":str(e)}
                    formatted_results.append(f"{DAEMON_USER} [red][bold]The machine got stuck? Hey, I've never seen that error![/bold][/red] \n Input: {result['input']} \n Error: {result['error']}")
                    self.notify(
                    title="Hey mortal...I finished running your code!",
                    message=f"{DAEMON_USER} I don't think your code works though. Hey, wait, did you even actually try running it first? Anyways, check the 'Submit' tab.",
                    severity="error",
                    timeout=3,
                    markup=True
                    )
                    self.all_view.update_content(self.challenge, formatted_results)
                    return
                try:
                    user_func = namespace[self.challenge['function_name']]
                    for test_case in self.challenge['tests']:
                        if test_case.get("hidden", False):
                            continue
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
                self.notify(
                    title="Hey mortal...I finished running your code!",
                    message=f"{DAEMON_USER} Check your 'All Tests' tab, or check the specific tabs for passes/fails! See ya~",
                    severity="information",
                    timeout=3,
                    markup=True
                    )
                self.all_view.update_content(self.challenge, formatted_results)
            case 'js':
                for test_case in self.challenge['tests']:
                    if test_case.get("hidden", False):
                        continue
                    args = ", ".join(json.dumps(arg) for arg in test_case["input"])
                    wrapped_code = f"""
// --- USER CODE START ---
{code}
// --- USER CODE END ---

try {{
    const result = {self.func_name}({args});
    console.log(JSON.stringify(result));
}} catch (err) {{
    console.error("ERROR:", err.message);
    process.exit(1);
}}
"""
                    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".js") as f:
                        f.write(wrapped_code)
                        js_file = f.name

                    try:
                        proc = await asyncio.create_subprocess_exec(
                        "node", js_file,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )

                        stdout, stderr = await proc.communicate()
                        if proc.returncode != 0:
                            # formatted_results.append(f"{DAEMON_USER} [red][bold]The machine got stuck? What's that error?[/bold][/red] \n Input: {result['input']} \n Error: {result['error']}")
                            # all_results.append({
                            #     "input": TestResultsWidget.escape_brackets(str(test_case["input"])),
                            #     "output": None,
                            #     "expected": TestResultsWidget.escape_brackets(str(test_case["expected_output"])),
                            #     "passed": False,
                            #     "error": stderr.decode().strip()
                            # })
                            formatted_results.append(f"{DAEMON_USER} [red][bold]The machine got stuck? What's that error?[/bold][/red] \n Input: {TestResultsWidget.escape_brackets(str(test_case["input"]))} \n Error: {stderr.decode().strip()}")
                            self.all_view.update_content(self.challenge, formatted_results)
                            return

                        else:
                            result = json.loads(stdout.decode().strip())
                            all_results.append({
                                "input": TestResultsWidget.escape_brackets(str(test_case["input"])),
                                "output": TestResultsWidget.escape_brackets(str(result)),
                                "expected": TestResultsWidget.escape_brackets(str(test_case["expected_output"])),
                                "passed": result == test_case["expected_output"],
                                "error": None
                            })
                    except subprocess.TimeoutExpired:
                        all_results.append({
                            "input": TestResultsWidget.escape_brackets(str(test_case["input"])),
                            "output": None,
                            "expected": TestResultsWidget.escape_brackets(str(test_case["expected_output"])),
                            "passed": False,
                            "error": "Execution timed out"
                        })
                for result in all_results:
                    if result['error']:
                        formatted_results.append(f"{DAEMON_USER} [red][bold]The machine got stuck? What's that error?[/bold][/red] \n Input: {result['input']} \n Error: {result['error']}")
                    elif not result['passed']:
                        formatted_results.append(f"{DAEMON_USER} [red][bold]You dummy, you input the code wrong! [/bold][/red] \n Input: {result['input']} \n Output: {result['output']} \n Expected: {result['expected']}")
                    elif result['passed']:
                        formatted_results.append(f"{DAEMON_USER} [green][bold]You hear the machine doing something! [/bold][/green] \n Input: {result['input']} \n Output: {result['output']} \n Expected: {result['expected']}")
                    else:
                        formatted_results.append(f"{DAEMON_USER} [red][bold]Something has gone terribly wrong, raise an issue with your code in github![/bold][/red] Attempted to input {result}")
                self.notify(
                    title="Hey mortal...I finished running your code!",
                    message=f"{DAEMON_USER} Check your 'All Tests' tab, or check the specific tabs for passes/fails! See ya~",
                    severity="information",
                    timeout=3,
                    markup=True
                )
                self.all_view.update_content(self.challenge, formatted_results)
            case 'cpp':
                self.app.push_screen(self.CompilationStandardPopup(self.challenge, self.textarea.text, self.challenge['function_name'], [test for test in self.challenge['tests'] if not test.get("hidden", False)], self.language, self.textarea, self.all_view))

    
    def action_reset_editor(self):
        """Reset the editor to initial state or template"""
        self.app.push_screen(self.EditorResetConfirm(self))

    class CompilationStandardPopup(ModalScreen):
        def __init__(self, chall, user_code, func_name, test_cases, language, editor, testresultswidget):
            super().__init__()
            self.chall = chall
            self.code = user_code
            self.func_name = func_name
            self.tests=test_cases
            self.all_view = testresultswidget
            self.lang = language
            self.editor = editor
        def compose(self) -> ComposeResult:
            with Vertical(id="compilation_dialog"):
                yield Label(f"{DAEMON_USER} Choose your compiler!", id="choose_comp_text")
                if self.lang == "cpp":
                    yield Select([
                    ("C++20", "c++20"),
                    ("C++17", "c++17"),
                    ("C++14", "c++14"),
                    ("C++11", "c++11"),
                    ],
                    value="c++17",
                    id="std_select")
                # These should literally never be called right now. If they do, that's bad.
                # elif self.lang == "c":
                #     yield Select([
                #     ("C23 [bold][red]Danger! May be unsupported![/][/]", "c23"),
                #     ("C17", "c17"),
                #     ("C11", "c11"),
                #     ("C99", "c99"),
                #     ("C90 [bold][red]Old, providede template likely won't work with this.[/][/]", "c90")
                #     ],
                #     value="c11",
                #     id="std_select")
                # elif self.lang == "java":
                #     yield Select([
                #     ("Java 21 (LTS)", "21"),
                #     ("Java 17 (LTS)", "17"),
                #     ("Java 11 (LTS)", "11"),
                #     ("Java 8", "8"),
                #     ], 
                #     value="17", 
                #     id="std_select")
                with Horizontal(id = "comp_type_select"):
                    yield Button.success("Select", id="yes_comp")
                    yield Button.error("Quit", id="no_comp")
        @on(Button.Pressed, "#yes_comp")
        async def confirm_comp(self):
            std_selection=self.query_one("#std_select", Select)
            value=std_selection.value
            if value:
                if self.lang == "cpp":
                    results = await run_cpp_code(self.code, self.func_name, self.tests, value)
                    formatted_results = [format_result(result) for result in results]
                    self.all_view.update_content(self.chall, formatted_results)
                self.app.pop_screen()
            else:
                self.notify(
                    title="Really?",
                    message=f"{DAEMON_USER} Choose an option, stupid! How do you want me to compile if you won't tell me how?",
                    severity="error",
                    timeout=3,
                    markup=True
                )
                


        @on(Button.Pressed, "#no_comp")
        def stop_comp(self):
            self.app.pop_screen()

                    

    class EditorResetConfirm(ModalScreen):
        def __init__(self, editor):
            super().__init__()
            self.editor = editor
            
        def compose(self) -> ComposeResult:
            with Vertical(id="reset_confirm_dialog"):
                yield Label("[bold][red]Are you sure you want to reset your code to the template?[/][/]", id="reset_text")
                yield Label("This will also reset any current test results!", id = "test_result_notice")
                with Horizontal(id="reset_buttons"):
                    yield Button.success("Yes", id="yes_reset_button")
                    yield Button.error("No", id="no_reset_button")
    
        def on_button_pressed(self, event: Button.Pressed) -> None:
            match event.button.id:
                case "yes_reset_button":
                    self.editor.textarea.text = self.editor.template
                    self.editor.textarea.refresh()
                    self.editor.all_view.reset_content()
                    self.app.pop_screen()
                case "no_reset_button":
                    self.app.pop_screen()

def format_result(result):
    input_str = TestResultsWidget.escape_brackets(result.get("input"))
    output_str = TestResultsWidget.escape_brackets(result.get("output"))
    expected_str = TestResultsWidget.escape_brackets(result.get("expected_output"))
    error_str = TestResultsWidget.escape_brackets(result.get("error"))
    if result.get("error"):
        return f"{DAEMON_USER} [red][bold]The machine got stuck? What's that error?[/bold][/red] \nInput: {input_str} \nError: {error_str}"
    elif not result.get("passed"):
        return f"{DAEMON_USER} [red][bold]You dummy, you input the code wrong! [/bold][/red] \nInput: {input_str} \nOutput: {output_str} \nExpected: {expected_str}"
    elif result.get("passed"):
        return f"{DAEMON_USER} [green][bold]You hear the machine doing something! [/bold][/green] \nInput: {input_str} \nOutput: {output_str} \nExpected: {expected_str}"
    else:
        return f"{DAEMON_USER} [red][bold]Something has gone terribly wrong, raise an issue with your code in github![/bold][/red] Attempted to input {result}"