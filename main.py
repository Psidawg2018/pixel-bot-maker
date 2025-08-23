import tkinter as tk
from tkinter import scrolledtext, colorchooser, filedialog, ttk
import time
import json
import random
import re

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
from automation import click_at, right_click_at, type_text, click_and_drag, scroll_wheel, press_key_combination
from settings_manager import SettingsManager

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pixel Bot")
        self.settings_manager = SettingsManager()
        self.geometry("800x600")

        # --- Color Theme ---
        self.dark_theme = {
            "bg_color": "#2C3E50", "widget_bg_color": "#34495E", "text_color": "#ECF0F1",
            "button_color": "#3498DB", "button_text_color": "#ECF0F1"
        }
        self.light_theme = {
            "bg_color": "#ECECEC", "widget_bg_color": "#FFFFFF", "text_color": "#000000",
            "button_color": "#007BFF", "button_text_color": "#FFFFFF"
        }
        self._configure_theme()
        self.configure(bg=self.bg_color)

        # --- App State ---
        self.running = False
        self.scan_job = None
        self.hotkey_listener = None
        self.action_sequence = []
        self.variables = {} # For the new variable system
        self.current_step_index = 0
        self.current_retry_count = 0
        self.hide_window_var = tk.BooleanVar(value=self.settings_manager.get_setting('hide_bot_default'))
        self.target_window_title = tk.StringVar()
        self.target_window_title.set("") # Set to empty string initially

        # Ensure templates directory exists
        if not os.path.exists("templates"):
            os.makedirs("templates")

        # --- Main Layout Frames ---
        main_frame = tk.Frame(self, bg=self.bg_color)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = tk.Frame(main_frame, bg=self.bg_color)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        right_frame = tk.Frame(main_frame, bg=self.bg_color)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # --- WIDGET CREATION (Right Panel) ---
        self.log_area = scrolledtext.ScrolledText(right_frame, width=45, height=10, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT, insertbackground=self.text_color)
        self.log_area.pack(fill="both", expand=True)

        # --- WIDGET CREATION (Left Panel) ---
        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure('TNotebook', background=self.bg_color, borderwidth=0)
        self.style.configure('TNotebook.Tab', background=self.bg_color, foreground=self.text_color, lightcolor=self.widget_bg_color, borderwidth=2)
        self.style.map('TNotebook.Tab', background=[('selected', self.widget_bg_color)], foreground=[('selected', self.text_color)])

        notebook = ttk.Notebook(left_frame, style='TNotebook')
        notebook.pack(expand=True, fill='both')

        main_tab = tk.Frame(notebook, bg=self.bg_color)
        settings_tab = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(main_tab, text='Main')
        notebook.add(settings_tab, text='Settings')

        # --- Main Tab Content ---
        # --- Sequence Editor UI ---
        sequence_frame = tk.LabelFrame(main_tab, text="Action Sequence", bg=self.bg_color, fg=self.text_color, padx=5, pady=5)
        sequence_frame.pack(fill="x", pady=(10, 10), padx=10)

        # Frame for Save/Load buttons
        file_io_frame = tk.Frame(sequence_frame, bg=self.bg_color)
        file_io_frame.pack(fill="x", pady=(0, 5))
        tk.Button(file_io_frame, text="Load Sequence", command=self.load_sequence, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT).pack(side="left", padx=5)
        tk.Button(file_io_frame, text="Save Sequence", command=self.save_sequence, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT).pack(side="left", padx=5)

        list_container = tk.Frame(sequence_frame, bg=self.bg_color)
        list_container.pack(fill="x")
        self.sequence_listbox = tk.Listbox(list_container, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT, height=10)
        self.sequence_listbox.pack(side="left", fill="x", expand=True)
        self.sequence_listbox.bind("<<ListboxSelect>>", self.on_sequence_select)
        seq_button_frame = tk.Frame(list_container, bg=self.bg_color)
        seq_button_frame.pack(side="left", padx=(5,0))
        self.add_step_button = tk.Button(seq_button_frame, text="Add", command=self.add_step, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT, state=tk.DISABLED)
        self.add_step_button.pack(pady=2, fill="x")
        self.edit_step_button = tk.Button(seq_button_frame, text="Edit", command=self.edit_step, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT, state=tk.DISABLED)
        self.edit_step_button.pack(pady=2, fill="x")
        self.move_up_button = tk.Button(seq_button_frame, text="Move Up", command=self.move_step_up, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT, state=tk.DISABLED)
        self.move_up_button.pack(pady=2, fill="x")
        self.move_down_button = tk.Button(seq_button_frame, text="Move Down", command=self.move_step_down, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT, state=tk.DISABLED)
        self.move_down_button.pack(pady=2, fill="x")
        self.remove_step_button = tk.Button(seq_button_frame, text="Remove", command=self.remove_step, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT, state=tk.DISABLED)
        self.remove_step_button.pack(pady=2, fill="x")

        # --- Final Controls ---
        controls_frame = tk.LabelFrame(main_tab, text="Global Target", bg=self.bg_color, fg=self.text_color, padx=5, pady=5)
        controls_frame.pack(pady=10, padx=10, fill="x")

        self.target_window_label = tk.Label(controls_frame, textvariable=self.target_window_title, bg=self.widget_bg_color, fg=self.text_color, wraplength=380, justify="left")
        self.target_window_label.pack(pady=5, fill="x")
        tk.Button(controls_frame, text="Change Target Window", command=self.prompt_for_window_selection, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT).pack(pady=(0,5))

        # --- Most Loaded Sequences ---
        most_loaded_frame = tk.LabelFrame(main_tab, text="Frequently Used", bg=self.bg_color, fg=self.text_color, padx=5, pady=5)
        most_loaded_frame.pack(pady=10, padx=10, fill="x")
        self.most_loaded_container = tk.Frame(most_loaded_frame, bg=self.bg_color)
        self.most_loaded_container.pack(fill="x", pady=5)

        bot_controls_frame = tk.Frame(main_tab, bg=self.bg_color)
        bot_controls_frame.pack(pady=10, padx=10, fill="x", side="bottom")

        self.hide_window_check = tk.Checkbutton(bot_controls_frame, text="Hide window when bot is running", variable=self.hide_window_var, bg=self.bg_color, fg=self.text_color, selectcolor=self.widget_bg_color, activebackground=self.bg_color, activeforeground=self.text_color)
        self.hide_window_check.pack()

        self.start_button = tk.Button(bot_controls_frame, text="Start Bot", command=self.toggle_bot, bg=self.button_color, fg=self.button_text_color, activebackground="#2980B9", activeforeground=self.text_color, relief=tk.FLAT, padx=10, pady=5)
        self.start_button.pack(pady=10)

        # --- Settings Tab Content ---
        settings_content_frame = tk.Frame(settings_tab, bg=self.bg_color)
        settings_content_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- General Settings ---
        general_frame = tk.LabelFrame(settings_content_frame, text="General", bg=self.bg_color, fg=self.text_color, padx=5, pady=5)
        general_frame.pack(fill="x", pady=5, anchor="n")

        self.hide_bot_default_var = tk.BooleanVar(value=self.settings_manager.get_setting('hide_bot_default'))
        hide_bot_check = tk.Checkbutton(general_frame, text="Hide window by default when bot is running", variable=self.hide_bot_default_var, bg=self.bg_color, fg=self.text_color, selectcolor=self.widget_bg_color, activebackground=self.bg_color, activeforeground=self.text_color, command=self.save_hide_bot_default)
        hide_bot_check.pack(anchor="w", padx=5, pady=2)

        # --- Appearance Settings ---
        theme_frame = tk.LabelFrame(settings_content_frame, text="Appearance", bg=self.bg_color, fg=self.text_color, padx=5, pady=5)
        theme_frame.pack(fill="x", pady=5, anchor="n")

        self.theme_var = tk.StringVar(value=self.settings_manager.get_setting('theme'))
        theme_label = tk.Label(theme_frame, text="Theme:", bg=self.bg_color, fg=self.text_color)
        theme_label.pack(side="left", padx=5)
        dark_radio = tk.Radiobutton(theme_frame, text="Dark", variable=self.theme_var, value="dark", bg=self.bg_color, fg=self.text_color, selectcolor=self.widget_bg_color, command=self.apply_theme)
        dark_radio.pack(side="left")
        light_radio = tk.Radiobutton(theme_frame, text="Light", variable=self.theme_var, value="light", bg=self.bg_color, fg=self.text_color, selectcolor=self.widget_bg_color, command=self.apply_theme)
        light_radio.pack(side="left")

        # --- Image Matching Settings ---
        matching_frame = tk.LabelFrame(settings_content_frame, text="Image Matching", bg=self.bg_color, fg=self.text_color, padx=5, pady=5)
        matching_frame.pack(fill="x", pady=5, anchor="n")

        self.similarity_threshold_var = tk.DoubleVar(value=self.settings_manager.get_setting('image_similarity_threshold'))

        threshold_inner_frame = tk.Frame(matching_frame, bg=self.bg_color)
        threshold_inner_frame.pack(fill="x", pady=2)

        tk.Label(threshold_inner_frame, text="Similarity Threshold:", bg=self.bg_color, fg=self.text_color).pack(side="left", padx=5)
        self.similarity_label_var = tk.StringVar(value=f"{self.similarity_threshold_var.get():.2f}")
        tk.Label(threshold_inner_frame, textvariable=self.similarity_label_var, bg=self.widget_bg_color, fg=self.text_color, width=5).pack(side="left")

        similarity_slider = tk.Scale(
            threshold_inner_frame,
            from_=0.0,
            to=1.0,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            variable=self.similarity_threshold_var,
            command=self.save_similarity_threshold,
            bg=self.bg_color,
            fg=self.text_color,
            troughcolor=self.widget_bg_color,
            showvalue=0, # Hide the default value text
            relief=tk.FLAT,
            highlightthickness=0
        )
        similarity_slider.pack(side="left", fill="x", expand=True, padx=5)


        # --- Hotkey Settings ---
        hotkey_frame = tk.LabelFrame(settings_content_frame, text="Hotkey", bg=self.bg_color, fg=self.text_color, padx=5, pady=5)
        hotkey_frame.pack(fill="x", pady=5, anchor="n")

        hotkey_inner_frame = tk.Frame(hotkey_frame, bg=self.bg_color)
        hotkey_inner_frame.pack(fill="x", pady=2)
        tk.Label(hotkey_inner_frame, text="Start/Stop Hotkey:", bg=self.bg_color, fg=self.text_color).pack(side="left", padx=5)
        self.hotkey_label_var = tk.StringVar(value=self.settings_manager.get_setting('hotkey'))
        tk.Label(hotkey_inner_frame, textvariable=self.hotkey_label_var, bg=self.widget_bg_color, fg=self.text_color, padx=10, width=12, anchor="center").pack(side="left")
        self.change_hotkey_button = tk.Button(hotkey_inner_frame, text="Change...", command=self.change_hotkey, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT)
        self.change_hotkey_button.pack(side="left", padx=5)

        # Placeholder for Default Wait Times UI
        wait_frame = tk.LabelFrame(settings_content_frame, text="Default Wait Times (Coming Soon)", bg=self.bg_color, fg=self.text_color, padx=5, pady=5)
        wait_frame.pack(fill="x", pady=5, anchor="n")
        tk.Label(wait_frame, text="Configuration for default wait times will be added here.", bg=self.bg_color, fg=self.text_color, wraplength=350, justify="left").pack(pady=10, padx=5)

        self.log("Welcome! Please select a target window to begin.")
        self.update_most_loaded_list()
        self.after(200, lambda: self.prompt_for_window_selection(is_splash=True))

    def _configure_theme(self):
        theme = self.settings_manager.get_setting('theme')
        colors = self.dark_theme if theme == 'dark' else self.light_theme

        self.bg_color = colors['bg_color']
        self.widget_bg_color = colors['widget_bg_color']
        self.text_color = colors['text_color']
        self.button_color = colors['button_color']
        self.button_text_color = colors['button_text_color']

    def prompt_for_window_selection(self, is_splash=False):
        self.log("Prompting for target window selection...")
        WindowSelector(self, is_splash=is_splash)

    def on_window_selected(self, title):
        self.target_window_title.set(title)
        if self.add_step_button['state'] == tk.DISABLED:
            self.add_step_button.config(state=tk.NORMAL)
        self.log(f"Global target window set to: {title}")

    def on_sequence_select(self, event):
        selected_indices = self.sequence_listbox.curselection()
        if selected_indices:
            index = selected_indices[0]
            self.edit_step_button.config(state=tk.NORMAL)
            self.remove_step_button.config(state=tk.NORMAL)

            # Enable/disable Move Up button
            if index > 0:
                self.move_up_button.config(state=tk.NORMAL)
            else:
                self.move_up_button.config(state=tk.DISABLED)

            # Enable/disable Move Down button
            if index < len(self.action_sequence) - 1:
                self.move_down_button.config(state=tk.NORMAL)
            else:
                self.move_down_button.config(state=tk.DISABLED)
        else:
            self.edit_step_button.config(state=tk.DISABLED)
            self.remove_step_button.config(state=tk.DISABLED)
            self.move_up_button.config(state=tk.DISABLED)
            self.move_down_button.config(state=tk.DISABLED)

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

    def move_step_up(self):
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices:
            return

        index = selected_indices[0]
        if index > 0:
            # Swap with the previous item
            self.action_sequence[index], self.action_sequence[index - 1] = self.action_sequence[index - 1], self.action_sequence[index]
            self.update_sequence_listbox()
            # Reselect the item at its new position
            self.sequence_listbox.selection_set(index - 1)
            self.on_sequence_select(None) # Update button states

    def move_step_down(self):
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices:
            return

        index = selected_indices[0]
        if index < len(self.action_sequence) - 1:
            # Swap with the next item
            self.action_sequence[index], self.action_sequence[index + 1] = self.action_sequence[index + 1], self.action_sequence[index]
            self.update_sequence_listbox()
            # Reselect the item at its new position
            self.sequence_listbox.selection_set(index + 1)
            self.on_sequence_select(None) # Update button states

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
                text += f"CONDITIONAL ({retries}x): Find '{primary_target_name}', on fail: {fallback_action}"
            elif step_type == 'loop':
                loop_mode = step.get('loop_mode', 'repeat')
                if loop_mode == 'repeat':
                    repeat_count = step.get('loop_repeat_count', 'N/A')
                    text += f"LOOP: Repeat {repeat_count} times"
                else:
                    text += f"LOOP: Until condition"
            else:
                text += "Unknown Step Type"

            self.sequence_listbox.insert(tk.END, text)
        self.on_sequence_select(None)

    def save_sequence(self):
        if not self.action_sequence:
            self.log("Cannot save an empty sequence.")
            return

        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Save Sequence",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
            defaultextension=".json"
        )
        if not filepath:
            return

        try:
            with open(filepath, 'w') as f:
                json.dump(self.action_sequence, f, indent=4)
            self.log(f"Sequence saved to {os.path.basename(filepath)}")
        except Exception as e:
            self.log(f"Error saving sequence: {e}")

    def update_most_loaded_list(self):
        # Clear existing labels
        for widget in self.most_loaded_container.winfo_children():
            widget.destroy()
        most_loaded = self.settings_manager.get_most_loaded_sequences(count=3)

        if not most_loaded:
            tk.Label(self.most_loaded_container, text="No sequences loaded yet.", bg=self.bg_color, fg=self.text_color, anchor="w").pack(fill="x", pady=2)
            return

        for filepath, count in most_loaded:
            # Shorten the display name
            display_name = os.path.basename(filepath)

            # Create a clickable label
            label_text = f"  {display_name} ({count} loads)"
            label = tk.Label(self.most_loaded_container, text=label_text, bg=self.widget_bg_color, fg=self.text_color, anchor="w", padx=5, cursor="hand2")
            label.pack(fill="x", pady=(0, 2))
            label.bind("<Button-1>", lambda e, path=filepath: self.load_sequence(path))
            label.bind("<Enter>", lambda e: e.widget.config(bg=self.button_color))
            label.bind("<Leave>", lambda e: e.widget.config(bg=self.widget_bg_color))

    def load_sequence(self, filepath=None):
        if filepath is None:
            filepath = filedialog.askopenfilename(
                parent=self,
                title="Load Sequence",
                filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
            )
        if not filepath:
            return

        try:
            with open(filepath, 'r') as f:
                loaded_sequence = json.load(f)

            if not isinstance(loaded_sequence, list):
                raise TypeError("File does not contain a valid sequence list.")

            self.action_sequence = loaded_sequence
            self.update_sequence_listbox()
            self.log(f"Sequence loaded from {os.path.basename(filepath)}")

            # Increment load count and update the list
            self.settings_manager.increment_sequence_load_count(filepath)
            self.update_most_loaded_list()
        except json.JSONDecodeError:
            self.log("Error: The selected file is not a valid JSON file.")
        except TypeError as e:
            self.log(f"Error loading sequence: {e}")
        except Exception as e:
            self.log(f"An unexpected error occurred while loading: {e}")

    def save_hide_bot_default(self):
        self.settings_manager.set_setting('hide_bot_default', self.hide_bot_default_var.get())
        self.log("Default 'Hide Bot' setting saved.")

    def save_similarity_threshold(self, value):
        """Called when the similarity slider is moved."""
        # The 'value' argument is a string from the Scale widget, so we convert it to float
        new_threshold = float(value)
        self.settings_manager.set_setting('image_similarity_threshold', new_threshold)
        self.similarity_label_var.set(f"{new_threshold:.2f}")
        # No log message here to prevent spamming the log while dragging the slider

    def apply_theme(self):
        theme = self.theme_var.get()
        self.settings_manager.set_setting('theme', theme)
        self.log("Theme changed. Please restart the application for the changes to take full effect.")

    def change_hotkey(self):
        HotkeyChangeDialog(self)

    def start_hotkey_listener(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()

        hotkey_str = self.settings_manager.get_setting('hotkey')
        target_key = None

        try:
            if hasattr(keyboard.Key, hotkey_str.lower()):
                target_key = getattr(keyboard.Key, hotkey_str.lower())
            elif len(hotkey_str) == 1:
                target_key = keyboard.KeyCode.from_char(hotkey_str)
        except Exception as e:
            self.log(f"Error parsing hotkey '{hotkey_str}': {e}. Defaulting to F9.")
            target_key = keyboard.Key.f9
            self.hotkey_label_var.set("f9")
            self.settings_manager.set_setting('hotkey', "f9")

        if target_key is None:
            self.log(f"Invalid hotkey '{hotkey_str}'. Please set a valid key. Defaulting to F9.")
            target_key = keyboard.Key.f9
            self.hotkey_label_var.set("f9")
            self.settings_manager.set_setting('hotkey', "f9")

        def on_press(key):
            if key == target_key:
                self.after(0, self.toggle_bot)

        self.hotkey_listener = keyboard.Listener(on_press=on_press)
        self.hotkey_listener.start()
        self.log(f"Bot running... Press '{hotkey_str.upper()}' to stop.")

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
            self.variables.clear() # Reset variables at the start of a run
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

    def _substitute_variables(self, text):
        """
        Substitutes placeholders like {{var_name}} in a string with their
        values from the self.variables dictionary.
        """
        if not isinstance(text, str):
            return text

        # This regex finds all occurrences of {{...}}
        return re.sub(r'\{\{(.*?)\}\}', self._replace_match, text)

    def _replace_match(self, match):
        """
        Helper function for re.sub to look up the variable.
        """
        var_name = match.group(1).strip()
        # Return the value if found, otherwise return the original placeholder
        return self.variables.get(var_name, match.group(0))

    def run_scan_loop(self):
        if not self.running:
            return

        if self.current_step_index >= len(self.action_sequence):
            self.log("Action sequence complete. Stopping bot.")
            self.toggle_bot()
            return

        current_step = self.action_sequence[self.current_step_index]
        step_type = current_step.get('step_type', 'simple')
        action_type = current_step.get('action_type')

        # Handle non-UI actions first
        if action_type == 'Set Variable':
            var_name = current_step.get('action_params', {}).get('variable_name')
            var_value = self._substitute_variables(current_step.get('action_params', {}).get('variable_value')) # Allow variables in values
            if var_name:
                self.log(f"Setting variable '{var_name}' to '{var_value}'")
                self.variables[var_name] = var_value
                self.current_step_index += 1
                self._handle_post_action_wait(current_step) # Still respect wait times
            else:
                self.log(f"Error in Step {self.current_step_index+1}: 'Set Variable' action has no variable name. Stopping bot.")
                self.toggle_bot()
            return
        elif action_type == 'OCR':
            params = current_step.get('action_params', {})
            region = params.get('ocr_region')
            output_var = params.get('output_variable_name')

            if not region or not output_var:
                self.log(f"Error in Step {self.current_step_index+1}: OCR step is not configured correctly. Stopping bot.")
                self.toggle_bot()
                return

            self.log(f"Performing OCR on region {region} and saving to '{output_var}'...")
            screenshot = capture_screen(region)
            from image_analyzer import extract_text_from_image
            extracted_text = extract_text_from_image(screenshot)

            if extracted_text == "TESSERACT_NOT_FOUND":
                self.log("FATAL: Tesseract OCR engine not found. Please install it to use the OCR feature. Stopping bot.")
                self.toggle_bot()
                return

            self.log(f"OCR Result: '{extracted_text}'. Stored in variable '{output_var}'.")
            self.variables[output_var] = extracted_text
            self.current_step_index += 1
            self._handle_post_action_wait(current_step)
            return


        if step_type == 'simple':
            self._execute_simple_step(current_step)
        elif step_type == 'loop':
            self._execute_loop_step(current_step)
        elif step_type == 'conditional_loop':
            self._execute_conditional_loop_step(current_step)
        else:
            self.log(f"Error: Unknown step type '{step_type}' at step {self.current_step_index + 1}. Stopping bot.")
            self.toggle_bot()

    def _execute_loop_step(self, step):
        loop_mode = step.get('loop_mode', 'repeat')

        target_window_title = step.get("window_title")
        if not target_window_title:
            self.log(f"Error in Loop Step {self.current_step_index+1}: No target window specified. Stopping bot.")
            self.toggle_bot()
            return

        try:
            target_windows = gw.getWindowsWithTitle(target_window_title)
            if not target_windows:
                self.log(f"Step {self.current_step_index+1}: Window '{target_window_title}' not found. Re-scanning...")
                self.scan_job = self.after(2000, self.run_scan_loop)
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
                self.log(f"Using custom scan region: {scan_region}")

        except Exception as e:
            self.log(f"Error getting window details: {e}. Stopping bot.")
            self.toggle_bot()
            return

        if loop_mode == 'repeat':
            repeat_count = step.get('loop_repeat_count', 1)
            self.log(f"Executing Loop Step {self.current_step_index + 1}: Repeating {repeat_count} times.")

            for i in range(repeat_count):
                self.log(f"  Loop iteration {i+1}/{repeat_count}")
                for action_step in step.get('loop_actions', []):
                    if not self.running: return # Check if bot was stopped

                    # We pass the same scan_region for all sub-actions
                    if not self._execute_single_action(action_step, scan_region):
                        self.log(f"    - Sub-action failed. Stopping bot.")
                        self.toggle_bot()
                        return

            self.log("Loop finished.")
            self.current_step_index += 1
            self._handle_post_action_wait(step)

        elif loop_mode == 'until':
            max_retries = step.get('max_retries', 10)
            condition_target = step.get('loop_condition_target')
            condition_found = False
            self.log(f"Executing Loop Step {self.current_step_index + 1}: Looping until '{step.get('loop_condition_target_name')}' is found.")

            for i in range(max_retries):
                if not self.running: return

                # 1. Check for the condition
                self.log(f"  - Condition check attempt {i+1}/{max_retries}...")
                haystack_img = capture_screen(scan_region)
                try:
                    targets = step['loop_condition_target']
                    if isinstance(targets, str): targets = [targets]
                    needle_imgs = [cv2.imread(p, cv2.IMREAD_UNCHANGED) for p in targets]

                    threshold = self.settings_manager.get_setting('image_similarity_threshold')
                    if find_image(haystack_img, [img for img in needle_imgs if img is not None], threshold=threshold):
                        self.log("  - Condition met. Exiting loop.")
                        condition_found = True
                        break
                except Exception as e:
                    self.log(f"  - Error loading condition image(s): {e}. Stopping bot.")
                    self.toggle_bot()
                    return

                # 2. If condition not met, perform actions
                self.log(f"  - Condition not met. Performing loop actions...")
                for action_step in step.get('loop_actions', []):
                    if not self.running: return
                    if not self._execute_single_action(action_step, scan_region):
                        self.log("    - Sub-action failed. Stopping bot.")
                        self.toggle_bot()
                        return

                # Small delay before next condition check
                time.sleep(1)

            if condition_found:
                self.log("Loop finished successfully.")
                self.current_step_index += 1
                self._handle_post_action_wait(step)
            else:
                self.log(f"Loop failed: Condition not met after {max_retries} retries. Stopping bot.")
                self.toggle_bot()

    def _execute_single_action(self, action_step, scan_region):
        """
        Executes a single, simple action. Returns True on success, False on failure.
        """
        self.log(f"  - Action: Find {action_step['detection_mode']} '{action_step.get('detection_target_name', 'N/A')}'...")
        haystack_img = capture_screen(scan_region)

        target_pos = None
        if action_step['detection_mode'] == "Color":
            locations = find_color(haystack_img, action_step['detection_target'])
            if locations:
                target_pos = locations[0]
        elif action_step['detection_mode'] == "Image":
            try:
                targets = action_step['detection_target']
                if isinstance(targets, str): # Backward compatibility
                    targets = [targets]

                needle_imgs = []
                for target_path in targets:
                    img = cv2.imread(target_path, cv2.IMREAD_UNCHANGED)
                    if img is None:
                        self.log(f"    - Warning: Could not load template image '{os.path.basename(target_path)}'. Skipping it.")
                        continue
                    needle_imgs.append(img)

                if not needle_imgs:
                    self.log(f"    - Error: No valid template images could be loaded.")
                    return False

                threshold = self.settings_manager.get_setting('image_similarity_threshold')
                target_pos = find_image(haystack_img, needle_imgs, threshold=threshold)
            except Exception as e:
                self.log(f"    - Error during image search: {e}")
                return False

        if target_pos:
            self.log(f"    - Target found.")
            abs_x = scan_region['left'] + target_pos[0]
            abs_y = scan_region['top'] + target_pos[1]

            action_type = action_step['action_type']
            action_params = action_step.get('action_params', {})

            if action_type == "Click":
                self.log(f"    - Performing action: Click at ({abs_x}, {abs_y})")
                click_at(abs_x, abs_y)
            elif action_type == "Right-click":
                self.log(f"    - Performing action: Right-click at ({abs_x}, {abs_y})")
                right_click_at(abs_x, abs_y)
            elif action_type == "Click with Offset":
                offset_x = action_params.get('click_offset_x', 0)
                offset_y = action_params.get('click_offset_y', 0)
                click_x = abs_x + offset_x
                click_y = abs_y + offset_y
                self.log(f"    - Performing action: Click with offset at ({click_x}, {click_y})")
                click_at(click_x, click_y)
            elif action_type == "Type":
                text_to_type = action_params.get('text', '')
                substituted_text = self._substitute_variables(text_to_type)
                self.log(f"    - Performing action: Type '{substituted_text}'")
                type_text(substituted_text)
            elif action_type == "Key Combo":
                key_combo = action_params.get('key_combo', '')
                substituted_combo = self._substitute_variables(key_combo)
                self.log(f"    - Performing action: Press keys '{substituted_combo}'")
                press_key_combination(substituted_combo)
            elif action_type == "Scroll":
                direction = action_params.get('scroll_direction', 'Down')
                amount = action_params.get('scroll_amount', 5)
                self.log(f"    - Performing action: Scroll {direction} by {amount}")
                scroll_wheel(direction.lower(), amount)

            # Sub-actions have waits too
            self._handle_post_action_wait(action_step)
            return True
        else:
            self.log("    - Target not found.")
            return False

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
                self.log(f"Using custom scan region for loop: {scan_region}")

        except Exception as e:
            self.log(f"Error getting window details: {e}. Stopping bot.")
            self.toggle_bot()
            return

        if self._execute_single_action(step, scan_region):
            self.current_step_index += 1
            self.current_retry_count = 0 # Reset for next step
            self.log("Action complete.")
            # The wait is handled inside _execute_single_action now
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
                self.log(f"Using custom scan region for conditional loop: {scan_region}")

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
            targets = primary_target['detection_target']
            if isinstance(targets, str): targets = [targets]
            needle_imgs = [cv2.imread(p, cv2.IMREAD_UNCHANGED) for p in targets]
            threshold = self.settings_manager.get_setting('image_similarity_threshold')
            primary_pos = find_image(haystack_img, [img for img in needle_imgs if img is not None], threshold=threshold)
        except Exception as e:
            self.log(f"Loop Error: Could not load primary target image(s). {e}")
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


        if action_type == "Do Nothing":
            self.log("Fallback action: Doing nothing.")
            return True
        elif action_type == "Click and Drag":

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

        elif action_type == "Scroll":
            params = action_details.get('action_params', {})
            direction = params.get('scroll_direction', 'Down')
            amount = params.get('scroll_amount', 5)
            self.log(f"Fallback action: Scrolling {direction} by {amount}")
            scroll_wheel(direction.lower(), amount)
            return True
        elif action_type == "Click" or action_type == "Click with Offset":
            self.log(f"Fallback: Finding '{action_details.get('detection_target_name')}' for action '{action_type}'.")
            haystack_img = capture_screen(scan_region)
            target_pos = None
            try:
                targets = action_details['detection_target']
                if isinstance(targets, str): targets = [targets]
                needle_imgs = [cv2.imread(p, cv2.IMREAD_UNCHANGED) for p in targets]
                threshold = self.settings_manager.get_setting('image_similarity_threshold')
                target_pos = find_image(haystack_img, [img for img in needle_imgs if img is not None], threshold=threshold)
            except Exception as e:
                self.log(f"Fallback Error: Could not load image(s). {e}")
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


class RegionSelector(tk.Toplevel):
    def __init__(self, master, callback):
        super().__init__(master)
        self.master = master
        self.callback = callback
        self.start_x = None
        self.start_y = None
        self.rect = None

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
        if not self.rect:
            self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='green', width=2)

    def on_mouse_drag(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)

        if abs(end_x - self.start_x) < 5 or abs(end_y - self.start_y) < 5:
            self.destroy()
            return

        x = int(min(self.start_x, end_x))
        y = int(min(self.start_y, end_y))
        width = int(abs(end_x - self.start_x))
        height = int(abs(end_y - self.start_y))

        region = {'x': x, 'y': y, 'width': width, 'height': height}
        self.callback(region)
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
    def __init__(self, master, step_data=None, index=None, target_sequence_list=None, on_save_callback=None, is_sub_editor=False):
        super().__init__(master)
        self.master = master # This is the App instance
        self.step_data = step_data if step_data else {}
        self.index = index
        self.target_sequence_list = target_sequence_list
        self.on_save_callback = on_save_callback
        self.is_sub_editor = is_sub_editor

        self.title("Action Editor" if is_sub_editor else "Step Editor")
        self.geometry("563x700") # Increased height for new options
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
        self.key_combo_text = tk.StringVar(value=self.step_data.get('action_params', {}).get('key_combo', 'ctrl+c'))
        self.variable_name = tk.StringVar(value=self.step_data.get('action_params', {}).get('variable_name', ''))
        self.variable_value = tk.StringVar(value=self.step_data.get('action_params', {}).get('variable_value', ''))
        self.output_variable_name = tk.StringVar(value=self.step_data.get('action_params', {}).get('output_variable_name', 'ocr_result'))
        self.ocr_region = self.step_data.get('action_params', {}).get('ocr_region')
        self.ocr_region_label_var = tk.StringVar(value=self._get_ocr_region_display_text())
        self.scroll_direction = tk.StringVar(value=self.step_data.get('action_params', {}).get('scroll_direction', 'Down'))
        self.scroll_amount = tk.StringVar(value=self.step_data.get('action_params', {}).get('scroll_amount', '5'))
        self.target_window_title = tk.StringVar(value=self.step_data.get('window_title', self.master.target_window_title.get() or ''))

        self.search_region = self.step_data.get('search_region') # This is now a direct attribute
        self.search_region_label_var = tk.StringVar(value=self._get_region_display_text())
        if self.step_data.get('detection_mode') == 'Color':
            self.target_color_bgr = self.step_data.get('detection_target', [0,0,255])
        else:
            self.target_color_bgr = [0,0,255] # Default value
        # This var is legacy, from before multi-image support. It's not actively used, but we'll initialize it safely.
        detection_target = self.step_data.get('detection_target')
        initial_template_name = ''
        if self.step_data.get('detection_mode') == 'Image' and detection_target:
            if isinstance(detection_target, list):
                if detection_target: # Ensure list is not empty
                    initial_template_name = os.path.basename(detection_target[0])
            elif isinstance(detection_target, str):
                initial_template_name = os.path.basename(detection_target)
        self.template_var = tk.StringVar(value=initial_template_name)

        # Vars for Conditional Loop
        self.max_retries = tk.StringVar(value=self.step_data.get('max_retries', '5'))
        self.fallback_action_type = tk.StringVar(value=self.step_data.get('on_fail', {}).get('action_type', 'Click'))
        self.fallback_drag_offset_x = tk.StringVar(value=self.step_data.get('on_fail', {}).get('action_params', {}).get('drag_offset_x', '0'))
        self.fallback_drag_offset_y = tk.StringVar(value=self.step_data.get('on_fail', {}).get('action_params', {}).get('drag_offset_y', '0'))

        # Vars for Loop Step
        self.loop_mode = tk.StringVar(value=self.step_data.get('loop_mode', 'repeat'))
        self.loop_repeat_count = tk.StringVar(value=self.step_data.get('loop_repeat_count', '5'))
        self.loop_actions = self.step_data.get('loop_actions', [])
        self.loop_max_retries = tk.StringVar(value=self.step_data.get('max_retries', '10'))

        # Vars for Post-Action Wait
        wait_params = self.step_data.get('wait_params', {})
        self.wait_type = tk.StringVar(value=wait_params.get('type', 'None'))
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
        self.step_type_radios = {}
        step_types = [("Simple Action", "simple"), ("Loop", "loop"), ("Conditional (Legacy)", "conditional_loop")]
        for text, value in step_types:
            radio = tk.Radiobutton(step_type_frame, text=text, variable=self.step_type, value=value, command=self.on_step_type_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color)
            radio.pack(side="left", padx=5)
            self.step_type_radios[value] = radio


        # --- Main Frames for each step type (parented to content_frame) ---
        self.simple_action_frame = tk.Frame(content_frame, bg=self.master.bg_color)
        self.conditional_loop_frame = tk.Frame(content_frame, bg=self.master.bg_color)
        self.loop_frame = tk.Frame(content_frame, bg=self.master.bg_color)


        # --- UI for Simple Action Frame ---
        self.build_simple_action_ui(self.simple_action_frame)

        # --- UI for Conditional Loop Frame ---
        self.build_conditional_loop_ui(self.conditional_loop_frame)

        # --- UI for Loop Frame ---
        self.build_loop_ui(self.loop_frame)

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

        region_frame = tk.LabelFrame(parent_frame, text="2. Set Search Region (Optional)", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        region_frame.pack(pady=10, padx=10, fill="x")
        self.region_label = tk.Label(region_frame, textvariable=self.search_region_label_var, bg=self.master.widget_bg_color, fg=self.master.text_color, wraplength=350)
        self.region_label.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(region_frame, text="Set Region", command=self.set_search_region, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(side="left", padx=(0, 5))
        tk.Button(region_frame, text="Clear", command=self.clear_search_region, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(side="left")


        mode_frame = tk.LabelFrame(parent_frame, text="3. Choose What to Look For", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        mode_frame.pack(pady=10, padx=10, fill="x")
        tk.Radiobutton(mode_frame, text="Color", variable=self.detection_mode, value="Color", command=self.on_mode_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")
        tk.Radiobutton(mode_frame, text="Image", variable=self.detection_mode, value="Image", command=self.on_mode_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")

        self.color_frame = tk.Frame(parent_frame, bg=self.master.bg_color)
        self.image_frame = tk.Frame(parent_frame, bg=self.master.bg_color)

        tk.Button(self.color_frame, text="Sample Color", command=self.sample_color, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack()
        self.color_preview = tk.Frame(self.color_frame, bg=self.master._bgr_to_hex(self.target_color_bgr), width=25, height=25, relief=tk.SUNKEN, borderwidth=1)
        self.color_preview.pack(pady=5)

        tk.Button(self.image_frame, text="Take Screenshot", command=self.take_screenshot, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(pady=(0,5))

        # --- Image List ---
        image_list_frame = tk.Frame(self.image_frame, bg=self.master.bg_color)
        image_list_frame.pack(fill="x", expand=True, pady=5)

        self.image_listbox = tk.Listbox(image_list_frame, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, height=4, selectmode=tk.EXTENDED)
        self.image_listbox.pack(side="left", fill="x", expand=True)

        image_button_frame = tk.Frame(image_list_frame, bg=self.master.bg_color)
        image_button_frame.pack(side="left", padx=(5,0))
        tk.Button(image_button_frame, text="Add", command=lambda: self._add_image_template_to_listbox(self.image_listbox), bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(fill="x", pady=2)
        tk.Button(image_button_frame, text="Remove", command=lambda: self._remove_image_template_from_listbox(self.image_listbox), bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(fill="x", pady=2)

        self._update_image_listbox()

        action_frame = tk.LabelFrame(parent_frame, text="3. Choose Action", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        action_frame.pack(pady=10, padx=10, fill="x")
        tk.Radiobutton(action_frame, text="Click", variable=self.action_type, value="Click", command=self.on_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")
        tk.Radiobutton(action_frame, text="Right-click", variable=self.action_type, value="Right-click", command=self.on_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")
        tk.Radiobutton(action_frame, text="Click with Offset", variable=self.action_type, value="Click with Offset", command=self.on_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")
        tk.Radiobutton(action_frame, text="Type", variable=self.action_type, value="Type", command=self.on_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")
        tk.Radiobutton(action_frame, text="Key Combo", variable=self.action_type, value="Key Combo", command=self.on_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")
        tk.Radiobutton(action_frame, text="Scroll", variable=self.action_type, value="Scroll", command=self.on_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")
        tk.Radiobutton(action_frame, text="Set Variable", variable=self.action_type, value="Set Variable", command=self.on_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")
        tk.Radiobutton(action_frame, text="OCR", variable=self.action_type, value="OCR", command=self.on_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")

        self.type_entry_frame = tk.Frame(action_frame, bg=self.master.bg_color)
        self.type_entry = tk.Entry(self.type_entry_frame, textvariable=self.text_to_type, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT)
        self.type_entry.pack(fill="x", padx=5, pady=5)

        self.key_combo_frame = tk.Frame(action_frame, bg=self.master.bg_color)
        tk.Label(self.key_combo_frame, text="Keys (e.g., ctrl+alt+delete):", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        self.key_combo_entry = tk.Entry(self.key_combo_frame, textvariable=self.key_combo_text, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=20)
        self.key_combo_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        self.set_variable_frame = tk.Frame(action_frame, bg=self.master.bg_color)
        tk.Label(self.set_variable_frame, text="Name:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(self.set_variable_frame, textvariable=self.variable_name, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=15).pack(side="left", padx=5)
        tk.Label(self.set_variable_frame, text="Value:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(self.set_variable_frame, textvariable=self.variable_value, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=20).pack(side="left", padx=5)

        self.ocr_frame = tk.Frame(action_frame, bg=self.master.bg_color)
        ocr_var_frame = tk.Frame(self.ocr_frame, bg=self.master.bg_color)
        tk.Label(ocr_var_frame, text="Save Text to Variable:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(ocr_var_frame, textvariable=self.output_variable_name, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=20).pack(side="left", padx=5)
        ocr_var_frame.pack(fill="x", pady=2)

        ocr_region_frame = tk.Frame(self.ocr_frame, bg=self.master.bg_color)
        self.ocr_region_label = tk.Label(ocr_region_frame, textvariable=self.ocr_region_label_var, bg=self.master.widget_bg_color, fg=self.master.text_color, wraplength=350)
        self.ocr_region_label.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(ocr_region_frame, text="Set Region", command=self.set_ocr_region, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(side="left", padx=(0, 5))
        ocr_region_frame.pack(fill="x", pady=2)


        self.simple_offset_frame = tk.Frame(action_frame, bg=self.master.bg_color)
        simple_offset_x_frame = tk.Frame(self.simple_offset_frame, bg=self.master.bg_color)
        tk.Label(simple_offset_x_frame, text="X Offset:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(simple_offset_x_frame, textvariable=self.simple_click_offset_x, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=7).pack(side="left")
        simple_offset_x_frame.pack(fill="x", pady=2)
        simple_offset_y_frame = tk.Frame(self.simple_offset_frame, bg=self.master.bg_color)
        tk.Label(simple_offset_y_frame, text="Y Offset:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(simple_offset_y_frame, textvariable=self.simple_click_offset_y, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=7).pack(side="left")
        simple_offset_y_frame.pack(fill="x", pady=2)

        self.scroll_frame = tk.Frame(action_frame, bg=self.master.bg_color)
        scroll_direction_frame = tk.Frame(self.scroll_frame, bg=self.master.bg_color)
        tk.Label(scroll_direction_frame, text="Direction:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.OptionMenu(scroll_direction_frame, self.scroll_direction, "Down", "Up").pack(side="left")
        scroll_direction_frame.pack(fill="x", pady=2)
        scroll_amount_frame = tk.Frame(self.scroll_frame, bg=self.master.bg_color)
        tk.Label(scroll_amount_frame, text="Amount:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(scroll_amount_frame, textvariable=self.scroll_amount, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=7).pack(side="left")
        scroll_amount_frame.pack(fill="x", pady=2)

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
        primary_target_frame = tk.LabelFrame(parent_frame, text="Primary Target (Image(s) to find)", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        primary_target_frame.pack(pady=5, padx=10, fill="x")

        primary_list_frame = tk.Frame(primary_target_frame, bg=self.master.bg_color)
        primary_list_frame.pack(fill="x", expand=True, pady=5)

        self.primary_image_listbox = tk.Listbox(primary_list_frame, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, height=4, selectmode=tk.EXTENDED)
        self.primary_image_listbox.pack(side="left", fill="x", expand=True)

        primary_button_frame = tk.Frame(primary_list_frame, bg=self.master.bg_color)
        primary_button_frame.pack(side="left", padx=(5,0))
        tk.Button(primary_button_frame, text="Add", command=lambda: self._add_image_template_to_listbox(self.primary_image_listbox), bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(fill="x", pady=2)
        tk.Button(primary_button_frame, text="Remove", command=lambda: self._remove_image_template_from_listbox(self.primary_image_listbox), bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(fill="x", pady=2)

        # --- Fallback Action ---
        fallback_action_frame = tk.LabelFrame(parent_frame, text="Fallback Action (If primary target not found)", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        fallback_action_frame.pack(pady=5, padx=10, fill="x")

        # --- Fallback Action Type ---
        fallback_action_type_frame = tk.Frame(fallback_action_frame, bg=self.master.bg_color)
        tk.Label(fallback_action_type_frame, text="Action:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", pady=2, padx=5)
        tk.Radiobutton(fallback_action_type_frame, text="Click", variable=self.fallback_action_type, value="Click", command=self.on_fallback_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left")
        tk.Radiobutton(fallback_action_type_frame, text="Click with Offset", variable=self.fallback_action_type, value="Click with Offset", command=self.on_fallback_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left")
        tk.Radiobutton(fallback_action_type_frame, text="Click and Drag", variable=self.fallback_action_type, value="Click and Drag", command=self.on_fallback_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left")
        tk.Radiobutton(fallback_action_type_frame, text="Do Nothing", variable=self.fallback_action_type, value="Do Nothing", command=self.on_fallback_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left")
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

        fallback_list_frame = tk.Frame(self.fallback_target_frame, bg=self.master.bg_color)
        fallback_list_frame.pack(fill="x", expand=True)

        self.fallback_image_listbox = tk.Listbox(fallback_list_frame, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, height=4, selectmode=tk.EXTENDED)
        self.fallback_image_listbox.pack(side="left", fill="x", expand=True)

        fallback_button_frame = tk.Frame(fallback_list_frame, bg=self.master.bg_color)
        fallback_button_frame.pack(side="left", padx=(5,0))
        tk.Button(fallback_button_frame, text="Add", command=lambda: self._add_image_template_to_listbox(self.fallback_image_listbox), bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(fill="x", pady=2)
        tk.Button(fallback_button_frame, text="Remove", command=lambda: self._remove_image_template_from_listbox(self.fallback_image_listbox), bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(fill="x", pady=2)

        self.fallback_target_frame.pack(fill="x")

        self._update_primary_image_listbox()
        self._update_fallback_image_listbox()
        self.on_fallback_action_change()
        self._build_wait_ui(parent_frame).pack(pady=10, padx=10, fill="x")

    def _update_primary_image_listbox(self):
        primary_target = self.step_data.get('primary_target', {})
        self._populate_listbox_from_step_data(self.primary_image_listbox, primary_target, 'detection_target')

    def build_loop_ui(self, parent_frame):
        # --- Loop Mode ---
        loop_mode_frame = tk.LabelFrame(parent_frame, text="Loop Mode", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        loop_mode_frame.pack(pady=5, padx=10, fill="x")
        tk.Radiobutton(loop_mode_frame, text="Repeat X Times", variable=self.loop_mode, value="repeat", command=self.on_loop_mode_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left")
        tk.Radiobutton(loop_mode_frame, text="Until Condition Met", variable=self.loop_mode, value="until", command=self.on_loop_mode_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(side="left")

        # --- Loop Settings ---
        self.loop_settings_frame = tk.Frame(parent_frame, bg=self.master.bg_color)
        self.loop_settings_frame.pack(pady=5, padx=10, fill="x")

        self.repeat_frame = tk.Frame(self.loop_settings_frame, bg=self.master.bg_color)
        tk.Label(self.repeat_frame, text="Repetitions:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(self.repeat_frame, textvariable=self.loop_repeat_count, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=5).pack(side="left")

        self.until_frame = tk.Frame(self.loop_settings_frame, bg=self.master.bg_color)
        tk.Label(self.until_frame, text="Condition (Image):", bg=self.master.bg_color, fg=self.master.text_color).pack(anchor="w", padx=5)

        until_list_frame = tk.Frame(self.until_frame, bg=self.master.bg_color)
        until_list_frame.pack(fill="x", expand=True)

        self.until_image_listbox = tk.Listbox(until_list_frame, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, height=4, selectmode=tk.EXTENDED)
        self.until_image_listbox.pack(side="left", fill="x", expand=True)

        until_button_frame = tk.Frame(until_list_frame, bg=self.master.bg_color)
        until_button_frame.pack(side="left", padx=(5,0))
        tk.Button(until_button_frame, text="Add", command=lambda: self._add_image_template_to_listbox(self.until_image_listbox), bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(fill="x", pady=2)
        tk.Button(until_button_frame, text="Remove", command=lambda: self._remove_image_template_from_listbox(self.until_image_listbox), bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(fill="x", pady=2)

        max_retries_frame = tk.Frame(self.until_frame, bg=self.master.bg_color)
        max_retries_frame.pack(fill="x", pady=2, side="bottom")
        tk.Label(max_retries_frame, text="Max Retries:", bg=self.master.bg_color, fg=self.master.text_color).pack(side="left", padx=5)
        tk.Entry(max_retries_frame, textvariable=self.loop_max_retries, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, width=5).pack(side="left")

        # --- Actions Frame ---
        actions_frame = tk.LabelFrame(parent_frame, text="Actions to Loop", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        actions_frame.pack(pady=5, padx=10, fill="both", expand=True)

        list_container = tk.Frame(actions_frame, bg=self.master.bg_color)
        list_container.pack(fill="both", expand=True)

        self.loop_actions_listbox = tk.Listbox(list_container, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, height=6)
        self.loop_actions_listbox.pack(side="left", fill="both", expand=True)
        self.loop_actions_listbox.bind("<<ListboxSelect>>", self.on_loop_action_select)

        seq_button_frame = tk.Frame(list_container, bg=self.master.bg_color)
        seq_button_frame.pack(side="left", padx=(5,0), fill="y")

        tk.Button(seq_button_frame, text="Add", command=self._add_loop_action, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(pady=2, fill="x")
        self.edit_loop_action_button = tk.Button(seq_button_frame, text="Edit", command=self._edit_loop_action, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, state=tk.DISABLED)
        self.edit_loop_action_button.pack(pady=2, fill="x")
        self.remove_loop_action_button = tk.Button(seq_button_frame, text="Remove", command=self._remove_loop_action, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT, state=tk.DISABLED)
        self.remove_loop_action_button.pack(pady=2, fill="x")

        # Disable loop/conditional step types if this is a sub-editor
        if self.is_sub_editor:
            self.step_type_radios['loop'].config(state=tk.DISABLED)
            self.step_type_radios['conditional_loop'].config(state=tk.DISABLED)
            self.step_type.set('simple') # Default to simple action for sub-steps


        self.on_loop_mode_change()
        self._update_loop_actions_listbox()
        self._update_until_image_listbox()

    def _add_loop_action(self):
        StepEditor(
            master=self.master,
            target_sequence_list=self.loop_actions,
            on_save_callback=self._update_loop_actions_listbox,
            is_sub_editor=True
        )

    def _edit_loop_action(self):
        selected_indices = self.loop_actions_listbox.curselection()
        if not selected_indices:
            return
        index = selected_indices[0]
        step_data = self.loop_actions[index]

        StepEditor(
            master=self.master,
            step_data=step_data,
            index=index,
            target_sequence_list=self.loop_actions,
            on_save_callback=self._update_loop_actions_listbox,
            is_sub_editor=True
        )

    def _remove_loop_action(self):
        selected_indices = self.loop_actions_listbox.curselection()
        if not selected_indices:
            return
        index = selected_indices[0]
        self.loop_actions.pop(index)
        self._update_loop_actions_listbox()
        self.master.log(f"Removed sub-action {index+1}.")

    def on_loop_action_select(self, event):
        selected_indices = self.loop_actions_listbox.curselection()
        if selected_indices:
            self.edit_loop_action_button.config(state=tk.NORMAL)
            self.remove_loop_action_button.config(state=tk.NORMAL)
        else:
            self.edit_loop_action_button.config(state=tk.DISABLED)
            self.remove_loop_action_button.config(state=tk.DISABLED)

    def _update_loop_actions_listbox(self):
        self.loop_actions_listbox.delete(0, tk.END)
        for i, step in enumerate(self.loop_actions):
            # This is a simplified representation. We can enhance it later.
            action = step.get('action_type', '?')
            target = step.get('detection_target_name', 'Unknown')
            text = f"{i+1}: {action} on '{target}'"
            self.loop_actions_listbox.insert(tk.END, text)


    def on_loop_mode_change(self):
        mode = self.loop_mode.get()
        if mode == 'repeat':
            self.repeat_frame.pack(fill="x")
            self.until_frame.pack_forget()
        else: # until
            self.repeat_frame.pack_forget()
            self.until_frame.pack(fill="x")



    def on_step_type_change(self):
        step_type = self.step_type.get()
        # Hide all frames first
        self.simple_action_frame.pack_forget()
        self.conditional_loop_frame.pack_forget()
        self.loop_frame.pack_forget()

        if step_type == 'simple':
            self.simple_action_frame.pack(fill="x", expand=True, padx=10)
        elif step_type == 'loop':
            self.loop_frame.pack(fill="x", expand=True, padx=10)
        else: # conditional_loop
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
        self.type_entry_frame.pack_forget()
        self.simple_offset_frame.pack_forget()
        self.scroll_frame.pack_forget()
        self.key_combo_frame.pack_forget()
        self.set_variable_frame.pack_forget()

        if action == "Type":
            self.type_entry_frame.pack(fill="x", padx=5, pady=2)
        elif action == "Click with Offset":
            self.simple_offset_frame.pack(fill="x", padx=15, pady=2)
        elif action == "Key Combo":
            self.key_combo_frame.pack(fill="x", padx=5, pady=2)
        elif action == "Scroll":
            self.scroll_frame.pack(fill="x", padx=15, pady=2)
        elif action == "Set Variable":
            self.set_variable_frame.pack(fill="x", padx=5, pady=2)
        elif action == "OCR":
            self.ocr_frame.pack(fill="x", padx=5, pady=2)

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
                "detection_target_name": "",
                "search_region": self.search_region
            }

            action_type = step['action_type']
            if action_type == 'Type':
                step['action_params']['text'] = self.text_to_type.get()
            elif action_type == 'Key Combo':
                step['action_params']['key_combo'] = self.key_combo_text.get()
            elif action_type == 'Set Variable':
                step['action_params']['variable_name'] = self.variable_name.get()
                step['action_params']['variable_value'] = self.variable_value.get()
            elif action_type == 'OCR':
                step['action_params']['output_variable_name'] = self.output_variable_name.get()
                step['action_params']['ocr_region'] = self.ocr_region
                if not self.ocr_region:
                    self.master.log("Error: OCR region is not set for this step.")
                    return
            elif action_type == 'Click with Offset':
                try:
                    step['action_params']['click_offset_x'] = int(self.simple_click_offset_x.get())
                    step['action_params']['click_offset_y'] = int(self.simple_click_offset_y.get())
                except ValueError:
                    self.master.log("Error: Click offsets must be integers.")
                    return
            elif action_type == 'Scroll':
                try:
                    step['action_params']['scroll_direction'] = self.scroll_direction.get()
                    step['action_params']['scroll_amount'] = int(self.scroll_amount.get())
                except ValueError:
                    self.master.log("Error: Scroll amount must be an integer.")
                    return

            if step['detection_mode'] == 'Color':
                step['detection_target'] = self.target_color_bgr
                step['detection_target_name'] = self.master._bgr_to_hex(self.target_color_bgr)
            else: # Image
                target_names = list(self.image_listbox.get(0, tk.END))
                if not target_names:
                    self.master.log("Error: No template images selected for this step.")
                    return
                # Save the list of full paths for later execution
                step['detection_target'] = [os.path.join("templates", name) for name in target_names]
                # Save just the names for display purposes
                step['detection_target_name'] = ", ".join(target_names)

        elif step_type == 'loop':
            try:
                repeat_count = int(self.loop_repeat_count.get())
            except ValueError:
                self.master.log("Error: Repetitions must be an integer.")
                return

            step = {
                "step_type": "loop",
                "loop_mode": self.loop_mode.get(),
                "loop_actions": self.loop_actions,
                "window_title": self.target_window_title.get(),
                "search_region": self.search_region
            }
            if step['loop_mode'] == 'repeat':
                step['loop_repeat_count'] = repeat_count
            else: # until
                try:
                    max_retries = int(self.loop_max_retries.get())
                except ValueError:
                    self.master.log("Error: Max retries must be an integer.")
                    return

                condition_target_names = list(self.until_image_listbox.get(0, tk.END))
                if not condition_target_names:
                    self.master.log("Error: At least one condition target image must be selected for an 'until' loop.")
                    return

                step['loop_condition_target'] = [os.path.join("templates", name) for name in condition_target_names]
                step['loop_condition_target_name'] = ", ".join(condition_target_names)
                step['max_retries'] = max_retries

        else: # conditional_loop
            try:
                max_retries = int(self.max_retries.get())
            except ValueError:
                self.master.log("Error: Max retries must be an integer.")
                return

            # Primary Target
            primary_target_names = list(self.primary_image_listbox.get(0, tk.END))
            if not primary_target_names:
                self.master.log("Error: At least one primary target image must be selected.")
                return

            primary_target_dict = {
                "detection_mode": "Image",
                "detection_target": [os.path.join("templates", name) for name in primary_target_names],
                "detection_target_name": ", ".join(primary_target_names),
            }

            # Fallback (on_fail) action
            fallback_action_type = self.fallback_action_type.get()
            on_fail_dict = { "action_type": fallback_action_type, "action_params": {} }

            if fallback_action_type in ["Click", "Click with Offset"]:
                fallback_target_names = list(self.fallback_image_listbox.get(0, tk.END))
                if not fallback_target_names:
                    self.master.log(f"Error: At least one fallback target image must be selected for a '{fallback_action_type}' action.")
                    return
                on_fail_dict["detection_mode"] = "Image"
                on_fail_dict["detection_target"] = [os.path.join("templates", name) for name in fallback_target_names]
                on_fail_dict["detection_target_name"] = ", ".join(fallback_target_names)

            if fallback_action_type == "Click with Offset":
                try:
                    on_fail_dict['action_params']['click_offset_x'] = int(self.fallback_drag_offset_x.get())
                    on_fail_dict['action_params']['click_offset_y'] = int(self.fallback_drag_offset_y.get())
                except ValueError:
                    self.master.log("Error: Fallback click offsets must be integers.")
                    return
            elif fallback_action_type == "Click and Drag":
                try:
                    on_fail_dict['action_params']['drag_offset_x'] = int(self.fallback_drag_offset_x.get())
                    on_fail_dict['action_params']['drag_offset_y'] = int(self.fallback_drag_offset_y.get())
                except ValueError:
                    self.master.log("Error: Fallback drag offsets must be integers.")
                    return

            step = {
                "step_type": "conditional_loop",
                "window_title": self.target_window_title.get(),
                "max_retries": max_retries,
                "primary_target": primary_target_dict,
                "on_fail": on_fail_dict,
                "search_region": self.search_region
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

        if self.target_sequence_list is not None and self.on_save_callback is not None:
            if self.index is not None:
                self.target_sequence_list[self.index] = step
            else:
                self.target_sequence_list.append(step)
            self.on_save_callback()
        else:
            # Default behavior: save to the main sequence
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

                # This method is now only called from the simple action editor,
                # so we can assume it's for the main image listbox.
                self.image_listbox.insert(tk.END, os.path.basename(filepath))

            except Exception as e:
                self.master.log(f"Error saving template: {e}")

    def _get_region_display_text(self):
        region = self.search_region
        if region:
            return f"Region set: X={region['x']}, Y={region['y']}, W={region['width']}, H={region['height']}"
        return "Not set. The entire target window will be searched."

    def set_search_region(self):
        self.master.log("Opening region selector...")
        RegionSelector(self, self.on_region_selected)

    def on_region_selected(self, region):
        # The region coordinates are relative to the screen. We need to make them
        # relative to the target window if a window is selected.
        try:
            target_window_title = self.target_window_title.get()
            if target_window_title and target_window_title != "(None Selected)":
                target_windows = gw.getWindowsWithTitle(target_window_title)
                if target_windows:
                    win = target_windows[0]
                    region['x'] -= win.left
                    region['y'] -= win.top
                    self.master.log(f"Region coordinates adjusted to be relative to window '{win.title}'.")

        except Exception as e:
            self.master.log(f"Could not adjust region to window: {e}. Using absolute coordinates.")

        self.search_region = region
        self.search_region_label_var.set(self._get_region_display_text())
        self.master.log(f"Search region set.")

    def clear_search_region(self):
        self.search_region = None
        self.search_region_label_var.set(self._get_region_display_text())
        self.master.log("Search region has been cleared.")

    def _add_image_template_to_listbox(self, listbox):
        filepaths = filedialog.askopenfilenames(
            parent=self,
            initialdir="templates",
            title="Select Image Templates",
            filetypes=(("PNG files", "*.png"), ("All files", "*.*"))
        )
        if filepaths:
            for filepath in filepaths:
                filename = os.path.basename(filepath)
                # Avoid adding duplicates
                if filename not in listbox.get(0, tk.END):
                    listbox.insert(tk.END, filename)

    def _remove_image_template_from_listbox(self, listbox):
        selected_indices = listbox.curselection()
        # Reverse the indices to avoid issues when deleting multiple items
        for i in sorted(selected_indices, reverse=True):
            listbox.delete(i)

    def _update_image_listbox(self):
        self._populate_listbox_from_step_data(self.image_listbox, self.step_data, 'detection_target')

    def _update_fallback_image_listbox(self):
        fallback_action = self.step_data.get('on_fail', {})
        self._populate_listbox_from_step_data(self.fallback_image_listbox, fallback_action, 'detection_target')

    def _update_until_image_listbox(self):
        self._populate_listbox_from_step_data(self.until_image_listbox, self.step_data, 'loop_condition_target')

    def _populate_listbox_from_step_data(self, listbox, data_dict, key):
        if not data_dict:
            return

        targets = data_dict.get(key, [])
        if isinstance(targets, str):
            # Handle old format where target was a single string path
            targets = [os.path.basename(targets)]

        listbox.delete(0, tk.END)
        for target in targets:
            # The saved value might be a full path, so we take the basename
            listbox.insert(tk.END, os.path.basename(target))

    def _get_ocr_region_display_text(self):
        region = self.ocr_region
        # Defensively check if region is a dictionary and has the required keys
        if isinstance(region, dict) and all(k in region for k in ['x', 'y', 'width', 'height']):
            return f"OCR Region: X={region['x']}, Y={region['y']}, W={region['width']}, H={region['height']}"
        return "Not set. Click 'Set Region' to define the area to read."

    def set_ocr_region(self):
        self.master.log("Opening region selector for OCR...")
        RegionSelector(self, self.on_ocr_region_selected)

    def on_ocr_region_selected(self, region):
        self.ocr_region = region
        self.ocr_region_label_var.set(self._get_ocr_region_display_text())
        self.master.log("OCR region set.")


class HotkeyChangeDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.title("Set Hotkey")
        self.geometry("300x150")
        self.configure(bg=self.master.bg_color)
        self.transient(self.master)
        self.grab_set()

        self.hotkey_str = tk.StringVar(value="Press any key...")

        tk.Label(self, text="Press any key to set it as the new hotkey.", bg=self.master.bg_color, fg=self.master.text_color, wraplength=280).pack(pady=10)
        tk.Label(self, textvariable=self.hotkey_str, bg=self.master.widget_bg_color, fg=self.master.text_color, width=20, font=("Arial", 12)).pack(pady=10)
        tk.Button(self, text="Cancel", command=self.on_close, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(pady=10)

        self.listener = keyboard.Listener(on_press=self.on_key_press, suppress=True)
        self.listener.start()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_key_press(self, key):
        try:
            key_name = None
            if isinstance(key, keyboard.Key):
                key_name = key.name
            elif isinstance(key, keyboard.KeyCode):
                key_name = key.char

            if key_name:
                self.hotkey_str.set(key_name)
                self.master.settings_manager.set_setting('hotkey', key_name)
                self.master.hotkey_label_var.set(key_name)
                self.master.log(f"Hotkey changed to: {key_name}")
                # Restart the main listener if it's running
                if self.master.hotkey_listener:
                    self.master.hotkey_listener.stop()
                    self.master.start_hotkey_listener()
        except Exception as e:
            self.master.log(f"Could not set hotkey: {e}")
        finally:
            self.after(100, self.on_close)

    def on_close(self):
        if self.listener.running:
            self.listener.stop()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
