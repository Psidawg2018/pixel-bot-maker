# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-09-07

### Added
- **"Wait" Step**: A new step type to pause the bot for a specified duration.
- **Enhanced Action Preview**: Action previews for image-based steps now show a yellow border around the found image for better visibility.
- **Robust Logging**: Implemented Python's `logging` module for logging to both the GUI and a file (`pixel_bot.log`).
- **Configuration Validation**: The bot now validates sequences before running to prevent errors from invalid configurations.

### Changed
- **Major Refactoring**: The entire application was restructured from a monolithic script into a proper Python package (`pixel_bot`) with a clear separation of concerns (core, gui, utils).
- **Hotkey System Overhaul**: Replaced the unreliable hotkey mechanism with a single, persistent listener for robust start/stop functionality.
- The application is now run as a module via `python -m pixel_bot`.

### Fixed
- **Critical**: Fixed a fundamental bug in variable evaluation for conditional (If/Else) steps, which now work reliably.
- Fixed a UI bug that caused the Step Editor to lose focus after taking a screenshot.
- Fixed a display bug where "If/Else" steps were shown as "Unknown Step Type".
- Addressed numerous initial bugs, including `NameError` crashes and silent failures when saving steps.

---
## [0.8.3] - 2025-08-24
- **Critical Fix**: Refactored the core execution logic for **Loop** steps to prevent an uncontrolled process explosion that would freeze the application. Loops are now managed sequentially on the main execution stack, ensuring stability.

## [v0.8.2] - (2025-08-24)
- **Bug Fix**: Fixed a critical bug where running a sequence with steps that had no post-action wait time would cause the application to freeze due to an infinite recursive loop.

## [v0.8.1] - (2025-08-24)
- **New Feature**: Added a **Dry Run Mode** to simulate a bot sequence by logging actions without executing them, allowing for safer testing.
- **Bug Fix**: Fixed a bug where **Time-based Conditions** would re-trigger multiple times within the same minute instead of only once.

## [v0.8] - (2025-08-23)
- **New Feature**: Added a **Default Wait Times** setting to configure the default post-action wait for new steps.
- **Bug Fix**: The **Action Preview** feature now works correctly, displaying a visual indicator without freezing the application.
- **Bug Fix**: Fixed a GUI layout issue where the "Remove" button in the Action Sequence list was not fully visible.

## [v0.7.5] - (2025-08-23)
- **Success/Failure Tracking & Bug Fix.**
- Added a new **On Failure** setting for simple actions, allowing the user to configure the bot to **Stop**, **Skip Step**, or **Retry Step** a set number of times if a target is not found.
- Fixed a bug where specific modifier keys (e.g., `ctrl_l`, `shift_r`) were not parsed correctly in **Key Combo** actions.

## [v0.7.4] - (2025-08-23)
- **Time-based Conditions & Bug Fix.**
- Added a new **Time-based Condition** step to allow for scheduled execution of actions.
- Fixed a bug where the `cmd` key was not recognized as a modifier for key combinations.

## [v0.7.3] - (2025-08-23)
- **Counter Variables & Variable Modification.**
- Added a new **Modify Variable** action to perform arithmetic (add/subtract) or `set` operations on variables, enabling counters and more dynamic logic.
- Improved the action list display for non-UI actions (`Set Variable`, `Modify Variable`, `OCR`).

## [v0.7.2] - (2025-08-22)
- **If/Else Chains.**
- Added a new **If/Else** step to allow for conditional branching in automation sequences.

## [v0.7.1] - (2025-08-22)
- **OCR Support.**
- Added an **OCR** action to read text from a specific screen region and save it to a variable.

## [v0.7.0] - (2025-08-22)
- **Variable System.**
- Added a **Set Variable** action to create and store text variables.
- Variables can be used in other actions (e.g., "Type", "Key Combo") using `{{variable_name}}` syntax.

## [v0.6.6] - (2025-08-22)
- **Keyboard Shortcut Actions.**
- Added **Key Combo** as a new action type, allowing the bot to press key combinations like `Ctrl+C` or `Alt+F4`.

## [v0.6.5] - (2025-08-21)
- **Mouse Wheel Actions.**
- Added **Scroll** as a new action type, allowing the bot to scroll up or down.

## [v0.6.4] - (2025-08-20)
- **Right-click action.**
- Added **Right-click** as a new action type for simple actions.

## [v0.6.3] - (2025-08-20)
- **Screen Region Locking & Bug Fix.**
- **New Feature**: Added **Screen Region Locking**.
- **Bug Fix**: Image-finding logic now correctly uses color information.

## [v0.6.2] - (2025-08-20)
- **Image Similarity Threshold.**
- Added a new **Image Similarity Threshold** slider to the Settings tab.

## [v0.6.1] - (2025-08-20)
- **Critical Bug Fixes & Stability.**
- Fixed a critical crash (`AttributeError`) related to "Conditional Loop" and "Loop" steps.

## [v0.6] - (2025-08-20)
- **Loop Controls & Multi-Image Matching.**
- Implemented a new **Loop** step type ("Repeat X Times" and "Until Condition Met").
- Added **Multiple Image Matching** (OR Logic in one step).

## [v0.5] - (2025-08-19)
- **New Features and Settings.**
- Added a **Settings Tab**, **Theme Selection**, and **Customizable Hotkeys**.
- Added a **"Frequently Used"** list.

## [v0.4] - (2025-08-19)
- **UI Enhancements.**
- The "Step Editor" window was made 25% wider.

## [v0.3] - (2025-08-19)
- **Major GUI Refactor.**
- Changed to a **two-column layout** and added **"Move Up"/"Move Down"** buttons.

## [v0.2] - (2025-08-18)
- **New Features and Enhancements.**
- Added **Click with Offset**, **Post-Action Wait**, and **Save/Load**.

## [v0.1] - (2025-08-16)
- **Initial feature set and bug fixes.**
- Implemented core action sequencer and "Conditional Loop."
