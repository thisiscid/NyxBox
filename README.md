# NyxBox

A Textual-based TUI app for all your challenge solving needs supporting Python, JS, Java, C++, and C (not yet...) Also, just who is Nyx?

---

## Features

- **Vend random coding challenges** from a curated set
- **Edit and run solutions** in multiple languages!
- **Hidden tests** for extra challenge (we cant just have you cheating the returns right?)
- **Fun daemon commentary** (depends on your humor) and themed UI
- **Extensible**: add your own challenges in JSON

---

## Getting Started

### 1. Install Requirements
Install nyxbox via pip.
```bash
pip install nyxbox
```
Make sure you have clang++ or g++ installed, or Node.js for JavaScript if planning on using these langs, as NyxBox uses these to run your challenges written in C++ or JS.

### 2. Run the App
```bash
python3 main.py
```
## Adding challenges
Add new challenges in the form of a JSON in the challenges directory. Challenges will not work if they do not follow the style of pre-made challenges.

## Notes
- Python 3.10+ recommended (The dev is running 3.12.1)
- C++, C, and Java runners require system dependencies. If they error out, make sure you have those installed first. (look above dummy)
- Run in a terminal supporting Unicode and colors like [Ghostty](https://ghostty.org), [Alacritty](https://alacritty.org), or others.

## Credits
1. ChatGPT + Copilot for helping me debug
2. Textual for providing the underlying framework for the Tui
3. you! for using it!