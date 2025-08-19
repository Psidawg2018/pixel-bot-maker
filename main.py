import tkinter as tk
from tkinter import scrolledtext, colorchooser, filedialog
import time
import json
import random

# Import our custom modules
import numpy as np
import mss
from pynput import keyboard
import threading
import pygetwindow as gw
import os
import cv2
from PIL import Image, ImageTk
from screen_capture import capture_screen
from image_analyzer import find_color, find_image
from automation import click_at, type_text, click_and_drag

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pixel Bot")
        self.geometry("400x750")

        # --- Color Theme ---
        self.bg_color = "#2C3E50"
        self.widget_bg_color = "#34495E"
        self.text_color = "#ECF0F1"
        self.button_color = "#3498DB"
        self.button_text_color = "#ECF0F1"

        self.configure(bg=self.bg_color)

        # --- App State ---
        self.running = False
        self.scan_job = None
        self.hotkey_listener = None
        self.action_sequence = []
        self.current_step_index = 0
        self.current_retry_count = 0
        self.hide_window_var = tk.BooleanVar(value=True)
        self.target_window_title = tk.StringVar()
        self.target_window_title.set("") # Set to empty string initially

        # Ensure templates directory exists
        if not os.path.exists("templates"):
            os.makedirs("templates")

        # --- WIDGET CREATION ---
        top_frame = tk.Frame(self, bg=self.bg_color)
        top_frame.pack(pady=10, padx=10, fill="x", anchor="n")

        self.log_area = scrolledtext.ScrolledText(self, width=45, height=8, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT, insertbackground=self.text_color)

        # --- Sequence Editor UI ---
        sequence_frame = tk.LabelFrame(top_frame, text="Action Sequence", bg=self.bg_color, fg=self.text_color, padx=5, pady=5)
        sequence_frame.pack(fill="x", pady=10)
        list_container = tk.Frame(sequence_frame, bg=self.bg_color)
        list_container.pack(fill="x")
        self.sequence_listbox = tk.Listbox(list_container, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT, height=5)
        self.sequence_listbox.pack(side="left", fill="x", expand=True)
        self.sequence_listbox.bind("<<ListboxSelect>>", self.on_sequence_select)
        seq_button_frame = tk.Frame(list_container, bg=self.bg_color)
        seq_button_frame.pack(side="left", padx=(5,0))
        self.add_step_button = tk.Button(seq_button_frame, text="Add", command=self.add_step, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT, state=tk.DISABLED)
        self.add_step_button.pack(pady=2, fill="x")
        self.edit_step_button = tk.Button(seq_button_frame, text="Edit", command=self.edit_step, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT, state=tk.DISABLED)
        self.edit_step_button.pack(pady=2, fill="x")
        self.remove_step_button = tk.Button(seq_button_frame, text="Remove", command=self.remove_step, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT, state=tk.DISABLED)
        self.remove_step_button.pack(pady=2, fill="x")

        # --- Save/Load Buttons ---
        file_button_frame = tk.Frame(sequence_frame, bg=self.bg_color)
        file_button_frame.pack(fill="x", pady=(5,0))
        tk.Button(file_button_frame, text="Load Sequence", command=self.load_sequence, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT).pack(side="left", padx=5)
        tk.Button(file_button_frame, text="Save Sequence", command=self.save_sequence, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT).pack(side="left", padx=5)

        # --- Final Controls ---
        controls_frame = tk.LabelFrame(self, text="Global Target", bg=self.bg_color, fg=self.text_color, padx=5, pady=5)
        controls_frame.pack(pady=10, padx=10, fill="x")

        self.target_window_label = tk.Label(controls_frame, textvariable=self.target_window_title, bg=self.widget_bg_color, fg=self.text_color, wraplength=380, justify="left")
        self.target_window_label.pack(pady=5, fill="x")
        tk.Button(controls_frame, text="Change Target Window", command=self.prompt_for_window_selection, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT).pack(pady=(0,5))

        bot_controls_frame = tk.Frame(self, bg=self.bg_color)
        bot_controls_frame.pack(pady=10, padx=10, fill="x")

        self.hide_window_check = tk.Checkbutton(bot_controls_frame, text="Hide window when bot is running", variable=self.hide_window_var, bg=self.bg_color, fg=self.text_color, selectcolor=self.widget_bg_color, activebackground=self.bg_color, activeforeground=self.text_color)
        self.hide_window_check.pack()

        self.start_button = tk.Button(bot_controls_frame, text="Start Bot", command=self.toggle_bot, bg=self.button_color, fg=self.button_text_color, activebackground="#2980B9", activeforeground=self.text_color, relief=tk.FLAT, padx=10, pady=5)
        self.start_button.pack(pady=10)
        self.log_area.pack(pady=10, padx=10, fill="both", expand=True)

        self.log("Welcome! Please select a target window to begin.")
        self.after(200, lambda: self.prompt_for_window_selection(is_splash=True))

    def prompt_for_window_selection(self, is_splash=False):
        self.log("Prompting for target window selection...")
        WindowSelector(self, is_splash=is_splash)

    def on_window_selected(self, title):
        self.target_window_title.set(title)
        if self.add_step_button['state'] == tk.DISABLED:
            self.add_step_button.config(state=tk.NORMAL)
        self.log(f"Global target window set to: {title}")

    def on_sequence_select(self, event):
        if self.sequence_listbox.curselection():
            self.edit_step_button.config(state=tk.NORMAL)
            self.remove_step_button.config(state=tk.NORMAL)
        else:
            self.edit_step_button.config(state=tk.DISABLED)
            self.remove_step_button.config(state=tk.DISABLED)

    def add_step(self):
        StepEditor(self)

    def edit_step(self):
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices:
            return
        index = selected_indices[0]
        step_data = self.action_sequence[index]
        StepEditor(self, step_data=step_data, index=index)

    def remove_step(self):
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices:
            return
        index = selected_indices[0]
        self.action_sequence.pop(index)
        self.update_sequence_listbox()
        self.log(f"Removed step {index+1}.")

    def save_sequence(self):
        if not self.action_sequence:
            self.log("Action sequence is empty. Nothing to save.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Save Sequence As...",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
            defaultextension=".json"
        )

        if not filepath:
            self.log("Save operation cancelled.")
            return

        try:
            with open(filepath, 'w') as f:
                json.dump(self.action_sequence, f, indent=4)
            self.log(f"Sequence saved to {filepath}")
        except Exception as e:
            self.log(f"Error saving sequence: {e}")

    def load_sequence(self):
        filepath = filedialog.askopenfilename(
            title="Load Sequence From...",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
        )

        if not filepath:
            self.log("Load operation cancelled.")
            return

        try:
            with open(filepath, 'r') as f:
                loaded_sequence = json.load(f)

            # Basic validation
            if not isinstance(loaded_sequence, list):
                raise ValueError("Loaded file is not a valid sequence list.")

            self.action_sequence = loaded_sequence
            self.update_sequence_listbox()
            self.log(f"Sequence loaded from {filepath}")
        except json.JSONDecodeError:
            self.log("Error: The selected file is not a valid JSON file.")
        except Exception as e:
            self.log(f"Error loading sequence: {e}")

    def on_step_saved(self, step_data, index=None):
        if index is not None:
            self.action_sequence[index] = step_data
        else:
            self.action_sequence.append(step_data)
        self.update_sequence_listbox()

    def update_sequence_listbox(self):
        self.sequence_listbox.delete(0, tk.END)
        for i, step in enumerate(self.action_sequence):
            step_type = step.get('step_type', 'simple')
            text = f"{i+1}: "

            if step_type == 'simple':
                mode = step.get('detection_mode', '?')
                action = step.get('action_type', '?')
                target = step.get('detection_target_name', 'Unknown')
                text += f"Find {mode} '{target}', then {action}"
            elif step_type == 'conditional_loop':
                primary_target_name = step.get('primary_target', {}).get('detection_target_name', 'N/A')
                fallback_action = step.get('on_fail', {}).get('action_type', 'N/A')
                retries = step.get('max_retries', 'N/A')
                text += f"LOOP ({retries}x): Find '{primary_target_name}', on fail: {fallback_action}"
            else:
                text += "Unknown Step Type"

            self.sequence_listbox.insert(tk.END, text)
        self.on_sequence_select(None)

    def toggle_bot(self):
        if self.running:
            self.running = False
            self.start_button.config(text="Start Bot")
            if self.scan_job:
                self.after_cancel(self.scan_job)
            self.scan_job = None
            if self.hotkey_listener:
                self.hotkey_listener.stop()
            self.hotkey_listener = None
            self.log("Bot stopped by user.")
            if self.hide_window_var.get():
                self.deiconify()
        else:
            if not self.action_sequence:
                self.log("Cannot start: Action sequence is empty.")
                return
            self.current_step_index = 0
            self.current_retry_count = 0
            self.running = True
            self.start_button.config(text="Stop Bot")
            self.start_hotkey_listener()
            if self.hide_window_var.get():
                self.withdraw()
            self.run_scan_loop()

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
            self.log(f"Waiting for {wait_duration:.2f} seconds...")
            self.scan_job = self.after(wait_ms, self.run_scan_loop)
        else:
            # If no wait, or wait is 0, proceed to the next step immediately.
            self.run_scan_loop()

    def run_scan_loop(self):
        if not self.running:
            return

        if self.current_step_index >= len(self.action_sequence):
            self.log("Action sequence complete. Stopping bot.")
            self.toggle_bot()
            return

        current_step = self.action_sequence[self.current_step_index]
        step_type = current_step.get('step_type', 'simple')

        if step_type == 'simple':
            self._execute_simple_step(current_step)
        elif step_type == 'conditional_loop':
            self._execute_conditional_loop_step(current_step)
        else:
            self.log(f"Error: Unknown step type '{step_type}' at step {self.current_step_index + 1}. Stopping bot.")
            self.toggle_bot()

    def _execute_simple_step(self, step):
        target_window_title = step.get("window_title")
        if not target_window_title:
            self.log(f"Error in Step {self.current_step_index+1}: No target window specified. Stopping bot.")
            self.toggle_bot()
            return

        try:
            target_windows = gw.getWindowsWithTitle(target_window_title)
            if not target_windows:
                self.log(f"Step {self.current_step_index+1}: Window '{target_window_title}' not found. Re-scanning...")
                self.scan_job = self.after(2000, self.run_scan_loop)
                return
            target_window = target_windows[0]
            scan_region = {'top': target_window.top, 'left': target_window.left, 'width': target_window.width, 'height': target_window.height}
        except Exception as e:
            self.log(f"Error getting window details: {e}. Stopping bot.")
            self.toggle_bot()
            return

        self.log(f"Executing Step {self.current_step_index+1}: Find {step['detection_mode']} '{step.get('detection_target_name', 'N/A')}'...")
        haystack_img = capture_screen(scan_region)

        target_pos = None
        if step['detection_mode'] == "Color":
            locations = find_color(haystack_img, step['detection_target'])
            if locations:
                target_pos = locations[0]
        elif step['detection_mode'] == "Image":
            try:
                needle_img = cv2.imread(step['detection_target'], cv2.IMREAD_UNCHANGED)
                target_pos = find_image(haystack_img, needle_img)
            except Exception as e:
                self.log(f"Step {self.current_step_index+1} Error: Could not load template. {e}")
                self.toggle_bot()
                return

        if target_pos:
            self.log(f"Step {self.current_step_index+1}: Target found.")
            abs_x = scan_region['left'] + target_pos[0]
            abs_y = scan_region['top'] + target_pos[1]

            action_type = step['action_type']
            action_params = step.get('action_params', {})

            if action_type == "Click":
                self.log(f"Performing action: Click at ({abs_x}, {abs_y})")
                click_at(abs_x, abs_y)
            elif action_type == "Click with Offset":
                offset_x = action_params.get('click_offset_x', 0)
                offset_y = action_params.get('click_offset_y', 0)
                click_x = abs_x + offset_x
                click_y = abs_y + offset_y
                self.log(f"Performing action: Click with offset at ({click_x}, {click_y})")
                click_at(click_x, click_y)
            elif action_type == "Type":
                text = action_params.get('text', '')
                self.log(f"Performing action: Type '{text}'")
                type_text(text)

            self.current_step_index += 1
            self.current_retry_count = 0 # Reset for next step
            self.log("Action complete.")
            self._handle_post_action_wait(step)
        else:
            self.log("Target not found. Re-scanning same step in 2 seconds...")
            self.scan_job = self.after(2000, self.run_scan_loop)

    def _execute_conditional_loop_step(self, step):
        max_retries = step.get('max_retries', 5)
        if self.current_retry_count >= max_retries:
            self.log(f"Loop failed after {max_retries} retries for step {self.current_step_index + 1}. Stopping bot.")
            self.toggle_bot()
            return

        # The window title for a conditional step is stored in the step itself
        target_window_title = step.get("window_title")
        if not target_window_title:
            self.log(f"Error in Step {self.current_step_index+1}: No target window specified for conditional loop. Stopping bot.")
            self.toggle_bot()
            return

        try:
            target_windows = gw.getWindowsWithTitle(target_window_title)
            if not target_windows:
                self.log(f"Step {self.current_step_index+1}: Window '{target_window_title}' not found. Retrying in 2s...")
                self.scan_job = self.after(2000, self.run_scan_loop)
                return
            target_window = target_windows[0]
            scan_region = {'top': target_window.top, 'left': target_window.left, 'width': target_window.width, 'height': target_window.height}
        except Exception as e:
            self.log(f"Error getting window details: {e}. Stopping bot.")
            self.toggle_bot()
            return

        # 1. Look for the primary target
        primary_target = step.get('primary_target', {})
        self.log(f"Loop Step {self.current_step_index+1} (Attempt {self.current_retry_count+1}/{max_retries}): Finding '{primary_target.get('detection_target_name')}'...")
        haystack_img = capture_screen(scan_region)

        primary_pos = None
        try:
            needle_img = cv2.imread(primary_target['detection_target'], cv2.IMREAD_UNCHANGED)
            primary_pos = find_image(haystack_img, needle_img)
        except Exception as e:
            self.log(f"Loop Error: Could not load primary target image. {e}")
            self.toggle_bot()
            return

        if primary_pos:
            # 2. If found, success! Move to next step.
            self.log("Primary target found! Proceeding to next step.")
            self.current_retry_count = 0
            self.current_step_index += 1
            self._handle_post_action_wait(step)
        else:
            # 3. If not found, perform fallback action.
            self.log("Primary target not found. Performing fallback action.")
            self.current_retry_count += 1

            fallback_action = step.get('on_fail', {})
            if not fallback_action:
                self.log("No fallback action defined. Stopping bot.")
                self.toggle_bot()
                return

            if self._perform_fallback_action(fallback_action, scan_region):
                self.log("Fallback action successful. Retrying primary target in 2 seconds...")
                self.scan_job = self.after(2000, self.run_scan_loop) # Re-run the same conditional step
            else:
                self.log("Fallback action failed. Stopping bot.")
                self.toggle_bot()

    def _perform_fallback_action(self, action_details, scan_region):
        action_type = action_details.get('action_type')

        if action_type == "Click and Drag":
            self.log("Fallback action: Performing 'Click and Drag'.")
            params = action_details.get('action_params', {})
            offset_x = params.get('drag_offset_x', 0)
            offset_y = params.get('drag_offset_y', 0)

            start_x = scan_region['left'] + scan_region['width'] // 2
            start_y = scan_region['top'] + scan_region['height'] // 2
            end_x = start_x + offset_x
            end_y = start_y + offset_y

            self.log(f"Dragging from window center ({start_x}, {start_y}) to ({end_x}, {end_y})")
            click_and_drag(start_x, start_y, end_x, end_y)
            return True

        elif action_type == "Do Nothing":
            self.log("Fallback action: Doing nothing.")
            return True
        elif action_type == "Click" or action_type == "Click with Offset":
            self.log(f"Fallback: Finding '{action_details.get('detection_target_name')}' for action '{action_type}'.")
            haystack_img = capture_screen(scan_region)
            target_pos = None
            try:
                needle_img = cv2.imread(action_details['detection_target'], cv2.IMREAD_UNCHANGED)
                if needle_img is None:
                    raise IOError(f"File not found or image format not supported: {action_details['detection_target']}")
                target_pos = find_image(haystack_img, needle_img)
            except Exception as e:
                self.log(f"Fallback Error: Could not load image. {e}")
                return False

            if target_pos:
                abs_x = scan_region['left'] + target_pos[0]
                abs_y = scan_region['top'] + target_pos[1]

                if action_type == "Click":
                    self.log(f"Fallback action: Clicking at ({abs_x}, {abs_y})")
                    click_at(abs_x, abs_y)
                else: # Click with Offset
                    params = action_details.get('action_params', {})
                    offset_x = params.get('click_offset_x', 0)
                    offset_y = params.get('click_offset_y', 0)
                    click_x = abs_x + offset_x
                    click_y = abs_y + offset_y
                    self.log(f"Fallback action: Click with offset at ({click_x}, {click_y})")
                    click_at(click_x, click_y)
                return True
            else:
                self.log("Fallback target not found.")
                return False

        self.log(f"Unknown fallback action type: {action_type}")
        return False

    def start_hotkey_listener(self):
        if self.hotkey_listener: return
        def on_press(key):
            if key == keyboard.Key.f9:
                self.after(0, self.toggle_bot)
        self.hotkey_listener = keyboard.Listener(on_press=on_press)
        listener_thread = threading.Thread(target=self.hotkey_listener.run, daemon=True)
        listener_thread.start()
        self.log("Bot running... Press F9 to stop.")

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_area.see(tk.END)

    def _bgr_to_hex(self, bgr_color):
        b, g, r = bgr_color
        return f"#{r:02x}{g:02x}{b:02x}".upper()

