# Pixel Bot Maker - Features

This document provides a detailed overview of every feature available in Pixel Bot Maker.

## Core Concepts

### Action Sequence
The core of every bot is the **Action Sequence**. This is a list of steps that the bot will execute in order, from top to bottom. You can add, edit, remove, and reorder these steps to create your automation workflow.

### Target Window
Before creating a sequence, you must select a **Target Window**. This is the application or game window that the bot will "look at" when searching for images or colors. This ensures the bot doesn't accidentally click on things outside of your intended application.

### Step Editor
The **Step Editor** is the window where you configure each step in your sequence. You can choose the step type (e.g., Simple Action, Loop), set the conditions for the step, and define the actions the bot should take.

---

## Step Types

Pixel Bot Maker has several types of steps you can add to your sequence.

### 1. Simple Action
This is the most common step type. It tells the bot to find a target on the screen and then perform a single action.

#### Find Target
A "Simple Action" step first needs to find a target. You can choose to find either a **Color** or an **Image**.

-   **Color:** The bot will search the target window for the exact color you specify.
    -   **Sample Color:** Use the on-screen eyedropper tool to select a color from anywhere on your screen.
-   **Image:** The bot will search the target window for an image that matches a template you provide.
    -   **Take Screenshot:** Use the screen capture tool to draw a box around the UI element (like a button or icon) you want the bot to find. Save this as a template image.
    -   **Multi-Image Matching:** You can add multiple image templates to a single step. The bot will perform its action on the *first* image it finds. This is useful if a button can have multiple states (e.g., a normal state and a "hovered" state).

#### Actions
Once the target is found, the bot can perform one of the following actions:

-   **Click:** Performs a standard left-click on the center of the found target.
-   **Right-click:** Performs a right-click on the center of the found target.
-   **Click with Offset:** Clicks at a position relative to the center of the found *image* target. For example, an offset of `X=10, Y=0` will click 10 pixels to the right of the image's center.
-   **Type:** Types a string of text. This does not require finding a target first.
-   **Key Combo:** Simulates a key combination (e.g., `ctrl+c`, `alt+f4`).
-   **Scroll:** Scrolls the mouse wheel up or down by a specified amount.
-   **Set Variable:** Creates or updates a variable with a specific text value. (See the Variable System section).
-   **Modify Variable:** Performs arithmetic (add/subtract) on a variable, or sets its value. Useful for creating counters.
-   **OCR (Optical Character Recognition):** Reads the text from a specified region of the screen and saves it to a variable.

### 2. Loop
A **Loop** step allows you to repeat a set of sub-actions multiple times.

-   **Repeat X Times:** The loop will execute its sub-actions a fixed number of times.
-   **Until Condition Met:** The loop will continue executing its sub-actions until a specific image appears on the screen. A "Max Retries" limit prevents the bot from getting stuck in an infinite loop.

### 3. If/Else
This step provides conditional logic. It checks if a condition involving a variable is true or false and executes a different branch of actions accordingly.

-   **Condition:** You define a condition based on a variable you've created (e.g., `if {{my_variable}} equals "some_value"`).
-   **IF Branch:** These actions run if the condition is true.
-   **ELSE Branch:** These actions run if the condition is false.

### 4. Time-based Condition
This step waits until a specific time of day is reached before executing its sub-actions.

-   **Time Condition:** You set the **Hour (0-23)** and **Minute (0-59)** for the condition to be met.
-   **Bot Time Clock:** The editor displays a real-time clock showing the bot's system time. Use this clock as a reference when setting your condition to avoid timezone confusion.
-   **Execution:** When the bot's system time matches the hour and minute you've set, it will run the sub-actions *once* and then proceed to the next step in the main sequence.

### 5. Conditional (Legacy)
This is an older, more complex step type that combines finding an image with a fallback action.

-   **Primary Target:** The image the bot tries to find.
-   **Max Retries:** The number of times the bot will try to find the primary target.
-   **Fallback Action:** If the primary target is not found after the specified number of retries, the bot will perform a fallback action (e.g., click a different button, scroll the mouse wheel).

---

## Advanced Features

### Variable System
You can store and reuse text using variables.

-   **Creating Variables:** Use the **Set Variable** action to create a variable and give it a value (e.g., variable `username` = `test_user`). The **OCR** action also creates a variable to store the text it reads.
-   **Using Variables:** In any text field (like the "Type" action or an "If/Else" condition), you can use `{{variable_name}}` to substitute the variable's value. For example, typing `Hello, {{username}}!` will result in `Hello, test_user!`.

### Configuration & Customization

-   **Screen Region Locking:** For any step that involves finding a target, you can define a specific rectangular area of the target window to search within. This makes the search much faster and more reliable, as the bot won't look for the image outside of this defined region.
-   **Image Similarity Threshold:** In the Settings tab, you can adjust the similarity threshold for image matching. A lower value (e.g., `0.7`) is "fuzzier" and will match images that are slightly different, while a higher value (e.g., `0.95`) requires a near-perfect match.
-   **Themes:** Choose between a light or dark theme in the Settings tab.
-   **Hotkeys:** Customize the global hotkey used to start and stop the bot.
-   **Post-Action Wait:** For any step, you can configure a wait time (either fixed or random) that occurs *after* the step's action is completed successfully. This is useful for making the bot's actions appear more human-like.
