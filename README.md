```
███    ██ ██    ██ ██   ██ ██████   ██████  ██   ██ 
████   ██  ██  ██   ██ ██  ██   ██ ██    ██  ██ ██  
██ ██  ██   ████     ███   ██████  ██    ██   ███   
██  ██ ██    ██     ██ ██  ██   ██ ██    ██  ██ ██  
██   ████    ██    ██   ██ ██████   ██████  ██   ██ 
```
Nyxbox is a Textual-based TUI app for all your challenge solving needs supporting Python, JS, Java, C++, and ~~C (this is never getting added)~~ Meant to help people learn and practice their coding. Also, who's Nyx?

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
## Backend
To run the backend, do the following.
### 1. Create a .env file
A .env file in the folder of the backend must be created. Here's what it should look like.
```bash
GOOGLE_CLIENT_ID=your-google-client.id.here
GOOGLE_CLIENT_SECRET=GOCSPX-your-google-oauth-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
GITHUB_CLIENT_ID=your-github-client-id-here
GITHUB_CLIENT_SECRET=your-github-oauth-secret-here
GITHUB_REDIRECT_URI=http://localhost:8000/auth/github/callback
JWT_SECRET=your-jwt-secret-here
DATABASE_URL=sqlite:///./nyxbox.db
API_BASE_URL = http://localhost:8000
```
JWT_SECRET is just a random combination of letters, you can just random SHA256 hash something potentially (i'm unsure about the max length of JWT_SECRET). Yes, this will involve grabbing your own OAuth secrets and clients.

### 2. Run via uvicorn
Inside of the backend folder, run 
```bash
uvicorn main:app
```
Make sure that it is running on port 8000. **Furthermore, set your redirects inside of Google and Github OAuth to localhost:8000/auth/github/callback or localhost:8000/auth/google/callback.**

## Frontend
### Method 1: Install via pip
#### 1. Install Requirements
Install nyxbox via pip.
```bash
pip install nyxbox
```
Make sure you have clang++ or g++ installed, or Node.js for JavaScript if planning on using these langs, as NyxBox uses these to run your challenges written in C++ or JS. Same goes for Java (any jdk works! working on adding custom paths so it doesn't matter where you install it)

#### 2. Run the App
```bash
nyxbox
```
### Method 2: Install via git

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
~~Add new challenges in the form of a JSON in the challenges directory. Challenges will not work if they do not follow the style of pre-made challenges.~~
This is temporarily no longer recommended as I work on a backend. 

## Notes
- Python 3.10+ recommended (The dev is running 3.12.1)
- C++ (clang++ or g++), JS (node.js), and Java (JDKs) runners require system dependencies. If they error out, make sure that you have them installed before adding 
- Run in a terminal supporting Unicode and colors like [Ghostty](https://ghostty.org), [Alacritty](https://alacritty.org), or others.

## Credits
1. Copilot for helping me debug (and with the html for the authentication stuff, lifesaver bcs I don't know frontend...)
2. Textual for providing the underlying framework for the TUI
3. You! For using it! Thank you!