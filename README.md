# Pixel Bot Maker

A simple GUI application for creating automated bot scripts that can find images or colors on the screen and perform actions.

## Features

- **Action Sequencing:** Create a list of steps for the bot to follow in order.
- **Save/Load Sequences:** Save your created action sequences to a file and load them back in later.
- **Simple Actions:**
  - **Click:** Find a target (image or color) and click it.

  - **Click with Offset:** Find a target image and then click at a position relative to the center of that image, based on the X and Y offsets you provide.
  - **Type:** Find a target and then type a specified text string.
- **Conditional Logic:**
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
