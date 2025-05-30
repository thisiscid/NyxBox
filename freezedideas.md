# Freezebox

Cool features. But please add them after you actually finish the core.

---
## Core
- Fully working vend → solve → verdict loop
- Python runner complete (Done)
- JavaScript (Node.js subprocess) basic support (Done)
- Java (wrapper + subprocess) basic support
- C (wrapper + subprocess) basic support
- C++ (wrapper + subprocess) basic support (in progress)
- UI tabs update properly
### Polished Experience:

- Daemon text system w/ random + per-challenge messages
- Challenge structure supports flavor + hidden tests 
- Errors never crash the UI (hopefully)
- Output is safe, escaped, and readable

### Packaging:

- textual run . or CLI launcher
- Sample challenge set included
- README.md with install + demo instructions

##  Delayed Features
- **User defined text editor**
  - Allow user to edit in an editor of their choice instead of only the built-in one
- **Multiplayer / Co-op Mode (maybe?)**
  - Synchronized challenge solving
  - Daemon chat relay or shared log

- **Additional Languages**
  - C, C++, Bash, Go, Rust
  - Requires runner templates and sandboxing

- **User-Created Challenges**
  - JSON/GUI interface for writing and sharing
  - Needs challenge validation and directory handling

- **Challenge Leaderboard / Scoring**
  - Local or remote score tracking
  - Requires user profiles or save system

- **Persistent Daemon Mood**
  - Mood memory across sessions?
  - More expressive feedback based on performance history

- **Visual / ASCII FX**
  - ASCII vending animation
  - Text effects or boot screen

- **Profile System**
  - Save challenge progress per user
  - Login/select user at start

---

## Freezing Criteria

- Doesn't directly improve the vend → solve → verdict loop
- Requires nontrivial backend or persistent storage
- Adds >1 hour to implementation without core benefit