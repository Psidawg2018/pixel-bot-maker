# Pixel Bot Maker

A simple GUI application for creating automated bot scripts that can find images or colors on the screen and perform actions.

## Features

- **Action Sequencing:** Create a list of steps for the bot to follow in order.
- **Simple Actions:**
  - **Click:** Find a target (image or color) and click it.
  - **Type:** Find a target and then type a specified text string.
- **Conditional Logic:**
  - **Conditional Loops:** Create complex steps that will try to find a primary image target. If the target isn't found, it can perform a fallback action (like clicking a 'Next' button) and then retry, up to a specified number of times.
- **Interactive Configuration:**
  - **Window Selector:** Select a specific application window for the bot to operate within.
  - **Image Template Manager:** Take screenshots of screen regions to use as image targets.
  - **Color Sampler:** An on-screen eyedropper tool to select a specific color to search for.
- **Global Hotkey:** Press F9 to stop the bot at any time.

## Changelog

### v0.1 - (2025-08-16)
- **Initial feature set and bug fixes.**
- Implemented core action sequencer.
- Added "Conditional Loop" step type with fallback actions.
- Added "Click and Drag" as a possible fallback action.
- Fixed several UI bugs, including a crash in the Step Editor.
- Added a splash screen to force window selection on startup.
- Added `.gitignore` to exclude user-generated template files.
