# Pocket Kitty: 3–5 minute recording guide

This is a local Python/PySide6 desktop prototype. Close any old instance with **right-click Kitty → Exit** before launching the latest code. Choose a simple desktop background and move other windows away from the pet before recording. Use whole-desktop capture so the separate speech and status tool windows appear in the video.

## Launch in PowerShell

```powershell
cd D:\AIPI_xiaomao
.\.venv\Scripts\python.exe main.py
```

If setting up on another Windows computer, first run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Recording walkthrough

1. Introduce Pocket Kitty as a transparent, always-on-top desktop companion. Leave the mouse away briefly to show gentle breathing. Explain that it stays quiet while you work.
2. Hover over Kitty and show Feed, Pat, Play, and Status. Move slowly between the cat and buttons to show the menu stays open. Drag Kitty to another spot, then drag the tiny right-paw arrow outward/inward to demonstrate proportional resizing.
3. Open Status and explain **Hungry**: the bar still represents fullness, so higher means better fed. Demonstrate Feed, Pat, and Play, letting each finish so the audience sees the new PNG, drawn effect, speech bubble, and return to idle. Show the live percentages. Extra action clicks during an animation are ignored.
4. Right-click Kitty and enable **Demo Mode**. Show its confirmation. Continue explaining the design or showing the status panel while waiting **15–20 seconds** for a proactive message. Leave the message visible for its four-second lifetime. Explain that normal mode uses **3–5 minutes**, so it is less distracting.
5. Show another interaction while Demo Mode remains on. Mention that a scheduled message waits until the interaction finishes. Close Status and move Kitty near a screen edge to show floating elements adjust their positions.
6. Right-click Kitty, disable Demo Mode, and show the confirmation. Finish with **right-click → Exit**, showing that the cat and floating windows disappear and the PowerShell prompt returns.

Suggested closing narration: “Everything is simulated locally with Python and Qt. The prototype needs no account, backend, AI model, or API.”

## Manual check before recording

- [ ] The cat has no rectangular background and stays over an ordinary application window.
- [ ] Breathing is subtle; the occasional float does not move the window or obscure work.
- [ ] Hovering, moving to all four buttons, delayed hiding, dragging, and paw-handle resizing work.
- [ ] Feed/Pat/Play each show the correct image, effect, readable bubble, and return to idle. Repeated action clicks do not overlap.
- [ ] Hungry/Happiness/Energy start at 65/65/75, then become 90/70/75 after Feed, 90/85/75 after Pat, and 85/100/60 after Play.
- [ ] Status updates live, toggles closed, and its × button works. Repeated opening does not freeze the pet.
- [ ] Demo Mode is checkmarked while enabled. A random bubble appears after 15–20 seconds, lasts about four seconds, and avoids an ongoing action. Turning Demo Mode off restores the quiet interval.
- [ ] Long bubbles wrap legibly. The bubble and status panel remain on-screen at the edges and do not cover the cat/menu. Check each monitor you intend to record on.
- [ ] Clicking unused transparent corners and the click-through bubble reaches the application below. The pet never steals typing focus when it speaks.
- [ ] Whole-desktop recording captures the cat, speech, status, and right-click menu.
- [ ] Exit works with a bubble/status panel open or during an action, leaves no orphan window, and allows a fresh launch. Ctrl+C in the launching PowerShell also exits cleanly.

These are manual checks to perform on the recording computer, not a claim that they have already been performed. Automated checks use Qt's offscreen platform.