class WindowSelector(tk.Toplevel):
    def __init__(self, master, is_splash=False):
        super().__init__(master)
        self.master = master
        self.is_splash = is_splash
        self.title("Select Target Window")
        self.geometry("350x450")

        # Find the root App instance for theming
        app = self.master
        while not isinstance(app, App):
            app = app.master

        self.configure(bg=app.bg_color)
        self.transient(master)
        self.grab_set()

        self.listbox = tk.Listbox(self, bg=app.widget_bg_color, fg=app.text_color, relief=tk.FLAT)
        self.listbox.pack(pady=10, padx=10, fill="both", expand=True)

        button_frame = tk.Frame(self, bg=app.bg_color)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Refresh", command=self.populate_windows, bg=app.widget_bg_color, fg=app.text_color, relief=tk.FLAT).pack(side="left", padx=5)
        tk.Button(button_frame, text="Select", command=self.on_select, bg=app.button_color, fg=app.button_text_color, relief=tk.FLAT).pack(side="left", padx=5)

        cancel_text = "Quit" if self.is_splash and isinstance(self.master, App) else "Cancel"
        tk.Button(button_frame, text=cancel_text, command=self.on_cancel, bg=app.widget_bg_color, fg=app.text_color, relief=tk.FLAT).pack(side="left", padx=5)

        self.populate_windows()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

    def populate_windows(self):
        self.listbox.delete(0, tk.END)
        titles = sorted([title for title in gw.getAllTitles() if title])
        for title in titles:
            self.listbox.insert(tk.END, title)

    def on_select(self):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            return
        selected_title = self.listbox.get(selected_indices[0])
        if hasattr(self.master, 'on_window_selected'):
            self.master.on_window_selected(selected_title)
        self.destroy()

    def on_cancel(self):
        # If this is the initial selection dialog and no selection has been made, closing it quits the app.
        if self.is_splash and isinstance(self.master, App) and not self.master.target_window_title.get():
            self.master.destroy()
        else:
            self.destroy()


