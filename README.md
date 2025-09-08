# Pixel Bot Maker v1.0.1

A simple GUI application for creating automated bot scripts that can find images or colors on the screen and perform actions.

## Overview

Pixel Bot Maker is a user-friendly tool designed for creating simple automation scripts (bots) without writing any code. It allows you to build a sequence of actions, such as clicking buttons or typing text, by identifying images or colors on your screen. It's perfect for automating repetitive tasks in games, applications, or websites.

The user interface has been recently updated with a modern, flat design for a more professional and intuitive experience.

## Features

Pixel Bot Maker is packed with features to handle a wide variety of automation tasks.

-   **Visual Scripting:** Build automation sequences by adding and arranging steps in a simple, intuitive interface.
-   **Intelligent Vision:** Find objects on the screen using either image matching (with transparency support) or specific color values.
-   **Advanced Control Flow:** Go beyond simple scripts with loops, if/else branches, time-based conditions, and timed waits.
-   **Dynamic Behavior with Variables:** Create and modify variables to build bots that can react to changing conditions, count items, or handle dynamic text.
-   **User-Friendly Configuration:** Use on-screen tools like an image-capture utility and a color sampler to easily configure your bot's targets.
-   **Robust Feedback**: Get immediate visual feedback with an enhanced action preview that draws a border around found images.
-   **Customization:** Tailor the application to your needs with customizable hotkeys and image-matching sensitivity.

**For a complete history of changes, please see the [CHANGELOG.md](CHANGELOG.md).**

## Getting Started

### Requirements
- Python 3.x
- Tesseract OCR (must be installed and in your system's PATH for OCR actions to work)

### Installation
1. Clone or download the repository.
2. Open a terminal or command prompt in the project directory.
3. Install the required libraries using pip:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application
Once the dependencies are installed, you can run the application as a Python module from the root directory:
```bash
python -m pixel_bot
```

## Usage (Quick Start)

Here’s a "Hello World" style tutorial to get you started:

1.  **Launch the App:** Run `python -m pixel_bot`. A window selector will appear.
2.  **Select a Window:** Choose the application window you want the bot to interact with from the dropdown list and click "Select."
3.  **Add a Step:**
    - Click the "Add" button in the "Action Sequence" area.
    - In the "Step Editor" window, select "Click" as the action type.
    - Click "Take Screenshot" and use the screen capture tool to select a region of the screen (e.g., a button) you want the bot to click. Save the template image.
    - Click "Save Step."
4.  **Save the Sequence:**
    - Click the "Save Sequence" button on the main window and give your bot a name.
5.  **Run the Bot:**
    - Press the "Start Bot" button (or your configured hotkey).
    - The bot will now search for the image you selected and click it.

## 🛣️ Roadmap

### 🎨 Next Up – User Experience
- [ ] Real-time Step Highlighting in the GUI
- [ ] Undo/Redo for sequence editing
- [ ] Action Templates (common sequences like login loops, farming cycles, scroll lists)
- [ ] Emergency Stop Options (screen edge detection, mouse shake, etc.)

### 🔍 Future – Debugging & Reliability
- [ ] Detailed Action Logging (with timestamps and results)
- [ ] Screenshot on Error (capture state when step fails)
- [ ] Backup Sequences (auto-save every X minutes)
- [ ] Configurable Error Handling: stop, retry, skip, or fallback sequence

### 🌐 Long-Term – Integration & Expansion
- [ ] Command Line Interface (run sequences via CLI/batch files)
- [ ] Built-in Scheduling (run sequences at set times)
- [ ] External Triggers (file changes, network events, API calls)
- [ ] Window Management (focus, minimize, maximize, switch between windows)
- [ ] Cross-Window Support (multiple apps simultaneously)
- [ ] AI-Assisted Image Recognition (robust matching for changed UI)
- [ ] Macro Recording Mode (record user actions into sequences)
- [ ] Plugin System / Scripting Hooks (Python/Lua for advanced logic)
- [ ] Cloud Sequence Syncing & Sharing
- [ ] Lightweight Mobile Companion (remote start/stop bots)
