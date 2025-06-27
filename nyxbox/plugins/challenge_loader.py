import json
import random
from importlib.resources import files
from pathlib import Path

#TODO: Actually make caching because this just isn't going to work out
def vend_random_chall(challenge_list):
    # challenge_files = list(challenge_dir.iterdir())
    # chosen = random.choice(challenge_files)
    # with chosen.open("r", encoding="utf-8") as f:
    #     return json.load(f)
    return random.choice(challenge_list)
    
def list_all_chall():
    challenge_dir = files("nyxbox").joinpath("../challenges")
    return [Path(f.name).stem for f in challenge_dir.iterdir() if f.name.endswith(".json")]

def list_all_chall_detailed():
    challenge_dir = files("nyxbox").joinpath("../challenges")
    return [
        json.load(f.open("r", encoding="utf-8"))
        for f in challenge_dir.iterdir()
        if f.name.endswith(".json")
    ]

def return_tests(challenge):
    challenge_dir = files("nyxbox").joinpath("../challenges")
    path = challenge_dir.joinpath(f"{challenge}.json")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)["tests"]