class ScreenshotTaker(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.start_x = None
        self.start_y = None
        self.rect = None

        # Configure the Toplevel window
        self.attributes('-fullscreen', True)
        self.attributes('-alpha', 0.3)
        self.attributes('-topmost', True)
        self.transient(master)
        self.grab_set()

        self.canvas = tk.Canvas(self, cursor="cross")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<Escape>", lambda e: self.destroy())

    def on_button_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        # Create rectangle if it doesn't exist
        if not self.rect:
            self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)

    def on_mouse_drag(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)

        # Check for a minimal size to avoid accidental clicks
        if abs(end_x - self.start_x) < 5 or abs(end_y - self.start_y) < 5:
            self.destroy()
            return

        # Determine the bounding box
        x1 = int(min(self.start_x, end_x))
        y1 = int(min(self.start_y, end_y))
        x2 = int(max(self.start_x, end_x))
        y2 = int(max(self.start_y, end_y))

        # Hide this transparent window
        self.withdraw()
        # Give the window manager time to process the withdraw command
        self.update_idletasks()
        time.sleep(0.2)

        # Capture the screen region
        with mss.mss() as sct:
            monitor = {"top": y1, "left": x1, "width": x2 - x1, "height": y2 - y1}
            img = sct.grab(monitor)

            # Convert to numpy array in BGR format for OpenCV
            img_np = np.array(img)
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)

        # Call the master's callback
        self.master.on_screenshot_taken(img_bgr)

        # Destroy this window
        self.destroy()


