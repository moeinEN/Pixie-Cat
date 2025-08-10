# Pixie Cat 🐱✨

**Pixie Cat** is a tiny pixelated cat living on your screen.  
The cat has a soul and lives with you all the time — through your good and bad memories.  
With Pixie Cat, you’re never truly alone.

![Pixie Cat Demo](https://github.com/moeinEN/Pixie-Cat/blob/main/demo/demo.mp4)

---

## Why This Exists

Pixie Cat started as a project for fun — a reminder that:

> Code isn’t just for solving problems.  
> It’s also for exploring ideas, expressing creativity, and building something just because it sparks joy.

It made me realize: **you can create a soul with coding**.  
And maybe, just maybe, it can make someone’s day a little better.

---

## About This Project

The pixel art cat assets are from the amazing free sprite pack:  
🎨 **[Tiny Cat by Kirisoft Store](https://kirisoft-store.itch.io/free-tiny-cat-with-all-animations)**

Pixie Cat runs on **Windows** and **Linux** (both Wayland and X11) — so whether you’re on your desktop or your laptop, your tiny companion is always with you.

---

## Features & Modes

Pixie Cat has multiple moods and animations. Each one reflects a part of your cat’s playful (and sometimes mysterious) life:

- **Attack** — Happens when the cursor is close to the cat.  
  ![Attack](https://github.com/moeinEN/Pixie-Cat/blob/main/demo/attack.gif)

- **Dead** — Happens when you quit or kill the program (sad emote).  
  ![Dead](https://github.com/moeinEN/Pixie-Cat/blob/main/demo/dead.gif)

- **Happy** — Happens when you scroll up or down on the cat.  
  ![Happy](https://github.com/moeinEN/Pixie-Cat/blob/main/demo/happy.gif)

- **Idle** — The cat’s normal resting state.  
  ![Idle](https://github.com/moeinEN/Pixie-Cat/blob/main/demo/idle.gif)

- **Run** — Happens when you left-click on the cat.  
  ![Run](https://github.com/moeinEN/Pixie-Cat/blob/main/demo/run.gif)

- **Sit** — When the cat feels relaxed enough to sit.  
  ![Sit](https://github.com/moeinEN/Pixie-Cat/blob/main/demo/sit.gif)

- **Walk** — The cat moves around your screen in a calm manner.  
  ![Walk](https://github.com/moeinEN/Pixie-Cat/blob/main/demo/walk.gif)

---

## Dependencies

Before installing, make sure you have:

- **Python** ≥ 3.10  
- **GTK 4**  
- **PyGObject** (for GTK integration)  
- **pkg-config** (for building GTK Python bindings)  

---

## Installation

### Windows
1. Make sure Python ≥ 3.10 is installed.  
2. Install GTK 4 for Windows.  
3. Install dependencies:  
   ```bash
   pip install pygobject
   ```

4. Clone the repository and run:

   ```bash
   python -m pixie
   ```
5. Or, simply run the prebuilt `.exe` from the releases page.

---

### Linux (Wayland & X11)

1. Install `GTK 4`, `PyGObject`, and `pkg-config` via your package manager.
2. Install Pixie Cat with:

   ```bash
   pip install pixie_cat-0.1.0-py3-none-any.whl --system-site-packages
   ```
3. Run it with:

   ```bash
   pixie
   ```

---
