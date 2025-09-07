# How to Create Script Templates

This document explains how to create and add new script templates to the Pixel Bot.

## 1. Template Structure

The template system consists of three main parts:
1.  **Category Directories**: Folders to organize template files (e.g., `gaming/`, `productivity/`).
2.  **Template Files**: JSON files containing the sequence of steps for a template.
3.  **Manifest File**: `template_manifest.json`, which registers templates and their metadata.

## 2. Creating a New Template

### Step 2.1: Create the Template JSON File

1.  **Create a new JSON file** in the appropriate category directory (e.g., `pixel_bot/templates/gaming/my_new_template.json`).
2.  **Define the sequence of steps** in the JSON file. Each step is an object in a list, following the same format as the main application's sequence files. You can create a sequence in the bot and save it to see the structure.

    **Example: `my_new_template.json`**
    ```json
    [
        {
            "step_type": "simple",
            "window_title": "CHANGE_ME",
            "detection_mode": "Image",
            "action_type": "Click",
            "detection_target": ["templates/placeholder.png"],
            "detection_target_name": "my_image.png",
            "wait_params": { "type": "Fixed", "fixed_time": 1.0 }
        }
    ]
    ```
    *   **`window_title`**: Use a placeholder like `"CHANGE_ME"` to remind the user to set it.
    *   **`detection_target`**: For image-based steps, you can reference a real image file (e.g., `templates/my_app/my_image.png`) or use the generic `templates/placeholder.png`.

### Step 2.2: Add Metadata to the Manifest

1.  **Open `pixel_bot/templates/template_manifest.json`**.
2.  **Add a new JSON object** to the `templates` list with the following information:

    ```json
    {
        "name": "My New Template",
        "category": "Gaming",
        "description": "A short but clear description of what this template does.",
        "difficulty": "Beginner",
        "estimated_time": "2 mins",
        "file": "my_new_template.json"
    }
    ```

    *   **`name`**: The display name of the template in the gallery.
    *   **`category`**: The category it belongs to. This must match one of the existing directory names (e.g., "Gaming", "Productivity").
    *   **`description`**: A user-friendly description.
    *   **`difficulty`**: "Beginner", "Intermediate", or "Advanced".
    *   **`estimated_time`**: A string representing the estimated time to configure the template (e.g., "5 mins").
    *   **`file`**: The filename of the JSON you created in Step 2.1.

## 3. Best Practices

*   **Use Placeholders**: For image paths and window titles that are user-specific, use clear placeholders like `"CHANGE_ME"` or `"placeholder.png"`.
*   **Keep Templates Focused**: Each template should accomplish a single, clear task.
*   **Write Good Descriptions**: The description is the main way for users to understand what your template does before inserting it. Be clear and concise.
*   **Use Variables**: For templates that involve user input (like login forms), use the `Set Variable` and `Type` actions to show how to use the variable system.
