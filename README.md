# Pocket Kitty

A small, local Windows desktop pet built with Python 3 and PySide6. It uses the provided watercolor cat PNG, with its original transparency. No browser, API, account, backend, or runtime network connection is used.

## Run on Windows (PowerShell)

Install Python 3.10 or newer with pip. Open PowerShell and run:

```powershell
cd D:\AIPI_xiaomao
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Installing PySide6 Essentials requires an internet connection once. It provides the `PySide6` widgets used here without the extra Qt modules and browser engine. Subsequent launches only need the last command. Virtual environment activation is unnecessary, so PowerShell execution-policy changes are unnecessary too.

The cat starts near the bottom-right of the primary desktop, above the taskbar, and stays above ordinary windows. Hold the left mouse button on the cat to drag it. Right-click the cat and choose **Exit** to close it. The app uses a frameless transparent tool window, so it does not have a normal taskbar button.

Hover over the cat to reveal four pastel circular buttons: **Feed** above, **Pat** to the left, **Play** to the right, and **Status** below. The menu fades and expands gently into place. Moving between the cat and buttons keeps it open; leaving starts a 300 ms delay before it fades out. Returning during that delay or fade keeps it open.

## Interact with Kitty

- **Feed**: switches to the eating PNG, draws a small fish moving into the mouth, then makes the fish disappear with a subtle chewing bounce. Shows **“Yummy! 🐟”** for about 2 seconds. Hunger decreases by 25, happiness increases by 5, and energy stays the same.
- **Pat**: switches to the happy PNG with floating pink hearts and a gentle squash/bounce. Shows **“Prrrr... 💗”** for about 2 seconds. Happiness increases by 15; hunger and energy stay the same.
- **Play**: switches to the tilted-head PNG, moves a feather left and right, and gently sways the cat. Shows **“Let's play! 🪶”** for about 3 seconds. Hunger increases by 5, happiness increases by 20, and energy decreases by 15.
- **Status**: opens a small floating panel beside the pet and radial menu, with live orange Hunger, pink Happiness, and mint Energy bars, numeric percentages, and a close button. The panel follows the pet when dragged and adjusts to screen edges. Opening it repeatedly reuses the same panel.

Every action returns to the idle PNG and clears its effects and bubble when finished. Only one pet action can run at a time: Feed, Pat, and Play are dimmed during an action, and extra clicks are ignored. Status stays available. Values start at **Hunger 35%, Happiness 65%, Energy 75%**, update immediately when an action is accepted, and are clamped to **0–100**. Higher Hunger means a hungrier cat. Values are kept only for the current session and reset when the app restarts; there is no automatic time-based decay.

The small **Size** slider beneath the cat appears with the hover menu. Drag it to resize the cat from **50% to 125%**, with a live preview and unchanged aspect ratio. Releasing the slider rearranges the buttons to fit. The slider stays visible while held, even if the pointer moves outside it. Size starts at 100% on each launch. Resizing is temporarily disabled during an action; dragging the cat remains available.

The window reserves enough space for the current cat size, the slider, and the four buttons, so revealing the menu does not move the cat. Dragging keeps that footprint inside the current monitor's work area, leaving the buttons accessible. Unused transparent corners are excluded from the native input mask, so applications beneath them remain clickable. While the menu is open, only the cat, controls, and narrow connecting paths receive input. Right-click Exit is still available on the cat.

## Stop or restart

Use **right-click the cat → Exit**, or press **Ctrl+C in the PowerShell window that launched it**. Ctrl+Break is also supported on Windows. The app handles these console signals and exits cleanly instead of raising `KeyboardInterrupt` inside a mouse callback. A small Qt timer lets Python receive console signals even while the cat is idle.

Only one instance per project folder can run at once. A second launch prints `Pocket Kitty is already running` and returns to the prompt. Exit the existing instance before relaunching to load code changes. The instance check uses a local lock file, without a server or network connection. Virtual environment activation and execution-policy changes are unnecessary when using the direct Python command above.

You can launch `main.py` from another working directory using its absolute path; assets are resolved relative to `main.py`.

## Files and future additions

- `main.py`: application startup and clear image-error dialog.
- `pocket_kitty/pet.py`: transparent window, drag behavior, context menu, and image loader.
- `pocket_kitty/radial_menu.py`: circular controls, painted icons, hover feedback, and reveal animation.
- `pocket_kitty/sprites.py`: validated PNG loading and shared frame alignment for each state.
- `pocket_kitty/effects.py`: cat motion, fish/hearts/feather drawings, and speech bubble painting.
- `pocket_kitty/status.py`: local pet values and the floating status panel.
- `pocket_kitty/lifecycle.py`: console signal handling and the local instance lock.
- `tests/test_pet.py`: automated interaction regression checks using Qt's test helpers.
- `tests/test_lifecycle.py`: subprocess checks for console shutdown, duplicate startup, and restart.
- `assets/cat_idle.png`: a copy of `xiaomao/水彩风灰色萌猫插画.png`; the original is preserved.
- `assets/cat_feed.png`: a copy of `xiaomao/贪吃猫咪与蓝色小鱼.png`.
- `assets/cat_pat.png`: a copy of `xiaomao/粉色爱心环绕的幸福灰猫.png`.
- `assets/cat_play.png`: a copy of `xiaomao/好奇歪头的灰色英短猫咪.png`.
- `requirements.txt`: the single runtime dependency, PySide6 Essentials.

The idle image is smoothly scaled to fit 240 × 260 pixels. The action PNGs have different padding, so they are drawn into the same transparent frame using measured body anchors in `SpriteLibrary.ANCHORS`. Their aspect ratios are preserved, and their body height and paw baseline align with idle. State changes keep the window, image frame, and menu geometry unchanged. Original PNGs are not edited. The supplied PNGs include some decorative fish, hearts, or feathers; the moving effects are additional local Qt drawings.

`PetWindow.ACTIONS` sets action durations and speech text. `PetStatus.DELTAS` sets the status changes. One Qt animation timeline drives each action's cat motion and effects; there are no background jobs or extra dependencies.

If `assets/cat_idle.png` is missing, startup shows an error dialog with the expected absolute path and exits after dismissal. A corrupt or unreadable image also produces an error. Restore the file with:

```powershell
Copy-Item -LiteralPath '.\xiaomao\水彩风灰色萌猫插画.png' -Destination '.\assets\cat_idle.png'
```

All four state PNGs are checked at startup. If another state image is missing, the error names that file. Restore the three action images with:

```powershell
Copy-Item -LiteralPath '.\xiaomao\贪吃猫咪与蓝色小鱼.png' -Destination '.\assets\cat_feed.png'
Copy-Item -LiteralPath '.\xiaomao\粉色爱心环绕的幸福灰猫.png' -Destination '.\assets\cat_pat.png'
Copy-Item -LiteralPath '.\xiaomao\好奇歪头的灰色英短猫咪.png' -Destination '.\assets\cat_play.png'
```

## Basic checks

```powershell
.\.venv\Scripts\python.exe -m compileall -q main.py pocket_kitty
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

