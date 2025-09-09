import logging
import os
import random
import time

import cv2
import pygetwindow as gw

from ..gui.dialogs import ActionPreview
from ..utils.automation import (click_and_drag, click_at, press_key_combination,
                                right_click_at, scroll_wheel, type_text)
from ..utils.image_analyzer import (extract_text_from_image, find_color,
                                    find_image)
from ..utils.screen_capture import capture_screen
from .script_validator import ScriptValidator


class ExecutionEngine:
    def __init__(self, app):
        self.app = app
        self.variable_manager = self.app.variable_manager
        self.validator = ScriptValidator()

    def validate_sequence(self, sequence):
        """
        Validates the entire sequence using the ScriptValidator.
        Raises a ValueError if any critical errors are found.
        """
        validation_result = self.validator.validate_sequence(sequence)
        if not validation_result.is_valid:
            # Format the errors for display in a messagebox or log
            error_message = "Sequence validation failed with critical errors:\n\n" + "\n".join(validation_result.errors)
            # We can also log warnings here if we want
            if validation_result.warnings:
                logging.warning("Validation warnings found:\n" + "\n".join(validation_result.warnings))
            raise ValueError(error_message)

        # Log warnings even if the sequence is valid enough to run
        if validation_result.warnings:
            logging.warning("Sequence has validation warnings. Execution will proceed, but check these issues:")
            for warning in validation_result.warnings:
                logging.warning(f"- {warning}")

    def load_template_image(self, path):
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        if not os.path.exists(path):
            logging.error(f"Template image not found: {path}")
            return None

        return cv2.imread(path, cv2.IMREAD_UNCHANGED)

    def run_scan_loop(self):
        if self.app.execution_depth > self.app.max_execution_depth:
            logging.error("Maximum execution depth reached. Stopping to prevent infinite loop.")
            self.app.toggle_bot()
            return

        self.app.execution_depth += 1
        try:
            if not self.app.running:
                return

            if not self.app.execution_stack:
                logging.info("Action sequence complete. Stopping bot.")
                self.app.toggle_bot()
                return

            current_sequence, current_index = self.app.execution_stack[-1]

            if current_index >= len(current_sequence):
                self.app.execution_stack.pop()
                self.app.scan_job = self.app.after(10, self.run_scan_loop) # Continue processing parent sequence
                return

            current_step = current_sequence[current_index]
            step_type = current_step.get('step_type', 'simple')
            step_number_str = f"Step {current_index + 1}" # For logging

            if self.app.dry_run_var.get():
                # Use the preview engine to check for issues even in dry run
                preview_result = self.app.preview_engine.preview_step(current_step, current_index + 1)
                if preview_result['potential_issues']:
                    logging.warning(f"[DRY RUN] {step_number_str}: Potential issues found: {', '.join(preview_result['potential_issues'])}")

            # For other actions, we pass the step and its context
            step_context = {'sequence': current_sequence, 'index': current_index, 'number_str': step_number_str}

            if step_type == 'simple':
                self._execute_simple_step(current_step, step_context)
            elif step_type == 'wait':
                self._execute_wait_step(current_step, step_context)
                return # The wait step handles its own continuation
            elif step_type == 'conditional_branch':
                logging.info(f"Evaluating condition for {step_number_str}...")
                # First, advance the parent sequence *before* pushing a new one.
                self.app.execution_stack[-1] = (current_sequence, current_index + 1)

                if self.variable_manager.evaluate_condition(current_step.get('condition')):
                    logging.info("Condition is TRUE. Executing IF branch.")
                    if_branch = current_step.get('if_branch', [])
                    if if_branch:
                        self.app.execution_stack.append((if_branch, 0))
                else:
                    logging.info("Condition is FALSE. Executing ELSE branch.")
                    else_branch = current_step.get('else_branch', [])
                    if else_branch:
                        self.app.execution_stack.append((else_branch, 0))

                # Continue to the next loop iteration immediately to process the new stack
                self.app.scan_job = self.app.after(10, self.run_scan_loop)
                return
            elif step_type == 'loop':
                self._execute_loop_step(current_step, step_context)
            elif step_type == 'conditional_loop':
                self._execute_conditional_loop_step(current_step, step_context)
            elif step_type == 'time_based_condition':
                self._execute_time_based_condition_step(current_step, step_context)
            else:
                logging.error(f"Error: Unknown step type '{step_type}' at {step_number_str}. Stopping bot.")
                self.app.toggle_bot()
        finally:
            self.app.execution_depth -= 1

    def _handle_post_action_wait(self, step):
        wait_params = step.get('wait_params', {})
        wait_type = wait_params.get('type', 'Fixed')
        wait_duration = 0

        if wait_type == 'Fixed':
            wait_duration = wait_params.get('fixed_time', 1.0)
        elif wait_type == 'Random':
            min_time = wait_params.get('min_time', 1.0)
            max_time = wait_params.get('max_time', 2.0)
            wait_duration = random.uniform(min_time, max_time)

        # The wait duration from config is in seconds. 'after' needs milliseconds.
        wait_ms = int(wait_duration * 1000)

        if wait_ms > 0:
            logging.info(f"Waiting for {wait_duration:.2f} seconds...")
            self.app.scan_job = self.app.after(wait_ms, self.run_scan_loop)
        else:
            # If no wait, or wait is 0, proceed to the next step immediately,
            # but use after(10) to yield to the main GUI loop and prevent freezing.
            self.app.scan_job = self.app.after(10, self.run_scan_loop)

    def _execute_loop_step(self, step, context):
        """
        Handles the execution of a 'loop' step by managing the execution stack
        instead of using a blocking internal loop.
        """
        step_id = id(step)
        try:
            loop_mode = step.get('loop_mode', 'repeat')

            # --- REPEAT X TIMES mode ---
            if loop_mode == 'repeat':
                repeat_count = step.get('loop_repeat_count', 1)
                # Get current iteration count, default to 0 if not present
                current_iteration = self.app.loop_counters.get(step_id, 0)

                if current_iteration < repeat_count:
                    logging.info(f"{context['number_str']} (Loop): Running iteration {current_iteration + 1}/{repeat_count}.")
                    # Increment the counter for the next time we see this step
                    self.app.loop_counters[step_id] = current_iteration + 1

                    # 1. Push the current loop step back onto the stack. When the sub-actions
                    #    are done, the bot will re-evaluate this same step.
                    self.app.execution_stack.append((context['sequence'], context['index']))
                    # 2. Push the sub-actions onto the stack to be executed now.
                    self.app.execution_stack.append((step.get('loop_actions', []), 0))
                else:
                    # Loop is finished
                    logging.info(f"{context['number_str']} (Loop): Finished {repeat_count} iterations.")
                    # Clean up the counter
                    if step_id in self.app.loop_counters:
                        del self.app.loop_counters[step_id]
                    # Advance the parent sequence to the *next* step
                    self.app.execution_stack[-1] = (context['sequence'], context['index'] + 1)

                # Immediately schedule the next scan to process the updated stack
                self.app.scan_job = self.app.after(10, self.run_scan_loop)
                return

            # --- UNTIL CONDITION MET mode ---
            elif loop_mode == 'until':
                max_retries = step.get('max_retries', 10)
                current_retries = self.app.loop_counters.get(step_id, 0)

                if current_retries >= max_retries:
                    logging.error(f"Loop failed: Condition not met after {max_retries} retries. Stopping bot.")
                    if step_id in self.app.loop_counters:
                        del self.app.loop_counters[step_id]
                    self.app.toggle_bot()
                    return

                # Get window and region details first
                try:
                    target_window_title = step.get("window_title")
                    target_windows = gw.getWindowsWithTitle(target_window_title)
                    if not target_windows:
                        logging.warning(f"{context['number_str']} (Loop): Window '{target_window_title}' not found. Re-scanning...")
                        self.app.scan_job = self.app.after(2000, self.run_scan_loop)
                        return
                    target_window = target_windows[0]
                    scan_region = {'top': target_window.top, 'left': target_window.left, 'width': target_window.width, 'height': target_window.height}
                    if step.get('search_region'):
                        custom_region = step['search_region']
                        scan_region = {'top': target_window.top + custom_region['y'], 'left': target_window.left + custom_region['x'], 'width': custom_region['width'], 'height': custom_region['height']}
                except Exception as e:
                    logging.error(f"Error getting window details: {e}. Stopping bot.")
                    self.app.toggle_bot()
                    return

                # 1. Check for the condition
                logging.info(f"Executing {context['number_str']} (Loop): Checking for condition '{step.get('loop_condition_target_name')}'. Attempt {current_retries + 1}/{max_retries}.")
                haystack_img = capture_screen(scan_region)
                condition_found = False
                try:
                    targets = step['loop_condition_target']
                    if isinstance(targets, str): targets = [targets]
                    needle_imgs = [self.load_template_image(p) for p in targets]
                    threshold = self.app.settings_manager.get_setting('image_similarity_threshold')
                    if find_image(haystack_img, [img for img in needle_imgs if img is not None], threshold=threshold):
                        condition_found = True
                except Exception as e:
                    logging.error(f"  - Error loading condition image(s): {e}. Stopping bot.")
                    self.app.toggle_bot()
                    return

                # 2. Decide what to do based on condition
                if condition_found:
                    logging.info("  - Condition met. Exiting loop.")
                    if step_id in self.app.loop_counters:
                        del self.app.loop_counters[step_id]
                    self.app.execution_stack[-1] = (context['sequence'], context['index'] + 1)
                else:
                    logging.info("  - Condition not met. Performing loop actions.")
                    self.app.loop_counters[step_id] = current_retries + 1
                    # Push the loop step and then the sub-actions, just like in 'repeat' mode
                    self.app.execution_stack.append((context['sequence'], context['index']))
                    self.app.execution_stack.append((step.get('loop_actions', []), 0))

                self.app.scan_job = self.app.after(10, self.run_scan_loop)
        except Exception:
            # Clean up counter even on exception
            if step_id in self.app.loop_counters:
                del self.app.loop_counters[step_id]
            raise

    def _execute_single_action(self, action_step, scan_region):
        """
        Executes a single, simple action. Returns True on success, False on failure.
        Handles both conditional (Image/Color) and unconditional actions.
        """
        action_type = action_step.get('action_type')
        detection_mode = action_step.get('detection_mode')

        # --- Handle special action types that are self-contained ---
        if action_type == 'OCR':
            return self._perform_ocr_action(action_step, scan_region)

        target_found = False
        action_center_x, action_center_y = None, None
        preview_w, preview_h = None, None

        # --- STEP 1: Find the target if required by detection_mode ---
        if detection_mode in ["Image", "Color"]:
            logging.info(f"  - Find {detection_mode}: '{action_step.get('detection_target_name', 'N/A')}'...")
            haystack_img = capture_screen(scan_region)

            if detection_mode == "Color":
                locations = find_color(haystack_img, action_step['detection_target'])
                if locations:
                    target_found = True
                    action_center_x, action_center_y = locations[0]
            elif detection_mode == "Image":
                try:
                    targets = action_step['detection_target']
                    if isinstance(targets, str): targets = [targets]

                    needle_imgs = [self.load_template_image(p) for p in targets if p]
                    if not needle_imgs:
                        logging.error(f"    - Error: No valid template images could be loaded for step.")
                        return False

                    threshold = self.app.settings_manager.get_setting('image_similarity_threshold')
                    match_data = find_image(haystack_img, needle_imgs, threshold=threshold)
                    if match_data:
                        target_found = True
                        top_left_x, top_left_y, width, height = match_data
                        action_center_x = top_left_x + width // 2
                        action_center_y = top_left_y + height // 2
                        preview_w, preview_h = width, height
                except Exception as e:
                    logging.error(f"    - Error during image search: {e}")
                    return False

            if target_found:
                logging.info(f"    - Target found.")
            else:
                logging.warning("    - Target not found.")
        else:
            # No detection needed, so the action is unconditional.
            target_found = True
            logging.info(f"  - Unconditional action: {action_type}")

        # --- STEP 2: Execute action if target was found (or not needed) ---
        if target_found:
            abs_x, abs_y = None, None
            if action_center_x is not None:
                abs_x = scan_region['left'] + action_center_x
                abs_y = scan_region['top'] + action_center_y

            self._perform_action(action_type, action_step, abs_x, abs_y, preview_w, preview_h)
            self._handle_post_action_wait(action_step)
            return True
        else:
            return False

    def _perform_ocr_action(self, action_step, scan_region):
        action_params = action_step.get('action_params', {})
        output_var = action_params.get('output_variable_name')

        # OCR uses its own region defined in params, which is absolute screen coords.
        final_region = action_params.get('ocr_region')

        if not final_region or not output_var:
            logging.error(f"Error in step: OCR step is not configured correctly.")
            return False

        logging.info(f"Performing OCR on region {final_region} and saving to '{output_var}'...")
        if self.app.dry_run_var.get():
            logging.info(f"    - [DRY RUN] Would perform OCR.")
        else:
            screenshot = capture_screen(final_region)
            extracted_text = extract_text_from_image(screenshot)
            if extracted_text == "TESSERACT_NOT_FOUND":
                logging.critical("FATAL: Tesseract OCR engine not found. Please install it. Stopping bot.")
                self.app.toggle_bot()
                return False
            logging.info(f"OCR Result: '{extracted_text}'. Stored in variable '{output_var}'.")
            self.variable_manager.variables[output_var] = extracted_text

        self._handle_post_action_wait(action_step)
        return True

    def _perform_action(self, action_type, action_step, abs_x, abs_y, width=None, height=None):
        """Helper to execute the final action after detection is successful."""
        action_params = action_step.get('action_params', {})

        if self.app.dry_run_var.get():
            logging.info(f"    - [DRY RUN] Would perform action: {action_type} at ({abs_x}, {abs_y})")
            return

        # --- Variable Actions ---
        if action_type == 'Set Variable':
            var_name = action_params.get('variable_name')
            var_value = self.variable_manager.substitute(action_params.get('variable_value'))
            if not var_name:
                logging.error(f"Error in step: 'Set Variable' action has no variable name.")
                return
            logging.info(f"    - Performing action: Set variable '{var_name}' to '{var_value}'")
            self.variable_manager.variables[var_name] = var_value

        elif action_type == 'Modify Variable':
            var_name = action_params.get('modify_variable_name')
            operation = action_params.get('modify_variable_operation')
            value_str = self.variable_manager.substitute(action_params.get('modify_variable_value', '0'))
            if not var_name:
                logging.error(f"Error in step: 'Modify Variable' action has no variable name.")
                return

            current_value_str = self.variable_manager.variables.get(var_name, '0')
            try:
                current_value = float(current_value_str)
                value_to_op = float(value_str)
                new_value = 0
                if operation == 'add': new_value = current_value + value_to_op
                elif operation == 'subtract': new_value = current_value - value_to_op
                elif operation == 'set': new_value = value_to_op

                if new_value == int(new_value): self.variable_manager.variables[var_name] = str(int(new_value))
                else: self.variable_manager.variables[var_name] = str(new_value)
                logging.info(f"    - Performing action: Variable '{var_name}' {operation}ed by {value_to_op}. New value: {self.variable_manager.variables[var_name]}")
            except ValueError:
                logging.error(f"Error in step: Cannot perform arithmetic on non-numeric variable '{var_name}' (value: '{current_value_str}') or input '{value_str}'.")

        # --- UI Interaction Actions ---
        elif action_type in ["Click", "Right-click", "Click with Offset"]:
            if abs_x is None or abs_y is None:
                logging.error(f"Error in step: Action '{action_type}' requires a screen location, but none was found.")
                return
            logging.info(f"    - Previewing action at ({abs_x}, {abs_y})...")
            preview = ActionPreview(self.app, abs_x, abs_y, width=width, height=height, duration=500)
            self.app.wait_window(preview)

            if action_type == "Click":
                logging.info(f"    - Performing action: Click at ({abs_x}, {abs_y})")
                click_at(abs_x, abs_y)
            elif action_type == "Right-click":
                logging.info(f"    - Performing action: Right-click at ({abs_x}, {abs_y})")
                right_click_at(abs_x, abs_y)
            elif action_type == "Click with Offset":
                offset_x = action_params.get('click_offset_x', 0)
                offset_y = action_params.get('click_offset_y', 0)
                click_x = abs_x + offset_x
                click_y = abs_y + offset_y
                logging.info(f"    - Performing action: Click with offset at ({click_x}, {click_y})")
                click_at(click_x, click_y)

        elif action_type == "Type":
            text_to_type = action_params.get('text', '')
            substituted_text = self.variable_manager.substitute(text_to_type)
            logging.info(f"    - Performing action: Type '{substituted_text}'")
            type_text(substituted_text)

        elif action_type == "Key Combo":
            key_combo = action_params.get('key_combo', '')
            substituted_combo = self.variable_manager.substitute(key_combo)
            logging.info(f"    - Performing action: Press keys '{substituted_combo}'")
            press_key_combination(substituted_combo)

        elif action_type == "Scroll":
            direction = action_params.get('scroll_direction', 'Down')
            amount = action_params.get('scroll_amount', 5)
            logging.info(f"    - Performing action: Scroll {direction} by {amount}")
            scroll_wheel(direction.lower(), amount)

    def _execute_simple_step(self, step, context):
        target_window_title = step.get("window_title")
        if not target_window_title:
            logging.error(f"Error in {context['number_str']}: No target window specified. Stopping bot.")
            self.app.toggle_bot()
            return

        try:
            target_windows = gw.getWindowsWithTitle(target_window_title)
            if not target_windows:
                logging.warning(f"{context['number_str']}: Window '{target_window_title}' not found. Re-scanning...")
                self.app.scan_job = self.app.after(2000, self.run_scan_loop)
                return
            target_window = target_windows[0]
            scan_region = {'top': target_window.top, 'left': target_window.left, 'width': target_window.width, 'height': target_window.height}

            if step.get('search_region'):
                custom_region = step['search_region']
                scan_region = {
                    'top': target_window.top + custom_region['y'],
                    'left': target_window.left + custom_region['x'],
                    'width': custom_region['width'],
                    'height': custom_region['height']
                }
        except Exception as e:
            logging.error(f"Error getting window details: {e}. Stopping bot.")
            self.app.toggle_bot()
            return

        if self._execute_single_action(step, scan_region):
            # On success, advance the index and reset retry count for this step
            sequence, index = self.app.execution_stack[-1]
            self.app.execution_stack[-1] = (sequence, index + 1)
            self.app.step_retry_counts[id(step)] = 0
            logging.info(f"SUCCESS: {context['number_str']} completed.")
        else:
            # On failure, handle according to the policy
            on_failure = step.get('on_failure', {'policy': 'Stop'})
            policy = on_failure.get('policy', 'Stop')
            logging.warning(f"FAILURE: {context['number_str']} failed. Policy: {policy}.")

            if policy == 'Stop':
                logging.error("Stopping bot due to step failure.")
                self.app.toggle_bot()
                return

            elif policy == 'Skip':
                logging.info("Skipping to next step.")
                sequence, index = self.app.execution_stack[-1]
                self.app.execution_stack[-1] = (sequence, index + 1)
                self.app.scan_job = self.app.after(10, self.run_scan_loop)

            elif policy == 'Retry':
                max_retries = on_failure.get('retries', 3)
                step_id = id(step)
                current_retries = self.app.step_retry_counts.get(step_id, 0)

                if current_retries < max_retries:
                    self.app.step_retry_counts[step_id] = current_retries + 1
                    logging.info(f"Retrying step... (Attempt {current_retries + 1}/{max_retries})")
                    self.app.scan_job = self.app.after(2000, self.run_scan_loop)
                else:
                    logging.error(f"Step failed after {max_retries} retries. Stopping bot.")
                    self.app.toggle_bot()

    def _execute_conditional_loop_step(self, step, context):
        max_retries = step.get('max_retries', 5)
        step_id = id(step)
        current_retries = self.app.conditional_loop_retry_counts.get(step_id, 0)

        if current_retries >= max_retries:
            logging.error(f"Loop failed after {max_retries} retries for {context['number_str']}. Stopping bot.")
            self.app.toggle_bot()
            return

        # The window title for a conditional step is stored in the step itself
        target_window_title = step.get("window_title")
        if not target_window_title:
            logging.error(f"Error in {context['number_str']} (Conditional): No target window specified. Stopping bot.")
            self.app.toggle_bot()
            return

        try:
            target_windows = gw.getWindowsWithTitle(target_window_title)
            if not target_windows:
                logging.warning(f"{context['number_str']} (Conditional): Window '{target_window_title}' not found. Retrying in 2s...")
                self.app.scan_job = self.app.after(2000, self.run_scan_loop)
                return
            target_window = target_windows[0]
            # Default scan region is the entire window
            scan_region = {'top': target_window.top, 'left': target_window.left, 'width': target_window.width, 'height': target_window.height}

            # If a specific search region is defined for the step, use it instead
            if step.get('search_region'):
                custom_region = step['search_region']
                # The custom region coords are relative to the window, so we add the window's top-left corner
                scan_region = {
                    'top': target_window.top + custom_region['y'],
                    'left': target_window.left + custom_region['x'],
                    'width': custom_region['width'],
                    'height': custom_region['height']
                }
                logging.info(f"Using custom scan region for conditional loop: {scan_region}")

        except Exception as e:
            logging.error(f"Error getting window details: {e}. Stopping bot.")
            self.app.toggle_bot()
            return

        # 1. Look for the primary target
        primary_target = step.get('primary_target', {})
        logging.info(f"{context['number_str']} (Attempt {current_retries+1}/{max_retries}): Finding '{primary_target.get('detection_target_name')}'...")
        haystack_img = capture_screen(scan_region)

        primary_pos = None
        try:
            targets = primary_target['detection_target']
            if isinstance(targets, str): targets = [targets]
            needle_imgs = [self.load_template_image(p) for p in targets]
            threshold = self.app.settings_manager.get_setting('image_similarity_threshold')
            primary_pos = find_image(haystack_img, [img for img in needle_imgs if img is not None], threshold=threshold)
        except Exception as e:
            logging.error(f"Loop Error: Could not load primary target image(s). {e}")
            self.app.toggle_bot()
            return

        if primary_pos:
            # 2. If found, success! Move to next step.
            logging.info("Primary target found! Proceeding to next step.")
            self.app.conditional_loop_retry_counts[step_id] = 0 # Reset counter for this specific step
            sequence, index = self.app.execution_stack[-1]
            self.app.execution_stack[-1] = (sequence, index + 1)
            self._handle_post_action_wait(step)
        else:
            # 3. If not found, perform fallback action.
            logging.info("Primary target not found. Performing fallback action.")
            self.app.conditional_loop_retry_counts[step_id] = current_retries + 1 # Increment counter

            fallback_action = step.get('on_fail', {})
            if not fallback_action:
                logging.error("No fallback action defined. Stopping bot.")
                self.app.toggle_bot()
                return

            if self._perform_fallback_action(fallback_action, scan_region):
                logging.info("Fallback action successful. Retrying primary target in 2 seconds...")
                self.app.scan_job = self.app.after(2000, self.run_scan_loop) # Re-run the same conditional step
            else:
                logging.error("Fallback action failed. Stopping bot.")
                self.app.toggle_bot()

    def _perform_fallback_action(self, action_details, scan_region):
        action_type = action_details.get('action_type')


        if action_type == "Do Nothing":
            logging.info("Fallback action: Doing nothing.")
            return True
        elif action_type == "Click and Drag":
            if self.app.dry_run_var.get():
                logging.info("Fallback action: [DRY RUN] Would perform 'Click and Drag'.")
            else:
                logging.info("Fallback action: Performing 'Click and Drag'.")
                params = action_details.get('action_params', {})
                offset_x = params.get('drag_offset_x', 0)
                offset_y = params.get('drag_offset_y', 0)

                start_x = scan_region['left'] + scan_region['width'] // 2
                start_y = scan_region['top'] + scan_region['height'] // 2
                end_x = start_x + offset_x
                end_y = start_y + offset_y

                logging.info(f"Dragging from window center ({start_x}, {start_y}) to ({end_x}, {end_y})")
                click_and_drag(start_x, start_y, end_x, end_y)
            return True

        elif action_type == "Scroll":
            if self.app.dry_run_var.get():
                logging.info("Fallback action: [DRY RUN] Would scroll.")
            else:
                params = action_details.get('action_params', {})
                direction = params.get('scroll_direction', 'Down')
                amount = params.get('scroll_amount', 5)
                logging.info(f"Fallback action: Scrolling {direction} by {amount}")
                scroll_wheel(direction.lower(), amount)
            return True
        elif action_type == "Click" or action_type == "Click with Offset":
            logging.info(f"Fallback: Finding '{action_details.get('detection_target_name')}' for action '{action_type}'.")
            haystack_img = capture_screen(scan_region)
            target_pos = None
            try:
                targets = action_details['detection_target']
                if isinstance(targets, str): targets = [targets]
                needle_imgs = [self.load_template_image(p) for p in targets]
                threshold = self.app.settings_manager.get_setting('image_similarity_threshold')
                target_pos = find_image(haystack_img, [img for img in needle_imgs if img is not None], threshold=threshold)
            except Exception as e:
                logging.error(f"Fallback Error: Could not load image(s). {e}")
                return False

            if target_pos:
                abs_x = scan_region['left'] + target_pos[0]
                abs_y = scan_region['top'] + target_pos[1]

                if self.app.dry_run_var.get():
                    logging.info(f"Fallback action: [DRY RUN] Would perform '{action_type}' at ({abs_x}, {abs_y})")
                else:
                    if action_type == "Click":
                        logging.info(f"Fallback action: Clicking at ({abs_x}, {abs_y})")
                        click_at(abs_x, abs_y)
                    else: # Click with Offset
                        params = action_details.get('action_params', {})
                        offset_x = params.get('click_offset_x', 0)
                        offset_y = params.get('click_offset_y', 0)
                        click_x = abs_x + offset_x
                        click_y = abs_y + offset_y
                        logging.info(f"Fallback action: Click with offset at ({click_x}, {click_y})")
                        click_at(click_x, click_y)
                return True
            else:
                logging.warning("Fallback target not found.")
                return False

        logging.error(f"Unknown fallback action type: {action_type}")
        return False

    def _execute_wait_step(self, step, context):
        """Handles the 'wait' step type."""
        try:
            duration = float(step.get('duration', 1.0))
        except (ValueError, TypeError):
            logging.error(f"Invalid duration for wait step: {step.get('duration')}. Stopping bot.")
            self.app.toggle_bot()
            return

        logging.info(f"{context['number_str']}: Waiting for {duration:.2f} seconds...")

        # Advance the stack to the next step
        sequence, index = self.app.execution_stack[-1]
        self.app.execution_stack[-1] = (sequence, index + 1)

        # Schedule the next scan loop after the duration
        wait_ms = int(duration * 1000)
        self.app.scan_job = self.app.after(wait_ms, self.run_scan_loop)

    def _execute_time_based_condition_step(self, step, context):
        time_cond = step.get('time_condition', {})
        hour = time_cond.get('hour')
        minute = time_cond.get('minute')

        if hour is None or minute is None:
            logging.error(f"Error in {context['number_str']}: Invalid time condition. Stopping bot.")
            self.app.toggle_bot()
            return

        now = time.localtime()
        time_key = (hour, minute)

        if now.tm_hour == hour and now.tm_min == minute:
            if time_key in self.app.time_condition_executed:
                logging.info(f"Time condition {hour:02d}:{minute:02d} already executed this cycle. Advancing.")
                # Condition was met and executed, so we just advance the parent sequence
                self.app.execution_stack[-1] = (context['sequence'], context['index'] + 1)
                self.app.scan_job = self.app.after(10, self.run_scan_loop)
                return

            logging.info(f"Time condition met: {hour:02d}:{minute:02d}. Executing actions.")
            self.app.time_condition_executed.add(time_key) # Mark as executed

            # Advance the parent sequence *before* pushing a new one.
            self.app.execution_stack[-1] = (context['sequence'], context['index'] + 1)
            actions = step.get('actions', [])
            if actions:
                self.app.execution_stack.append((actions, 0))
            # After executing, immediately continue to the next step in the main loop
            self.app.scan_job = self.app.after(10, self.run_scan_loop)
        else:
            logging.info(f"Waiting for time condition: {hour:02d}:{minute:02d}. Current time: {now.tm_hour:02d}:{now.tm_min:02d}. Re-checking in 5 seconds.")
            self.app.scan_job = self.app.after(5000, self.run_scan_loop)
