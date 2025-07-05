import random
import pathlib
import time
import qrcode
from datetime import datetime
from qrcode.image.pil import PilImage
from rich_pixels import Pixels
from io import BytesIO
from qrcode.constants import ERROR_CORRECT_L
from importlib.metadata import version, PackageNotFoundError

try:
    NYXBOX_VERSION = version("nyxbox")
except PackageNotFoundError:
    NYXBOX_VERSION = "1.0.2"
USER_AGENT = f"NyxBoxClient/{NYXBOX_VERSION}"
DAEMON_USER="[#B3507D][bold]nyx[/bold][/#B3507D]@[#A3C9F9]hackclub[/#A3C9F9]:~$"
SERVER_URL="https://nyxbox.thisisrainy.hackclub.app"

def escape_brackets(s):
        # Escapes [ and ] for Textual markup
        return str(s).replace("[", "\\[").replace("]", "]")

def format_result(result):
    input_str = escape_brackets(result.get("input"))
    output_str = escape_brackets(result.get("output"))
    expected_str = escape_brackets(result.get("expected_output"))
    error_str = escape_brackets(result.get("error"))
    if result.get("error"):
        ERROR_MESSAGES = [
            f"{DAEMON_USER} [red][bold]Oops! Something went wrong, but that's totally normal![/bold][/red]",
            f"{DAEMON_USER} [red][bold]Don't worry, errors are just learning opportunities![/bold][/red]", 
            f"{DAEMON_USER} [red][bold]Hey, debugging is part of the fun! Let's figure this out.[/bold][/red]",
            f"{DAEMON_USER} [red][bold]Every coder faces errors - you're doing great![/bold][/red]",
            f"{DAEMON_USER} [red][bold]Let's see what the machine is trying to tell us.[/bold][/red]"
        ]
        return f"{random.choice(ERROR_MESSAGES)} \nInput: {input_str} \nError: {error_str}"
    elif not result.get("passed"):
        FAILED_MESSAGES = [
            f"{DAEMON_USER} [red][bold]Almost there! Just a small adjustment needed.[/bold][/red]",
            f"{DAEMON_USER} [red][bold]You're on the right track! Let's refine this a bit.[/bold][/red]", 
            f"{DAEMON_USER} [red][bold]Take another look at the expected output, you've got this![/bold][/red]",
            f"{DAEMON_USER} [red][bold]Good attempt! Sometimes it takes a few tries.[/bold][/red]",
            f"{DAEMON_USER} [red][bold]You're learning! Check the differences and see where it went wrong!.[/bold][/red]",
            f"{DAEMON_USER} [red][bold]Keep going! You're building great problem-solving skills.[/bold][/red]"
        ]
        return f"{random.choice(FAILED_MESSAGES)} \nInput: {input_str} \nOutput: {output_str} \nExpected: {expected_str}"
    
    elif result.get("passed"):
        PASSED_MESSAGES = [
            f"{DAEMON_USER} [green][bold]Excellent work! You nailed it![/bold][/green]",
            f"{DAEMON_USER} [green][bold]Perfect! Your logic is spot on.[/bold][/green]",
            f"{DAEMON_USER} [green][bold]Amazing! That's exactly what I was looking for.[/bold][/green]", 
            f"{DAEMON_USER} [green][bold]You're getting really good at this.[/bold][/green]",
            f"{DAEMON_USER} [green][bold]You should be proud of that solution.[/bold][/green]",
            f"{DAEMON_USER} [green][bold]Well done! Your code passed this test.[/bold][/green]"
        ]
        return f"{random.choice(PASSED_MESSAGES)} \nInput: {input_str} \nOutput: {output_str} \nExpected: {expected_str}"
    
    else:
        FALLBACK_MESSAGES = [
            f"{DAEMON_USER} [red][bold]Hmm, something unexpected happened. Mind filing a bug report?[/bold][/red]",
            f"{DAEMON_USER} [red][bold]Looks like I encountered something new! Could you help by reporting this?[/bold][/red]",
            f"{DAEMON_USER} [red][bold]Oops, this is unusual! A bug report would be super helpful.[/bold][/red]"
        ]
        return f"{random.choice(FALLBACK_MESSAGES)} Attempted to input {result}"

def create_log(path, severity, message):
    try:
        # if pathlib.Path.exists(path):
        with open(path, 'a') as f:
            if severity == "error":
                f.write(f"{time.time()} ERROR: {message}\n")
            elif severity == "warning":
                f.write(f"{time.time()} WARNING: {message}\n")
            else:
                f.write(f"{time.time()} INFO: {message}\n")

    except Exception as e:
        return str(e)
    
def return_log_path() -> pathlib.Path:
    log_dir = pathlib.Path.home() / ".nyxbox"
    log_dir.mkdir(exist_ok=True)
    log_path = pathlib.Path.joinpath(log_dir, f"nyxbox-{datetime.today().strftime('%Y-%m-%d')}.log")
    return log_path

def make_qr_pixels(data: str) -> Pixels | None:
    """
    Generates a QR code for the given data and returns it as a rich_pixels.Pixels object.
    Returns None if QR code generation fails.
    """
    try:
        qr = qrcode.QRCode(
            box_size=1, # For pixels, box_size=1 is usually best
            border=0,   # Small border
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(image_factory=PilImage)
        pil_img = img.get_image()  # Convert PilImage to PIL.Image.Image
        return Pixels.from_image(pil_img) 
    except Exception as e:
        # Optionally log the error e
        print(f"Error generating QR pixels: {e}")
        return None