For a manual desktop check, launch the app, confirm there is no rectangular background, drag the cat, place another ordinary window beneath it to check always-on-top behavior, then right-click → Exit.

For the radial menu, hover over the cat and move slowly to each button. Check each action's image, moving effect, speech bubble, and return to idle. Open Status and check that Feed changes the initial values to 10/70/75, Pat then changes them to 10/85/75, and Play then changes them to 15/100/60. Try clicking an action repeatedly while it runs: only the first click should count. Close Status with its × button. Move outside the pet and confirm the menu hides after a short delay, then return quickly to check it stays open. Drag toward each screen edge and confirm the menu and status panel fit. Resize while idle and repeat an action. Click a transparent corner over another application to check click-through behavior. Close any previously running Pocket Kitty instance and relaunch to load code changes.

The eighteen automated checks run offscreen and cover action images, real-time completion, speech text, moving effects, return to idle, exact status changes and limits, duplicate click prevention, the live/closable status panel, shared image geometry, hover behavior, resizing, screen bounds/input masks, dragging during actions, missing images, Exit, duplicate launch prevention, and clean shutdown when SIGINT (the Ctrl+C signal) arrives while Qt runs. The lifecycle check uses a temporary project copy so it does not disturb a running pet. Native Windows layering and pointer hit-testing should also be checked with the manual steps above.