class ColorSampler(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        app = self.master.master # The App instance

        # Hide the main window to get a clean screenshot
        app.withdraw()
        time.sleep(0.3) # Give WM time to hide the window

        # Configure the sampler Toplevel window
        self.attributes('-fullscreen', True)
        self.attributes('-topmost', True)
        self.transient(master)
        self.grab_set()

        # Take a screenshot of the primary monitor
        with mss.mss() as sct:
            # sct.monitors[0] is the entire virtual screen, [1] is the primary monitor
            sct_img = sct.grab(sct.monitors[1])

        # Convert to a PIL Image. mss provides .rgb for direct PIL compatibility.
        self.pil_img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)

        # Now that the screenshot is taken, we can show the main window again
        app.deiconify()

        # Create a PhotoImage to display in Tkinter
        self.tk_img = ImageTk.PhotoImage(self.pil_img)

        self.canvas = tk.Canvas(self, cursor="tcross")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, image=self.tk_img, anchor="nw")

        self.canvas.bind("<ButtonPress-1>", self.on_click)
        self.canvas.bind("<Escape>", lambda e: self.destroy())

    def on_click(self, event):
        x, y = event.x, event.y
        # Get the color from the original PIL image
        rgb_color = self.pil_img.getpixel((x, y))
        # Convert from tkinter's RGB to OpenCV's BGR
        bgr_color = [rgb_color[2], rgb_color[1], rgb_color[0]]
        # Pass the color to the parent's callback
        self.master.on_color_sampled(bgr_color)
        # Close the sampler
        self.destroy()


