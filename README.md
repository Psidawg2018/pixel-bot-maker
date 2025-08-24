# Pixel Bot Maker

A simple GUI application for creating automated bot scripts that can find images or colors on the screen and perform actions.

## Overview

Pixel Bot Maker is a user-friendly tool designed for creating simple automation scripts (bots) without writing any code. It allows you to build a sequence of actions, such as clicking buttons or typing text, by identifying images or colors on your screen. It's perfect for automating repetitive tasks in games, applications, or websites.

### Screenshots

*A screenshot of the main interface would go here, showing the two-column layout, action sequence, and log.*

*A short GIF demonstrating the process of adding a step, saving a sequence, and running the bot would be ideal here.*

## Features

Pixel Bot Maker is packed with features to handle a wide variety of automation tasks.

-   **Visual Scripting:** Build automation sequences by adding and arranging steps in a simple, intuitive interface.
-   **Intelligent Vision:** Find objects on the screen using either image matching (with transparency support) or specific color values.
-   **Advanced Control Flow:** Go beyond simple scripts with loops, if/else branches, and time-based conditions.
-   **Dynamic Behavior with Variables:** Create and modify variables to build bots that can react to changing conditions, count items, or handle dynamic text.
-   **User-Friendly Configuration:** Use on-screen tools like an image-capture utility and a color sampler to easily configure your bot's targets.
-   **Customization:** Tailor the application to your needs with customizable hotkeys, color themes, and image-matching sensitivity.

**For a complete and detailed explanation of every feature, please see our [Feature Documentation](FEATURES.md).**

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

### v0.8.1 - (2025-08-24)
- **New Feature**: Added a **Dry Run Mode** to simulate a bot sequence by logging actions without executing them, allowing for safer testing.
- **Bug Fix**: Fixed a bug where **Time-based Conditions** would re-trigger multiple times within the same minute instead of only once.

### v0.8 - (2025-08-23)
- **New Feature**: Added a **Default Wait Times** setting to configure the default post-action wait for new steps.
- **Bug Fix**: The **Action Preview** feature now works correctly, displaying a visual indicator without freezing the application.
- **Bug Fix**: Fixed a GUI layout issue where the "Remove" button in the Action Sequence list was not fully visible.

### v0.7.5 - (2025-08-23)
- **Success/Failure Tracking & Bug Fix.**
- Added a new **On Failure** setting for simple actions, allowing the user to configure the bot to **Stop**, **Skip Step**, or **Retry Step** a set number of times if a target is not found.
- Fixed a bug where specific modifier keys (e.g., `ctrl_l`, `shift_r`) were not parsed correctly in **Key Combo** actions.

### v0.7.4 - (2025-08-23)
- **Time-based Conditions & Bug Fix.**
- Added a new **Time-based Condition** step to allow for scheduled execution of actions.
- Fixed a bug where the `cmd` key was not recognized as a modifier for key combinations.

### v0.7.3 - (2025-08-23)
- **Counter Variables & Variable Modification.**
- Added a new **Modify Variable** action to perform arithmetic (add/subtract) or `set` operations on variables, enabling counters and more dynamic logic.
- Improved the action list display for non-UI actions (`Set Variable`, `Modify Variable`, `OCR`).

### v0.7.2 - (2025-08-22)
- **If/Else Chains.**
- Added a new **If/Else** step to allow for conditional branching in automation sequences.

### v0.7.1 - (2025-08-22)
- **OCR Support.**
- Added an **OCR** action to read text from a specific screen region and save it to a variable.

### v0.7.0 - (2025-08-22)
- **Variable System.**
- Added a **Set Variable** action to create and store text variables.
- Variables can be used in other actions (e.g., "Type", "Key Combo") using `{{variable_name}}` syntax.

### v0.6.6 - (2025-08-22)
- **Keyboard Shortcut Actions.**
- Added **Key Combo** as a new action type, allowing the bot to press key combinations like `Ctrl+C` or `Alt+F4`.

### v0.6.5 - (2025-08-21)
- **Mouse Wheel Actions.**
- Added **Scroll** as a new action type, allowing the bot to scroll up or down.

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

### ✅ Completed (v0.1 – v0.8.1)
- [x] Core action sequencer (click, type, click offset, drag, fallback logic)
- [x] Conditional loops with fallback actions
- [x] Save/load sequences
- [x] Post-action wait (fixed/random) with configurable defaults
- [x] Frequently Used list
- [x] GUI refinements (two-column layout, step reordering, theme selection, hotkeys, hide bot option, layout fixes)
- [x] Loop Controls: "Repeat X times" and "Loop until condition"
- [x] Multiple Image Matching (OR logic in one step)
- [x] Image Similarity Threshold (fuzzy matching)
- [x] Screen Region Locking: Restrict actions to specific areas
- [x] Right-click Actions
- [x] Mouse Wheel Actions (scrolling support)
- [x] Keyboard Shortcuts: Key combos (Ctrl+Alt+Del, etc.)
- [x] If/Else Chains (multi-branch logic)
- [x] Variable System: Simple text variables
- [x] Counter Variables (track action counts)
- [x] Time-based Conditions (scheduled logic)
- [x] Success/Failure Tracking (log pass/fail, allow retry/skip)
- [x] OCR Support (text recognition for UI elements)
- [x] Action Preview: Show where the bot will click before executing
- [x] Dry Run Mode (simulate sequence without actions)

---

### 🎨 v0.8 – User Experience Upgrade
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
