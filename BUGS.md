# Bug Tracker

This file tracks the bugs found in the Pixel Bot Maker application and their resolution.

## Bug #1: `AttributeError` on adding a Conditional Loop step

-   **Date Found:** 2025-08-20
-   **Status:** Fixed
-   **Description:** The application would crash with an `AttributeError: 'StepEditor' object has no attribute '_build_image_selection_ui'` when trying to add or edit a "Conditional Loop" step.
-   **Root Cause Analysis:**
    1.  The method `_build_image_selection_ui` was called but did not exist.
    2.  There was a duplicated definition for the `build_loop_ui` method, one of which also called the non-existent method.
    3.  The UI for selecting images was inconsistent across different step types (some used single-selection dropdowns, others used multi-selection listboxes).
    4.  The `on_save` logic in the `StepEditor` was deeply flawed, with conflicting and buggy code for saving `conditional_loop` and `loop` steps.
-   **Fix:**
    1.  Removed the call to the non-existent `_build_image_selection_ui` method and standardized the UI to use listboxes for multi-image selection across all relevant step types.
    2.  Removed the duplicated `build_loop_ui` method definition.
    3.  Completely refactored the `on_save` method to correctly and consistently save data from the updated UI.
    4.  Removed several unused variables and dead code blocks that were remnants of an incomplete refactoring.
