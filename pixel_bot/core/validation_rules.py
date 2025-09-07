"""
This file contains individual validation rule functions.

Each function should accept a step and an optional context,
and return a ValidationResult object. The context can be used
for sequence-level checks, like ensuring a variable is defined
before it is used.
"""
import os
import re
from .script_validator import ValidationResult

def validate_required_fields(step):
    """Checks for the presence of essential fields in a step."""
    result = ValidationResult()
    if 'step_type' not in step:
        result.add_error("Step is missing the required 'step_type' field.")
        # No point in checking further if we don't know the type
        return result

    # Most steps that interact with a window need a target
    if step['step_type'] in ['simple', 'conditional_loop', 'loop'] and not step.get('window_title'):
        result.add_error("Step is missing a 'window_title'.")

    if step['step_type'] == 'simple' and 'action_type' not in step:
        result.add_error("Simple step is missing the required 'action_type' field.")

    return result

def validate_image_paths(step):
    """Checks if image files specified in a step exist."""
    result = ValidationResult()

    # This rule only applies to steps that use image detection
    if step.get('detection_mode') != 'Image' and 'primary_target' not in step:
        return result

    targets_to_check = []

    # Handle simple steps
    if step.get('detection_mode') == 'Image' and step.get('detection_target'):
        targets = step['detection_target']
        if isinstance(targets, str):
            targets_to_check.append(targets)
        elif isinstance(targets, list):
            targets_to_check.extend(targets)

    # Handle conditional_loop primary target
    if 'primary_target' in step:
        primary_target = step.get('primary_target', {})
        targets = primary_target.get('detection_target', [])
        if isinstance(targets, str):
            targets_to_check.append(targets)
        elif isinstance(targets, list):
            targets_to_check.extend(targets)

    # Handle conditional_loop fallback target
    if 'on_fail' in step:
        on_fail = step.get('on_fail', {})
        if on_fail.get('detection_mode') == 'Image':
            targets = on_fail.get('detection_target', [])
            if isinstance(targets, str):
                targets_to_check.append(targets)
            elif isinstance(targets, list):
                targets_to_check.extend(targets)

    # Handle 'until' loop condition target
    if step.get('loop_mode') == 'until' and step.get('loop_condition_target'):
        targets = step['loop_condition_target']
        if isinstance(targets, str):
            targets_to_check.append(targets)
        elif isinstance(targets, list):
            targets_to_check.extend(targets)

    for path in targets_to_check:
        # The Step Editor saves paths relative to the root (e.g., "templates/image.png").
        # The templates themselves are stored in "pixel_bot/templates/".
        # This is a known inconsistency that should be fixed, but for now, the validator
        # should be lenient and check the most likely correct path.
        # The correct path for assets should be relative to the project root.
        if not os.path.exists(path):
             result.add_error(f"Image file not found at path: '{path}'")

    return result

def validate_variable_syntax(step):
    """Checks for basic syntax errors in variable usage, like mismatched braces."""
    result = ValidationResult()
    variable_pattern = re.compile(r"\{.*?\}")

    text_to_check = []

    # Check 'text' field for 'Type' action
    if step.get('action_type') == 'Type':
        text_to_check.append(step.get('action_params', {}).get('text', ''))

    # Check 'value' field for 'Set Variable' action
    if step.get('action_type') == 'Set Variable':
        text_to_check.append(step.get('action_params', {}).get('variable_value', ''))

    for text in text_to_check:
        # Check for mismatched braces
        if text.count('{') != text.count('}'):
            result.add_warning(f"Mismatched curly braces in text: '{text}'")
            continue # Don't check further if braces are mismatched

        # Check for nested or malformed braces
        for match in variable_pattern.finditer(text):
            var = match.group(0)
            if var.count('{') > 1 or var.count('}') > 1:
                result.add_warning(f"Potentially malformed variable syntax found: '{var}'")
            if var == '{}':
                result.add_warning("Empty variable '{}' found. This will be treated as literal text.")

    return result

def validate_wait_times(step):
    """Warns if a wait time is very short."""
    result = ValidationResult()
    wait_params = step.get('wait_params', {})
    wait_type = wait_params.get('type')

    if wait_type == 'Fixed':
        try:
            if float(wait_params.get('fixed_time', 1.0)) < 0.1:
                result.add_warning("Fixed wait time is very short (<0.1s), which may cause timing issues.")
        except (ValueError, TypeError):
            result.add_error("Invalid value for fixed wait time. Must be a number.")

    elif wait_type == 'Random':
        try:
            if float(wait_params.get('min_time', 1.0)) < 0.1:
                result.add_warning("Random minimum wait time is very short (<0.1s), which may cause timing issues.")
        except (ValueError, TypeError):
            result.add_error("Invalid value for random wait time. Must be a number.")

    return result

def validate_unreachable_code(step):
    """Suggests improvements for conditional branches that are empty."""
    result = ValidationResult()
    if step.get('step_type') == 'conditional_branch':
        if not step.get('if_branch') and not step.get('else_branch'):
            result.add_suggestion("Conditional branch has no actions in either the 'if' or 'else' block.")
        elif not step.get('if_branch'):
            result.add_suggestion("The 'if' block of this conditional is empty.")
    return result

def validate_variable_definition(sequence):
    """
    Checks the entire sequence to ensure variables are defined before they are used.
    """
    result = ValidationResult()
    defined_variables = set()
    # This pattern finds variable names inside braces, e.g., {var_name}
    variable_usage_pattern = re.compile(r"\{(\w+)\}")

    for i, step in enumerate(sequence):
        # Find where variables are USED first
        text_to_check = []
        action_type = step.get('action_type')
        if action_type == 'Type':
            text_to_check.append(step.get('action_params', {}).get('text', ''))
        elif action_type == 'Modify Variable':
            # The value can be a variable
            text_to_check.append(step.get('action_params', {}).get('modify_variable_value', ''))

        if step.get('step_type') == 'conditional_branch':
            # The variable in the condition itself, and the value it's compared against
            text_to_check.append(step.get('condition', {}).get('variable', ''))
            text_to_check.append(step.get('condition', {}).get('value', ''))

        for text in text_to_check:
            # `findall` will extract the names of the variables from the text
            used_vars = variable_usage_pattern.findall(text)
            for var_name in used_vars:
                if var_name not in defined_variables:
                    result.add_warning(f"Step {i+1}: Variable '{{{var_name}}}' is used before it is defined in the sequence.")

        # NOW, find where variables are DEFINED for subsequent steps
        if action_type == 'Set Variable':
            var_name = step.get('action_params', {}).get('variable_name')
            if var_name: defined_variables.add(var_name)
        elif action_type == 'Modify Variable':
            var_name = step.get('action_params', {}).get('modify_variable_name')
            if var_name: defined_variables.add(var_name)
        elif action_type == 'OCR':
            var_name = step.get('action_params', {}).get('output_variable_name')
            if var_name: defined_variables.add(var_name)

    return result
