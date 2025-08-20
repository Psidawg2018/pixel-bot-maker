# Pixel Bot Maker

A simple GUI application for creating automated bot scripts that can find images or colors on the screen and perform actions.

## Features

- **Tabbed Interface:** The main window is organized into "Main" and "Settings" tabs for a cleaner user experience.
- **Action Sequencing:** Create a list of steps for the bot to follow in order. You can easily reorder actions using "Move Up" and "Move Down" buttons.
- **Save/Load Sequences:** Save your created action sequences to a file and load them back in later.
- **Frequently Used List:** The top 3 most frequently loaded sequences are displayed on the main screen for quick one-click access.
- **Simple Actions:**
  - **Click:** Find a target (image or color) and click it.
  - **Click with Offset:** Find a target image and then click at a position relative to the center of that image, based on the X and Y offsets you provide.
  - **Type:** Find a target and then type a specified text string.
- **Loop Controls:**
  - **Repeat X Times:** Create a loop that executes a sequence of sub-actions a specified number of times.
  - **Loop Until Condition:** Create a loop that executes a sequence of sub-actions until a specific image appears on the screen. This loop includes a configurable retry limit to prevent infinite execution.
- **Conditional Logic (Legacy):**
  - **Conditional Loops:** Create complex steps that will try to find a primary image target. If the target isn't found, it can perform a fallback action.
  #### Fallback Actions
  - **Click**: This action requires a secondary image target. If the primary target is not found, the bot will search for this secondary target and click on it.
  - **Click with Offset**: This action also requires a secondary image target. It finds the target and then applies an X/Y offset before clicking. This is useful for clicking next to a known image when the button itself is not unique.
  - **Click and Drag**: This action does **not** use an image. Instead, it performs a drag action relative to the center of the target window. The X and Y offsets you provide will define the drag vector from the window's center. This is useful for actions like scrolling a list.
- **Human-like Delays:**
  - **Post-Action Wait:** For any step, you can configure a wait time that occurs after the action is successfully completed. This makes the automation appear less robotic.
  - **Wait Options:** You can choose between no wait, a fixed duration, or a random duration between a min and max value.
- **Interactive Configuration:**
  - **Window Selector:** Select a specific application window for the bot to operate within.
  - **Image Template Manager:** Take screenshots of screen regions to use as image targets.
  - **Multiple Image Matching:** For any image-based action, you can provide multiple template images. The bot will perform the action on the first one it finds (OR logic).
  - **Color Sampler:** An on-screen eyedropper tool to select a specific color to search for.
- **Customization:**
  - **Global Hotkey:** Customize the key used to start and stop the bot.
  - **Themes:** Choose between a light or dark theme.
  - **Defaults:** Set the default behavior for hiding the application window when the bot is running.

## Changelog

### v0.6.1 - (2025-08-20)
- **Critical Bug Fixes & Stability.**
- Fixed a critical crash (`AttributeError`) that occurred when creating or editing "Conditional Loop" and "Loop" steps.
- The underlying cause was an incomplete refactoring, which led to inconsistent UI and broken save logic.
- Standardized the image selection UI in the Step Editor to consistently use a multi-select listbox.
- Completely rewrote the save logic for "Conditional Loop" and "Loop" steps to be more robust and bug-free.
- Removed significant amounts of dead code and unused variables from the `StepEditor`.

### v0.6 - (2025-08-20)
- **Loop Controls & Multi-Image Matching.**
- Implemented a new **Loop** step type with two modes:
  - **Repeat X Times**: Executes a sequence of sub-actions a specified number of times.
  - **Until Condition Met**: Executes sub-actions until a specific image is found on screen. This includes a configurable retry limit to prevent infinite loops.
- The Step Editor now supports creating and editing nested actions within these loops.
- Added **Multiple Image Matching** (OR Logic). Any step that searches for an image can now be given multiple templates. The bot will act on the first one it finds.

### v0.5 - (2025-08-19)
- **New Features and Settings.**
- Added a **Settings Tab** to the main UI.
- Implemented **Theme Selection** (Light/Dark). The application must be restarted for the theme to apply.
- Implemented **Customizable Hotkeys**. Users can now set their own key to start/stop the bot.
- Added a setting to control the **default state of the "Hide Bot" checkbox**.
- Added a **"Frequently Used"** list to the main tab, showing the top 3 most loaded sequences for quick access.
- All settings are now saved to a `settings.json` file and persist between sessions.

### v0.4 - (2025-08-19)
- **UI Enhancements.**
- The "Step Editor" window has been made 25% wider to better accommodate complex step configurations.

### v0.3 - (2025-08-19)
- **Major GUI Refactor.**
- The main window layout has been changed from a single column to a **two-column layout**, with controls on the left and the log on the right.
- Added **"Move Up" and "Move Down" buttons** to the Action Sequence panel, allowing users to reorder steps.

### v0.2 - (2025-08-18)
- **New Features and Enhancements.**
- Added **Click with Offset** as a new action type for both simple and fallback actions.
- Added a **Post-Action Wait** setting for each step, with options for "None," "Fixed," or "Random" delays.
- Added **Do Nothing** as a new fallback action for conditional loops.
- Implemented **Save and Load** functionality for action sequences.
- The "Click and Drag" fallback action is now correctly based on the window center and does not require an image.

### v0.1 - (2025-08-16)
- **Initial feature set and bug fixes.**
- Implemented core action sequencer.
- Added "Conditional Loop" step type with fallback actions.
- Added "Click and Drag" as a possible fallback action.
- Fixed several UI bugs, including a crash in the Step Editor.
- Added a splash screen to force window selection on startup.
- Added `.gitignore` to exclude user-generated template files.

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


---

### 🛠 v0.6 – Core Automation Expansion
- [ ] Screen Region Locking: Restrict actions to specific areas
- [ ] Image Similarity Threshold (fuzzy matching)
- [ ] Keyboard Shortcuts: Key combos (Ctrl+Alt+Del, etc.)
- [ ] Mouse Wheel Actions (scrolling support)
- [ ] Right-click Actions

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
