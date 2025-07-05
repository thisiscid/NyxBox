```
███    ██ ██    ██ ██   ██ ██████   ██████  ██   ██ 
████   ██  ██  ██   ██ ██  ██   ██ ██    ██  ██ ██  
██ ██  ██   ████     ███   ██████  ██    ██   ███   
██  ██ ██    ██     ██ ██  ██   ██ ██    ██  ██ ██  
██   ████    ██    ██   ██ ██████   ██████  ██   ██ 
```
Nyxbox is a Textual-based TUI app for all your challenge solving needs supporting Python, JS, Java, and C++. Meant to help people learn and practice their coding. Also, who's Nyx?

## What's new?
Latest - 1.0.1
1.0.1 - 6/28/25
- Fixed minor issue potentially causing crashes in clients running python in versions <3.12
- Fixed issue affecting search where it would error out

1.0.0 - 6/28/25
- Fully featured app out now!
- Powered on a backend now (thanks nest (psst hack club))
- Supports slack and guest sign in as well
- Execution environments finally work!

---

## Features

- **Vend random coding challenges** from a curated set
- **Edit and run solutions** in multiple languages!
- **Hidden tests** for extra challenge (we cant just have you cheating the returns right?)
- **~~Really bad~~ Really good** daemon character!

---

## Getting Started
### Web version
A web version is available at [this link](https://nyxbox-client.thisisrainy.hackclub.app)! May be slightly buggy, but should mostly work.

### Pip version
#### 1. Install
Install nyxbox via pip. (If you don't know how to, find an app called terminal, open it, and follow [these instructions](https://pip.pypa.io/en/stable/installation/))
```bash
pip install nyxbox
```
Ensure clang++ or g++ is installed for C++, and node for JavaScript support. Same goes for Java (any JDK should work! Working on adding custom paths so it doesn't matter where you install it)

#### 2. Run the App
```bash
nyxbox
```

### Git version

Clone git repo and cd. (find an app called terminal or something similar on your computer!)

```bash
git clone https://github.com/thisiscid/NyxBox
cd NyxBox
```

Then, run as a module.

```bash
python3 -m nyxbox.main
```

## Development

### Backend
This assumes that you have already cloned the repo (check above)

#### 1. Create a .env file
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
SLACK_CLIENT_ID=sample
SLACK_CLIENT_SECRET=sample_secret
SLACK_SIGNING_SECRET=sample_sign
SLACK_REDIRECT_URI=http://localhost:8000
SLACK_CHANNEL_WEBHOOK_URL=slack_here
SLACK_DMS_WEBHOOK_URL=slack_here
```
JWT_SECRET should be a long random string (e.g., use `openssl rand -hex 32`).

You will also have to to manually enter the frontend folder where NyxBox has been installed and check utils.py in order to change the link to your server, as the backend currently does not exist.

#### 2. Run via uvicorn
Inside of the backend folder, run 
```bash
uvicorn main:app
```

Make sure that it is running on port 8000. **Furthermore, set your redirects inside of Github and Google OAuth to localhost:8000/auth/github/callback or localhost:8000/auth/google/callback.**

## Notes
- Python 3.10+ recommended (The dev is running 3.12.1)
- C++ (clang++ or g++), JS (node.js), and Java (JDKs) runners require system dependencies. If they error out, make sure that you have them installed before raising an issue.
- Run in a terminal supporting Unicode and colors like [Ghostty](https://ghostty.org), [Alacritty](https://alacritty.org), or others.

## Credits
1. Textual for providing the underlying framework for the TUI
2. You! For using it! Thank you!
3. hack clubbers :3
