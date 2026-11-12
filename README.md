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

- **Feed**: switches to the eating PNG, draws a small fish moving into the mouth, then makes the fish disappear with a subtle chewing bounce. Shows **“Yummy! 🐟”** for about 2 seconds. Fullness increases by 25, happiness increases by 5, and energy stays the same.
- **Pat**: switches to the happy PNG with floating pink hearts and a gentle squash/bounce. Shows **“Prrrr... 💗”** for about 2 seconds. Happiness increases by 15; fullness and energy stay the same.
- **Play**: switches to the tilted-head PNG, moves a feather left and right, and gently sways the cat. Shows **“Let's play! 🪶”** for about 3 seconds. Fullness decreases by 5, happiness increases by 20, and energy decreases by 15.
- **Status**: opens a small floating panel beside the pet and radial menu, with live orange Hungry, pink Happiness, and mint Energy bars, numeric percentages, and a close button. The panel follows the pet when dragged and adjusts to screen edges. Click Status again to close it; opening it reuses the same panel. Panel placement is coalesced outside native window-move callbacks to avoid move feedback loops.

Speech appears in a rounded chat bubble above and to the left of Kitty, with a small tail pointing toward the cat. Near the left screen edge it can flip to the upper right. The bubble follows dragging, stays separate from the cat and menu, and is click-through.

## Quiet companionship and Demo Mode

While idle, Kitty breathes gently on a 5.5-second cycle, with less than 0.4% vertical scale variation. An occasional soft float lasts 2.8 seconds and moves at most about 2 pixels. These are painted inside the existing cat frame; the window stays still. The motion pauses during dragging/resizing, and the action images blend smoothly in and out over the start/end of each interaction.

A local timer chooses from seven predefined messages, including “Meow~”, “Can you pet me? 💗”, and “Don't forget to take a break!”. Normal mode schedules messages every **3–5 minutes**; each stays for **4 seconds**, then fades out. Longer messages wrap inside a cream rounded bubble with a soft shadow and dark text. No message repeats immediately. The bubble prefers the upper-left position, but can use another clear area near screen edges when the cat, menu, and status panel occupy that corner.

**Right-click the cat → Demo Mode** enables or disables the checkmarked mode. Demo Mode schedules messages every **15–20 seconds**. A small confirmation bubble shows the selected mode. Toggling off immediately restores the normal scheduling range. Random messages and confirmations wait during Feed, Pat, Play, dragging, resizing, or the context menu. Actions take priority over an ambient bubble. At most one pending random message is kept, so missed messages do not build up in a queue. Demo Mode starts off on every launch.

Every action returns to the idle PNG and clears its effects and bubble when finished. Only one pet action can run at a time: Feed, Pat, and Play are dimmed during an action, and extra clicks are ignored. Status stays available. Values start at **Hungry 65%, Happiness 65%, Energy 75%**, update immediately when an action is accepted, and are clamped to **0–100**. The displayed Hungry bar retains fullness semantics: higher means a better-fed cat; feeding fills the orange bar instead of emptying a hunger bar. Values are kept only for the current session and reset when the app restarts; there is no automatic time-based decay.

Hover over the cat to reveal a small **diagonal-arrow resize handle beside its right paw**. Hold the handle and drag outward to enlarge, or inward to shrink, from **50% to 125%**. The cat, all four circular buttons, icons, labels, and spacing scale together in a fixed proportion. Buttons are smaller and sit closer to the cat. During a resize, the cat's center stays fixed and the menu stays open; releasing the handle keeps the group inside the screen. Size starts at 100% on each launch. Resizing is temporarily disabled during an action; dragging the cat remains available.

At 100%, the compact window footprint is 320 × 352 logical pixels; the buttons use 64-pixel frames instead of the previous 100-pixel frames. Buttons now sit just above the ears, beside the body, and below the paws. Labels are 50% larger than the previous compact version. The paw handle has half its previous visual diameter, with a larger invisible mouse target for reliable dragging. The entire footprint scales proportionally. Revealing the menu does not move the cat. Dragging keeps the group inside the current monitor's work area, leaving the buttons accessible. Unused transparent corners are excluded from the native input mask, so applications beneath them remain clickable. While the menu is open, only the cat, controls, and narrow connecting paths receive input. Right-click Exit is still available on the cat.

