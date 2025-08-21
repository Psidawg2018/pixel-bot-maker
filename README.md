# Pixel Bot Maker

A simple GUI application for creating automated bot scripts that can find images or colors on the screen and perform actions.

## Overview

Pixel Bot Maker is a user-friendly tool designed for creating simple automation scripts (bots) without writing any code. It allows you to build a sequence of actions, such as clicking buttons or typing text, by identifying images or colors on your screen. It's perfect for automating repetitive tasks in games, applications, or websites.

### Screenshots

*A screenshot of the main interface would go here, showing the two-column layout, action sequence, and log.*

*A short GIF demonstrating the process of adding a step, saving a sequence, and running the bot would be ideal here.*

## Features

- **Tabbed Interface:** The main window is organized into "Main" and "Settings" tabs for a cleaner user experience.
- **Action Sequencing:** Create a list of steps for the bot to follow in order. You can easily reorder actions using "Move Up" and "Move Down" buttons.
- **Save/Load Sequences:** Save your created action sequences to a file and load them back in later.
- **Frequently Used List:** The top 3 most frequently loaded sequences are displayed on the main screen for quick one-click access.
- **Simple Actions:**
  - **Click:** Find a target (image or color) and click it.
  - **Right-click:** Find a target and right-click it.
  - **Click with Offset:** Find a target image and then click at a position relative to the center of that image, based on the X and Y offsets you provide.
  - **Type:** Find a target and then type a specified text string.
- **Loop Controls:**
  - **Repeat X Times:** Create a loop that executes a sequence of sub-actions a specified number of times.
  - **Loop Until Condition:** Create a loop that executes a sequence of sub-actions until a specific image appears on the screen. This loop includes a configurable retry limit to prevent infinite execution.
- **Conditional Logic (Legacy):**
  - **Conditional Loops:** Create complex steps that will try to find a primary image target. If the target isn't found, it can perform a fallback action (e.g., click a different button, scroll a list).
- **Human-like Delays:**
  - **Post-Action Wait:** For any step, you can configure a wait time that occurs after the action is successfully completed. This makes the automation appear less robotic.
- **Interactive Configuration:**
  - **Window Selector:** Select a specific application window for the bot to operate within.
  - **Image Template Manager:** Take screenshots of screen regions to use as image targets.
  - **Screen Region Locking:** Define a specific rectangular area within the target window to search for an image, improving both speed and reliability.
  - **Multiple Image Matching:** Provide multiple template images for an action; the bot will act on the first one it finds.
  - **Color Sampler:** An on-screen eyedropper tool to select a specific color to search for.
- **Customization:**
  - **Global Hotkey:** Customize the key used to start and stop the bot.
  - **Themes:** Choose between a light or dark theme.
  - **Image Similarity Threshold:** Adjust the strictness of image matching (fuzzy matching).

## Getting Started

### Requirements
- Python 3.x

### Installation
1. Clone or download the repository.
2. Open a terminal or command prompt in the project directory.
3. Install the required libraries using pip:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application
Once the dependencies are installed, you can run the application with the following command:
```bash
python main.py
```

## Usage (Quick Start)

Here’s a "Hello World" style tutorial to get you started:

1.  **Launch the App:** Run `python main.py`. A window selector will appear.
2.  **Select a Window:** Choose the application window you want the bot to interact with from the dropdown list and click "Select."
3.  **Add a Step:**
    - Click the "Add Step" button.
    - In the "Step Editor" window, select "Click" as the action type.
    - Click "Add Image" and use the screen capture tool to select a region of the screen (e.g., a button) you want the bot to click.
    - Click "Save Step."
4.  **Save the Sequence:**
    - Click the "Save Sequence" button on the main window and give your bot a name.
5.  **Run the Bot:**
    - Press the "Start Bot" button (or your configured hotkey).
    - The bot will now search for the image you selected and click it.

## Changelog

### v0.6.4 - (2025-08-20)
- **Right-click action.**
- Added **Right-click** as a new action type for simple actions.

### v0.6.3 - (2025-08-20)
- **Screen Region Locking & Bug Fix.**
- **New Feature**: Added **Screen Region Locking**.
- **Bug Fix**: Image-finding logic now correctly uses color information.