class StepEditor(tk.Toplevel):
    def __init__(self, master, step_data=None, index=None):
        super().__init__(master)
        self.master = master # This is the App instance
        self.step_data = step_data if step_data else {}
        self.index = index

        self.title("Step Editor")
        self.geometry("450x700") # Increased height for new options
        self.configure(bg=self.master.bg_color)
        self.transient(self.master)
        self.grab_set()

        # --- VARS ---
        self.step_type = tk.StringVar(value=self.step_data.get('step_type', 'simple'))

        # Vars for Simple Action
        self.detection_mode = tk.StringVar(value=self.step_data.get('detection_mode', 'Image'))
        self.action_type = tk.StringVar(value=self.step_data.get('action_type', 'Click'))
        self.simple_click_offset_x = tk.StringVar(value=self.step_data.get('action_params', {}).get('click_offset_x', '0'))
        self.simple_click_offset_y = tk.StringVar(value=self.step_data.get('action_params', {}).get('click_offset_y', '0'))
        self.text_to_type = tk.StringVar(value=self.step_data.get('action_params', {}).get('text', ''))
        self.target_window_title = tk.StringVar(value=self.step_data.get('window_title', self.master.target_window_title.get() or ''))
        if self.step_data.get('detection_mode') == 'Color':
            self.target_color_bgr = self.step_data.get('detection_target', [0,0,255])
        else:
            self.target_color_bgr = [0,0,255] # Default value
        self.template_var = tk.StringVar(value=os.path.basename(self.step_data.get('detection_target', '')) if self.step_data.get('detection_mode') == 'Image' else '')

        # Vars for Conditional Loop
        self.max_retries = tk.StringVar(value=self.step_data.get('max_retries', '5'))
        self.primary_template_var = tk.StringVar(value=self.step_data.get('primary_target', {}).get('detection_target_name', ''))
        self.fallback_template_var = tk.StringVar(value=self.step_data.get('on_fail', {}).get('detection_target_name', ''))
        self.fallback_action_type = tk.StringVar(value=self.step_data.get('on_fail', {}).get('action_type', 'Click'))
        self.fallback_drag_offset_x = tk.StringVar(value=self.step_data.get('on_fail', {}).get('action_params', {}).get('drag_offset_x', '0'))
        self.fallback_drag_offset_y = tk.StringVar(value=self.step_data.get('on_fail', {}).get('action_params', {}).get('drag_offset_y', '0'))
        self._active_screenshot_target = None # Used to route screenshot callback

        # Vars for Post-Action Wait
        wait_params = self.step_data.get('wait_params', {})
        self.wait_type = tk.StringVar(value=wait_params.get('type', 'Fixed'))
        self.fixed_wait = tk.StringVar(value=wait_params.get('fixed_time', '1.0'))
        self.min_wait = tk.StringVar(value=wait_params.get('min_time', '1.0'))
        self.max_wait = tk.StringVar(value=wait_params.get('max_time', '2.0'))

        # --- LAYOUT FRAMES ---
        # A bottom frame for buttons that never gets pushed out of view
        button_frame = tk.Frame(self, bg=self.master.bg_color)
        button_frame.pack(side="bottom", fill="x", pady=10, padx=10)

        # A main content frame that can expand and scroll
        content_frame = tk.Frame(self, bg=self.master.bg_color)
        content_frame.pack(side="top", fill="both", expand=True)

        # --- WIDGETS ---
        # --- Step Type Selection ---
        step_type_frame = tk.LabelFrame(content_frame, text="Step Type", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        step_type_frame.pack(pady=10, padx=10, fill="x")
        tk.Radiobutton(step_type_frame, text="Simple Action", variable=self.step_type, value="simple", command=self.on_step_type_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left", padx=5)
        tk.Radiobutton(step_type_frame, text="Conditional Loop", variable=self.step_type, value="conditional_loop", command=self.on_step_type_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left", padx=5)

        # --- Main Frames for each step type (parented to content_frame) ---
        self.simple_action_frame = tk.Frame(content_frame, bg=self.master.bg_color)
        self.conditional_loop_frame = tk.Frame(content_frame, bg=self.master.bg_color)

        # --- UI for Simple Action Frame ---
        self.build_simple_action_ui(self.simple_action_frame)

        # --- UI for Conditional Loop Frame ---
        self.build_conditional_loop_ui(self.conditional_loop_frame)

        # --- Save/Cancel Buttons (parented to button_frame) ---
        tk.Button(button_frame, text="Cancel", command=self.destroy, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=10).pack(side="right", padx=10)
        tk.Button(button_frame, text="Save Step", command=self.on_save, bg=self.master.button_color, fg=self.master.button_text_color, relief=tk.FLAT, width=10).pack(side="right")

        self.on_step_type_change() # Set initial view

    def build_simple_action_ui(self, parent_frame):
        # This function builds the UI for a simple action, parented to the given frame.
        window_frame = tk.LabelFrame(parent_frame, text="1. Select Target Window", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        window_frame.pack(pady=10, padx=10, fill="x")
        self.window_label = tk.Label(window_frame, textvariable=self.target_window_title, bg=self.master.widget_bg_color, fg=self.master.text_color, wraplength=250)
        self.window_label.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(window_frame, text="Select...", command=self.select_window, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(side="left")
        if not self.target_window_title.get(): self.target_window_title.set("(None Selected)")

        mode_frame = tk.LabelFrame(parent_frame, text="2. Choose What to Look For", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        mode_frame.pack(pady=10, padx=10, fill="x")
        tk.Radiobutton(mode_frame, text="Color", variable=self.detection_mode, value="Color", command=self.on_mode_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")
        tk.Radiobutton(mode_frame, text="Image", variable=self.detection_mode, value="Image", command=self.on_mode_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")

        self.color_frame = tk.Frame(parent_frame, bg=self.master.bg_color)
        self.image_frame = tk.Frame(parent_frame, bg=self.master.bg_color)

        tk.Button(self.color_frame, text="Sample Color", command=self.sample_color, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack()
        self.color_preview = tk.Frame(self.color_frame, bg=self.master._bgr_to_hex(self.target_color_bgr), width=25, height=25, relief=tk.SUNKEN, borderwidth=1)
        self.color_preview.pack(pady=5)

        tk.Button(self.image_frame, text="Take Screenshot", command=self.take_screenshot, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack()
        self.template_dropdown = tk.OptionMenu(self.image_frame, self.template_var, "")
        self.template_dropdown.pack(pady=5)
        self.update_template_list()

        action_frame = tk.LabelFrame(parent_frame, text="3. Choose Action", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        action_frame.pack(pady=10, padx=10, fill="x")
        tk.Radiobutton(action_frame, text="Click", variable=self.action_type, value="Click", command=self.on_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")
        tk.Radiobutton(action_frame, text="Click with Offset", variable=self.action_type, value="Click with Offset", command=self.on_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")
        tk.Radiobutton(action_frame, text="Type", variable=self.action_type, value="Type", command=self.on_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")

        self.type_entry_frame = tk.Frame(action_frame, bg=self.master.bg_color)
        self.type_entry = tk.Entry(self.type_entry_frame, textvariable=self.text_to_type, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT)
        self.type_entry.pack(fill="x", padx=5, pady=5)

        self.simple_offset_frame = tk.Frame(action_frame, bg=self.master.bg_color)
        simple_offset_x_frame = tk.Frame(self.simple_offset_frame, bg=self.master.bg_color)
        tk.Label(simple_offset_x_frame, text="X Offset:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(simple_offset_x_frame, textvariable=self.simple_click_offset_x, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=7).pack(side="left")
        simple_offset_x_frame.pack(fill="x", pady=2)
        simple_offset_y_frame = tk.Frame(self.simple_offset_frame, bg=self.master.bg_color)
        tk.Label(simple_offset_y_frame, text="Y Offset:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(simple_offset_y_frame, textvariable=self.simple_click_offset_y, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=7).pack(side="left")
        simple_offset_y_frame.pack(fill="x", pady=2)

        self.on_mode_change()
        self.on_action_change()
        self._build_wait_ui(parent_frame).pack(pady=10, padx=10, fill="x")

    def build_conditional_loop_ui(self, parent_frame):
        # --- Loop Settings ---
        retries_frame = tk.LabelFrame(parent_frame, text="Loop Settings", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        retries_frame.pack(pady=5, padx=10, fill="x")
        tk.Label(retries_frame, text="Max Retries:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(retries_frame, textvariable=self.max_retries, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=5).pack(side="left", padx=5)

        # --- Primary Target ---
        primary_target_frame = tk.LabelFrame(parent_frame, text="Primary Target (Image to find)", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        primary_target_frame.pack(pady=5, padx=10, fill="x")
        self.primary_template_dropdown = self._build_image_selection_ui(primary_target_frame, self.primary_template_var, "primary")

        # --- Fallback Action ---
        fallback_action_frame = tk.LabelFrame(parent_frame, text="Fallback Action (If primary target not found)", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        fallback_action_frame.pack(pady=5, padx=10, fill="x")

        # --- Fallback Action Type ---
        fallback_action_type_frame = tk.Frame(fallback_action_frame, bg=self.master.bg_color)
        tk.Label(fallback_action_type_frame, text="Action:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", pady=2, padx=5)
        tk.Radiobutton(fallback_action_type_frame, text="Do Nothing", variable=self.fallback_action_type, value="Do Nothing", command=self.on_fallback_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left")
        tk.Radiobutton(fallback_action_type_frame, text="Click", variable=self.fallback_action_type, value="Click", command=self.on_fallback_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left")
        tk.Radiobutton(fallback_action_type_frame, text="Click with Offset", variable=self.fallback_action_type, value="Click with Offset", command=self.on_fallback_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left")
        tk.Radiobutton(fallback_action_type_frame, text="Click and Drag", variable=self.fallback_action_type, value="Click and Drag", command=self.on_fallback_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left")
        fallback_action_type_frame.pack(fill="x")

        # --- Fallback Action Params ---
        self.fallback_drag_frame = tk.Frame(fallback_action_frame, bg=self.master.bg_color)
        drag_x_frame = tk.Frame(self.fallback_drag_frame, bg=self.master.bg_color)
        tk.Label(drag_x_frame, text="X Offset:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(drag_x_frame, textvariable=self.fallback_drag_offset_x, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=7).pack(side="left")
        drag_x_frame.pack(fill="x", pady=2)
        drag_y_frame = tk.Frame(self.fallback_drag_frame, bg=self.master.bg_color)
        tk.Label(drag_y_frame, text="Y Offset:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(drag_y_frame, textvariable=self.fallback_drag_offset_y, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=7).pack(side="left")
        drag_y_frame.pack(fill="x", pady=2)

        # --- Fallback Target ---
        self.fallback_target_frame = tk.Frame(fallback_action_frame, bg=self.master.bg_color)
        tk.Label(self.fallback_target_frame, text="Target for Fallback Action:", bg=self.master.bg_color, fg=self.master.text_color).pack(pady=2, anchor="w", padx=5)
        self.fallback_template_dropdown = self._build_image_selection_ui(self.fallback_target_frame, self.fallback_template_var, "fallback")
        self.fallback_target_frame.pack(fill="x")

        self.update_conditional_template_lists()
        self.on_fallback_action_change()
        self._build_wait_ui(parent_frame).pack(pady=10, padx=10, fill="x")

    def _build_image_selection_ui(self, parent, template_var, target_key):
        frame = tk.Frame(parent, bg=self.master.bg_color)
        tk.Button(frame, text="Take Screenshot", command=lambda: self.take_screenshot_for(target_key), bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(side="left", padx=5, pady=5)

        dropdown = tk.OptionMenu(frame, template_var, "No templates found")
        dropdown.config(bg=self.master.widget_bg_color, fg=self.master.text_color, activebackground=self.master.widget_bg_color, activeforeground=self.master.text_color, relief=tk.FLAT)
        dropdown["menu"].config(bg=self.master.widget_bg_color, fg=self.master.text_color)
        dropdown.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        frame.pack(fill="x", expand=True)
        return dropdown

    def take_screenshot_for(self, target_type):
        self._active_screenshot_target = target_type
        self.take_screenshot()

    def update_conditional_template_lists(self):
        templates = [f for f in os.listdir("templates") if f.endswith(".png")]
        if not templates:
            templates = ["No templates found"]

        # Update primary dropdown
        menu1 = self.primary_template_dropdown["menu"]
        menu1.delete(0, "end")
        for t in templates:
            menu1.add_command(label=t, command=lambda v=t: self.primary_template_var.set(v))
        if self.primary_template_var.get() not in templates:
             self.primary_template_var.set(templates[0])

        # Update fallback dropdown
        menu2 = self.fallback_template_dropdown["menu"]
        menu2.delete(0, "end")
        for t in templates:
            menu2.add_command(label=t, command=lambda v=t: self.fallback_template_var.set(v))
        if self.fallback_template_var.get() not in templates:
            self.fallback_template_var.set(templates[0])

    def on_step_type_change(self):
        step_type = self.step_type.get()
        if step_type == 'simple':
            self.conditional_loop_frame.pack_forget()
            self.simple_action_frame.pack(fill="x", expand=True, padx=10)
        else: # conditional_loop
            self.simple_action_frame.pack_forget()
            self.conditional_loop_frame.pack(fill="x", expand=True, padx=10)

    def on_mode_change(self):
        if self.detection_mode.get() == "Color":
            self.image_frame.pack_forget()
            self.color_frame.pack(pady=10, padx=10, fill="x")
        else:
            self.color_frame.pack_forget()
            self.image_frame.pack(pady=10, padx=10, fill="x")

    def on_action_change(self):
        action = self.action_type.get()
        if action == "Type":
            self.type_entry_frame.pack(fill="x", padx=5, pady=2)
            self.simple_offset_frame.pack_forget()
        elif action == "Click with Offset":
            self.type_entry_frame.pack_forget()
            self.simple_offset_frame.pack(fill="x", padx=15, pady=2)
        else:  # Click
            self.type_entry_frame.pack_forget()
            self.simple_offset_frame.pack_forget()

    def on_fallback_action_change(self):
        action = self.fallback_action_type.get()
        if action == "Click with Offset":
            self.fallback_drag_frame.pack(fill="x", padx=15, pady=2)
            self.fallback_target_frame.pack(fill="x")
        elif action == "Click and Drag":
            self.fallback_drag_frame.pack(fill="x", padx=15, pady=2)
            self.fallback_target_frame.pack_forget()
        elif action == "Do Nothing":
            self.fallback_drag_frame.pack_forget()
            self.fallback_target_frame.pack_forget()
        else: # Click
            self.fallback_drag_frame.pack_forget()
            self.fallback_target_frame.pack(fill="x")

    def _build_wait_ui(self, parent_frame):
        wait_frame = tk.LabelFrame(parent_frame, text="Post-Action Wait", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)

        # --- Wait Type ---
        wait_type_frame = tk.Frame(wait_frame, bg=self.master.bg_color)
        tk.Radiobutton(wait_type_frame, text="None", variable=self.wait_type, value="None", command=self.on_wait_type_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left")
        tk.Radiobutton(wait_type_frame, text="Fixed", variable=self.wait_type, value="Fixed", command=self.on_wait_type_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left")
        tk.Radiobutton(wait_type_frame, text="Random", variable=self.wait_type, value="Random", command=self.on_wait_type_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left")
        wait_type_frame.pack(fill="x", pady=(0,5))

        # --- Fixed Wait Frame ---
        self.fixed_wait_frame = tk.Frame(wait_frame, bg=self.master.bg_color)
        tk.Label(self.fixed_wait_frame, text="Wait (sec):", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(self.fixed_wait_frame, textvariable=self.fixed_wait, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=7).pack(side="left")

        # --- Random Wait Frame ---
        self.random_wait_frame = tk.Frame(wait_frame, bg=self.master.bg_color)
        tk.Label(self.random_wait_frame, text="Min (sec):", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(self.random_wait_frame, textvariable=self.min_wait, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=7).pack(side="left")
        tk.Label(self.random_wait_frame, text="Max (sec):", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=(10,5))
        tk.Entry(self.random_wait_frame, textvariable=self.max_wait, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=7).pack(side="left")

        self.on_wait_type_change() # Set initial visibility
        return wait_frame

    def on_wait_type_change(self):
        wait_type = self.wait_type.get()
        if wait_type == "Fixed":
            self.fixed_wait_frame.pack(fill="x", pady=2)
            self.random_wait_frame.pack_forget()
        elif wait_type == "Random":
            self.fixed_wait_frame.pack_forget()
            self.random_wait_frame.pack(fill="x", pady=2)
        else: # None
            self.fixed_wait_frame.pack_forget()
            self.random_wait_frame.pack_forget()

    def on_save(self):
        step_type = self.step_type.get()

        if step_type == 'simple':
            step = {
                "step_type": "simple",
                "window_title": self.target_window_title.get(),
                "detection_mode": self.detection_mode.get(),
                "action_type": self.action_type.get(),
                "action_params": {},
                "detection_target": None,
                "detection_target_name": ""
            }

            action_type = step['action_type']
            if action_type == 'Type':
                step['action_params']['text'] = self.text_to_type.get()
            elif action_type == 'Click with Offset':
                try:
                    step['action_params']['click_offset_x'] = int(self.simple_click_offset_x.get())
                    step['action_params']['click_offset_y'] = int(self.simple_click_offset_y.get())
                except ValueError:
                    self.master.log("Error: Click offsets must be integers.")
                    return

            if step['detection_mode'] == 'Color':
                step['detection_target'] = self.target_color_bgr
                step['detection_target_name'] = self.master._bgr_to_hex(self.target_color_bgr)
            else: # Image
                target_name = self.template_var.get()
                if not target_name or target_name == "No templates found":
                    self.master.log("Error: No template image selected for this step.")
                    return
                step['detection_target'] = os.path.join("templates", target_name)
                step['detection_target_name'] = target_name
        else: # conditional_loop
            primary_target_name = self.primary_template_var.get()
            fallback_target_name = self.fallback_template_var.get()
            fallback_action_type = self.fallback_action_type.get()

            if not primary_target_name or "No templates" in primary_target_name:
                self.master.log("Error: A primary target image must be selected for a conditional loop.")
                return

            if fallback_action_type == "Click" or fallback_action_type == "Click with Offset":
                if not fallback_target_name or "No templates" in fallback_target_name:
                    self.master.log(f"Error: A fallback target image must be selected for a '{fallback_action_type}' fallback action.")
                    return
            # "Do Nothing" and "Click and Drag" do not require a fallback target.

            try:
                max_retries = int(self.max_retries.get())
            except ValueError:
                self.master.log("Error: Max retries must be an integer.")
                return

            on_fail_params = {}
            if fallback_action_type == "Click and Drag" or fallback_action_type == "Click with Offset":
                try:
                    if fallback_action_type == "Click and Drag":
                        on_fail_params['drag_offset_x'] = int(self.fallback_drag_offset_x.get())
                        on_fail_params['drag_offset_y'] = int(self.fallback_drag_offset_y.get())
                    else: # Click with Offset
                        on_fail_params['click_offset_x'] = int(self.fallback_drag_offset_x.get())
                        on_fail_params['click_offset_y'] = int(self.fallback_drag_offset_y.get())
                except ValueError:
                    self.master.log("Error: Fallback offsets must be integers.")
                    return

            on_fail_dict = {
                "action_type": fallback_action_type,
                "action_params": on_fail_params
            }

            if fallback_action_type == "Click" or fallback_action_type == "Click with Offset":
                on_fail_dict["detection_mode"] = "Image"
                on_fail_dict["detection_target"] = os.path.join("templates", fallback_target_name)
                on_fail_dict["detection_target_name"] = fallback_target_name
            else: # Click and Drag or Do Nothing
                on_fail_dict["detection_mode"] = None
                on_fail_dict["detection_target"] = None
                on_fail_dict["detection_target_name"] = None

            step = {
                "step_type": "conditional_loop",
                "window_title": self.target_window_title.get(),
                "max_retries": max_retries,
                "primary_target": {
                    "detection_mode": "Image",
                    "detection_target": os.path.join("templates", primary_target_name),
                    "detection_target_name": primary_target_name,
                },
                "on_fail": on_fail_dict
            }

        # --- Save Wait Parameters ---
        wait_type = self.wait_type.get()
        wait_params = {'type': wait_type}
        try:
            if wait_type == 'Fixed':
                wait_params['fixed_time'] = float(self.fixed_wait.get())
            elif wait_type == 'Random':
                wait_params['min_time'] = float(self.min_wait.get())
                wait_params['max_time'] = float(self.max_wait.get())
                if wait_params['min_time'] >= wait_params['max_time']:
                    self.master.log("Error: Min wait time must be less than max wait time.")
                    return
        except ValueError:
            self.master.log("Error: Wait times must be valid numbers.")
            return
        step['wait_params'] = wait_params

        self.master.on_step_saved(step, self.index)
        self.destroy()

    def select_window(self):
        WindowSelector(self, is_splash=False)

    def on_window_selected(self, title):
        self.target_window_title.set(title)
        self.master.log(f"Step editor window target set to: {title}")

    def sample_color(self):
        ColorSampler(self)

    def on_color_sampled(self, bgr_color):
        self.target_color_bgr = bgr_color
        hex_color = self.master._bgr_to_hex(bgr_color)
        self.color_preview.config(bg=hex_color)
        self.master.log(f"Step color changed to {hex_color}")

    def take_screenshot(self):
        ScreenshotTaker(self)

    def on_screenshot_taken(self, image):
        self.master.log("Screenshot captured for step.")
        filepath = filedialog.asksaveasfilename(
            parent=self,
            initialdir="templates",
            title="Save Template",
            filetypes=(("PNG files", "*.png"),),
            defaultextension=".png"
        )
        if filepath:
            try:
                cv2.imwrite(filepath, image)
                self.master.log(f"Template saved to {filepath}")

                # Update the correct variable based on which screenshot button was pressed
                target_var = None
                if self._active_screenshot_target == 'primary':
                    target_var = self.primary_template_var
                elif self._active_screenshot_target == 'fallback':
                    target_var = self.fallback_template_var
                else: # Default to the simple action template var
                    target_var = self.template_var

                if target_var:
                    target_var.set(os.path.basename(filepath))

                # Update all template lists
                self.update_template_list()
                if self.step_type.get() == 'conditional_loop':
                    self.update_conditional_template_lists()

            except Exception as e:
                self.master.log(f"Error saving template: {e}")

    def update_template_list(self):
        menu = self.template_dropdown["menu"]
        menu.delete(0, "end")
        templates = [f for f in os.listdir("templates") if f.endswith(".png")]
        if templates:
            for template in templates:
                menu.add_command(label=template, command=lambda value=template: self.template_var.set(value))
            if not self.template_var.get() in templates:
                self.template_var.set(templates[0])
        else:
            self.template_var.set("No templates found")

if __name__ == "__main__":
    app = App()
    app.mainloop()