## Stop or restart

Use **right-click the cat → Exit**, or press **Ctrl+C in the PowerShell window that launched it**. Ctrl+Break is also supported on Windows. The app handles these console signals and exits cleanly instead of raising `KeyboardInterrupt` inside a mouse callback. A small Qt timer lets Python receive console signals even while the cat is idle.

Closing the pet or quitting stops idle, speech, hover, and action timers/animations, hides both owned floating windows, and releases the local instance lock.

Only one instance per project folder can run at once. A second launch prints `Pocket Kitty is already running` and returns to the prompt. Exit the existing instance before relaunching to load code changes. The instance check uses a local lock file, without a server or network connection. Virtual environment activation and execution-policy changes are unnecessary when using the direct Python command above.

You can launch `main.py` from another working directory using its absolute path; assets are resolved relative to `main.py`.

## Files and future additions

- `main.py`: application startup and clear image-error dialog.
- `pocket_kitty/pet.py`: transparent window, drag behavior, context menu, and image loader.
- `pocket_kitty/radial_menu.py`: circular controls, painted icons, hover feedback, and reveal animation.
- `pocket_kitty/resize_handle.py`: the small right-paw drag handle for proportional group resizing.
- `pocket_kitty/sprites.py`: validated PNG loading and shared frame alignment for each state.
- `pocket_kitty/effects.py`: cat motion, fish/hearts/feather drawings, and speech bubble painting.
- `pocket_kitty/companion.py`: subtle idle updates, predefined random speech, message priority, and Demo Mode scheduling.
- `pocket_kitty/status.py`: local pet values and the floating status panel.
- `pocket_kitty/lifecycle.py`: console signal handling and the local instance lock.
- `tests/test_pet.py`: automated interaction regression checks using Qt's test helpers.
- `tests/test_lifecycle.py`: subprocess checks for console shutdown, duplicate startup, and restart.
- `tests/test_companion.py`: idle bounds, message intervals/lifetime, mode switching, priorities, long bubbles, screen edges, and timer cleanup.
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

For the radial menu, hover over the cat and move slowly to each button. Check each action's image, moving effect, speech bubble, and return to idle. Open Status and check that Feed changes the initial values to 90/70/75, Pat then changes them to 90/85/75, and Play then changes them to 85/100/60. Try clicking an action repeatedly while it runs: only the first click should count. Close Status with its × button. Move outside the pet and confirm the menu hides after a short delay, then return quickly to check it stays open. Drag toward each screen edge and confirm the menu and status panel fit. Resize while idle and repeat an action. Click a transparent corner over another application to check click-through behavior. Close any previously running Pocket Kitty instance and relaunch to load code changes.

The thirty automated checks run offscreen and cover the existing interactions plus idle bounds, smooth state blends, Demo Mode menu wiring, interval ranges, actual four-second speech expiry, deferred messages, long-message placement with the status panel at screen corners, and timer/animation cleanup. Minute-scale intervals are checked as scheduled values; tests use a short timer to exercise delivery without waiting several minutes. The lifecycle check uses a temporary project copy so it does not disturb a running pet. Native Windows layering and pointer hit-testing should also be checked with the manual steps above. See [DEMO.md](DEMO.md) for a short recording walkthrough and manual checklist.

## Prototype limitations

- Status, size, and Demo Mode reset when the application restarts; there is no saved game or automatic status decay.
- The seven messages are predefined random phrases, not generated dialogue or an inference about the user's activity. The hungry phrase can appear even when Fullness is high.
- PNG states are static artwork with local transforms and drawn effects, rather than frame-by-frame character animation. Decorative props already present in the supplied PNGs stay in the image.
- Emoji appearance depends on installed Windows fonts. Very small scaling makes the labels smaller too.
- Offscreen tests and Qt-rendered previews do not verify native desktop click-through, always-on-top behavior, recording software capture, or mixed-DPI/multi-monitor behavior. These need the manual checks on the recording computer. Extremely small work areas may not fit every floating element at once; use a typical desktop of at least 800 × 600 logical pixels.