### v0.6.2 - (2025-08-20)
- **Image Similarity Threshold.**
- Added a new **Image Similarity Threshold** slider to the Settings tab.

### v0.6.1 - (2025-08-20)
- **Critical Bug Fixes & Stability.**
- Fixed a critical crash (`AttributeError`) related to "Conditional Loop" and "Loop" steps.

### v0.6 - (2025-08-20)
- **Loop Controls & Multi-Image Matching.**
- Implemented a new **Loop** step type ("Repeat X Times" and "Until Condition Met").
- Added **Multiple Image Matching** (OR Logic).

### v0.5 - (2025-08-19)
- **New Features and Settings.**
- Added a **Settings Tab**, **Theme Selection**, and **Customizable Hotkeys**.
- Added a **"Frequently Used"** list.

### v0.4 - (2025-08-19)
- **UI Enhancements.**
- The "Step Editor" window was made 25% wider.

### v0.3 - (2025-08-19)
- **Major GUI Refactor.**
- Changed to a **two-column layout** and added **"Move Up"/"Move Down"** buttons.

### v0.2 - (2025-08-18)
- **New Features and Enhancements.**
- Added **Click with Offset**, **Post-Action Wait**, and **Save/Load**.

### v0.1 - (2025-08-16)
- **Initial feature set and bug fixes.**
- Implemented core action sequencer and "Conditional Loop."

## 🛣️ Roadmap

### ✅ Completed (v0.1 – v0.6)
- [x] Core action sequencer (click, type, click offset, drag, fallback logic)
- [x] Conditional loops with fallback actions
- [x] Save/load sequences
- [x] Post-action wait (fixed/random)
- [x] Frequently Used list
- [x] GUI refinements (two-column layout, step reordering, theme selection, hotkeys, hide bot option)
- [x] Loop Controls: "Repeat X times" and "Loop until condition"
- [x] Multiple Image Matching (OR logic in one step)
- [x] Image Similarity Threshold (fuzzy matching)
- [x] Screen Region Locking: Restrict actions to specific areas
- [x] Right-click Actions

---

### 🛠 v0.6 – Core Automation Expansion
- [ ] Keyboard Shortcuts: Key combos (Ctrl+Alt+Del, etc.)
- [ ] Mouse Wheel Actions (scrolling support)

---

### ⚡ v0.7 – Logic & Intelligence
- [ ] If/Else Chains (multi-branch logic)
- [ ] Variable System: Simple text variables
- [ ] Counter Variables (track action counts)
- [ ] Time-based Conditions (scheduled logic)
- [ ] Success/Failure Tracking (log pass/fail, allow retry/skip)
- [ ] OCR Support (text recognition for UI elements)

---

### 🎨 v0.8 – User Experience Upgrade
- [ ] Action Preview: Show where the bot will click before executing
- [ ] Dry Run Mode (simulate sequence without actions)
- [ ] Real-time Step Highlighting in the GUI
- [ ] Undo/Redo for sequence editing
- [ ] Action Templates (common sequences like login loops, farming cycles, scroll lists)
- [ ] Emergency Stop Options (screen edge detection, mouse shake, etc.)

---

### 🔍 v0.9 – Debugging & Reliability
- [ ] Detailed Action Logging (with timestamps and results)
- [ ] Screenshot on Error (capture state when step fails)
- [ ] Backup Sequences (auto-save every X minutes)
- [ ] Configurable Error Handling: stop, retry, skip, or fallback sequence

---

### 🌐 v1.0 – Integration & Expansion
- [ ] Command Line Interface (run sequences via CLI/batch files)
- [ ] Built-in Scheduling (run sequences at set times)
- [ ] External Triggers (file changes, network events, API calls)
- [ ] Window Management (focus, minimize, maximize, switch between windows)
- [ ] Cross-Window Support (multiple apps simultaneously)

---

### 🚀 Beyond v1.0 – Stretch Goals
- [ ] AI-Assisted Image Recognition (robust matching for changed UI)
- [ ] Macro Recording Mode (record user actions into sequences)
- [ ] Plugin System / Scripting Hooks (Python/Lua for advanced logic)
- [ ] Cloud Sequence Syncing & Sharing
- [ ] Lightweight Mobile Companion (remote start/stop bots)
