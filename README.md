# NyxBox

A Textual-based TUI app for all your challenge solving needs supporting Python, JS, Java, C++, and C (not yet...) Also, just who is Nyx?

## What's new?
Latest - 0.1.2
0.1.2 - 6/5/25
- Some search fuctionality! (i'm working on it i promise)
- Fixed minor errors
- Fixed README + Getting Started instructions

---

## Features

- **Vend random coding challenges** from a curated set
- **Edit and run solutions** in multiple languages!
- **Hidden tests** for extra challenge (we cant just have you cheating the returns right?)
- **Fun daemon commentary** (depends on your humor) and themed UI
- **Extensible**: add your own challenges in JSON

---

## Getting Started

## Method 1: Install via pip
### 1. Install Requirements
Install nyxbox via pip.
```bash
pip install nyxbox
```
Make sure you have clang++ or g++ installed, or Node.js for JavaScript if planning on using these langs, as NyxBox uses these to run your challenges written in C++ or JS. Same goes for Java (any jdk works! working on adding custom paths so it doesn't matter where you install it)

### 2. Run the App
```bash
nyxbox
```
## Method 2: Install via git

Clone git repo and cd.

```bash
git clone https://github.com/thisiscid/NyxBox
cd NyxBox
```

Then, run as a module.

```bash
python3 -m nyxbox.main
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