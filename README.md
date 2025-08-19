# Pixel Bot Maker

A simple GUI application for creating automated bot scripts that can find images or colors on the screen and perform actions.

## Features

- **Action Sequencing:** Create a list of steps for the bot to follow in order.
- **Save/Load Sequences:** Save your created action sequences to a file and load them back in later.
- **Simple Actions:**
  - **Click:** Find a target (image or color) and click it.
  - **Click with Offset:** Find a target image, then click at a specified X/Y offset from its center.
  - **Type:** Find a target and then type a specified text string.
- **Conditional Logic:**
  - **Conditional Loops:** Create complex steps that will try to find a primary image target. If the target isn't found, it can perform a fallback action (like clicking a 'Next' button, clicking another target, or doing nothing) and then retry, up to a specified number of times.
- **Human-like Behavior:**
  - **Post-Action Wait:** Add a configurable delay after each step completes. The wait can be a fixed duration or a random duration within a specified range, helping to mimic human behavior.
- **Interactive Configuration:**
  - **Window Selector:** Select a specific application window for the bot to operate within.
  - **Image Template Manager:** Take screenshots of screen regions to use as image targets.
  - **Color Sampler:** An on-screen eyedropper tool to select a specific color to search for.
- **Global Hotkey:** Press F9 to stop the bot at any time.

## Changelog

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
