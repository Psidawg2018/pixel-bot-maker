import tkinter as tk
from tkinter import scrolledtext, colorchooser, filedialog
import time
import json

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
from automation import click_at, type_text

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
        self.hide_window_var = tk.BooleanVar(value=True)

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
        self.add_step_button = tk.Button(seq_button_frame, text="Add", command=self.add_step, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT)
        self.add_step_button.pack(pady=2, fill="x")
        self.edit_step_button = tk.Button(seq_button_frame, text="Edit", command=self.edit_step, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT, state=tk.DISABLED)
        self.edit_step_button.pack(pady=2, fill="x")
        self.remove_step_button = tk.Button(seq_button_frame, text="Remove", command=self.remove_step, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT, state=tk.DISABLED)
        self.remove_step_button.pack(pady=2, fill="x")

        # --- Final Controls ---
        controls_frame = tk.Frame(self, bg=self.bg_color)
        controls_frame.pack(pady=10, padx=10, fill="x")

        self.hide_window_check = tk.Checkbutton(controls_frame, text="Hide window when bot is running", variable=self.hide_window_var, bg=self.bg_color, fg=self.text_color, selectcolor=self.widget_bg_color, activebackground=self.bg_color, activeforeground=self.text_color)
        self.hide_window_check.pack()

        self.start_button = tk.Button(controls_frame, text="Start Bot", command=self.toggle_bot, bg=self.button_color, fg=self.button_text_color, activebackground="#2980B9", activeforeground=self.text_color, relief=tk.FLAT, padx=10, pady=5)
        self.start_button.pack(pady=10)
        self.log_area.pack(pady=10, padx=10, fill="both", expand=True)

        self.log("Welcome! Press 'Start Bot' to begin.")

    def on_sequence_select(self, event):
        if self.sequence_listbox.curselection():
            self.edit_step_button.config(state=tk.NORMAL)
            self.remove_step_button.config(state=tk.NORMAL)
        else:
            self.edit_step_button.config(state=tk.DISABLED)
            self.remove_step_button.config(state=tk.DISABLED)

    def add_step(self):
        StepEditor(self, master=self)

    def edit_step(self):
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices:
            return
        index = selected_indices[0]
        step_data = self.action_sequence[index]
        StepEditor(self, master=self, step_data=step_data, index=index)

    def remove_step(self):
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices:
            return
        index = selected_indices[0]
        self.action_sequence.pop(index)
        self.update_sequence_listbox()
        self.log(f"Removed step {index+1}.")

    def on_step_saved(self, step_data, index=None):
        if index is not None:
            self.action_sequence[index] = step_data
        else:
            self.action_sequence.append(step_data)
        self.update_sequence_listbox()

    def update_sequence_listbox(self):
        self.sequence_listbox.delete(0, tk.END)
        for i, step in enumerate(self.action_sequence):
            mode = step['detection_mode']
            action = step['action_type']
            target = step.get('detection_target_name', 'Unknown')
            text = f"{i+1}: Find {mode} '{target}', then {action}"
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
            self.running = True
            self.start_button.config(text="Stop Bot")
            self.start_hotkey_listener()
            if self.hide_window_var.get():
                self.withdraw()
            self.run_scan_loop()

    def run_scan_loop(self):
        if not self.running:
            return

        if self.current_step_index >= len(self.action_sequence):
            self.log("Action sequence complete. Stopping bot.")
            self.toggle_bot()
            return

        current_step = self.action_sequence[self.current_step_index]
        target_window_title = current_step.get("window_title")

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

        self.log(f"Executing Step {self.current_step_index+1}: Find {current_step['detection_mode']} '{current_step.get('detection_target_name', 'N/A')}'...")

        haystack_img = capture_screen(scan_region)

        target_pos = None
        mode = current_step['detection_mode']

        if mode == "Color":
            locations = find_color(haystack_img, current_step['detection_target'])
            if locations:
                target_pos = locations[0]

        elif mode == "Image":
            try:
                needle_img = cv2.imread(current_step['detection_target'], cv2.IMREAD_UNCHANGED)
                target_pos = find_image(haystack_img, needle_img)
            except Exception as e:
                self.log(f"Step {self.current_step_index+1} Error: Could not load template. {e}")
                self.toggle_bot()
                return

        if target_pos:
            self.log(f"Step {self.current_step_index+1}: Target found at {target_pos} (relative).")
            abs_x = scan_region['left'] + target_pos[0]
            abs_y = scan_region['top'] + target_pos[1]

            action_type = current_step['action_type']
            action_params = current_step.get('action_params', {})

            if action_type == "Click":
                self.log(f"Performing action: Click at ({abs_x}, {abs_y})")
                click_at(abs_x, abs_y)
            elif action_type == "Type":
                text = action_params.get('text', '')
                self.log(f"Performing action: Type '{text}'")
                type_text(text)

            self.current_step_index += 1
            self.log("Action complete. Moving to next step in 1 second...")
            self.scan_job = self.after(1000, self.run_scan_loop)
        else:
            self.log("Target not found. Re-scanning same step in 2 seconds...")
            self.scan_job = self.after(2000, self.run_scan_loop)

    def start_hotkey_listener(self):
        if self.hotkey_listener:
            return
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

class StepEditor(tk.Toplevel):
    def __init__(self, parent, master, step_data=None, index=None):
        super().__init__(master)
        self.parent = parent
        self.master = master
        self.step_data = step_data if step_data else {}
        self.index = index

        self.title("Step Editor")
        self.geometry("450x600")
        self.configure(bg=self.master.bg_color)
        self.transient(self.master)
        self.grab_set()

        # --- VARS ---
        self.detection_mode = tk.StringVar(value=self.step_data.get('detection_mode', 'Image'))
        self.action_type = tk.StringVar(value=self.step_data.get('action_type', 'Click'))
        self.text_to_type = tk.StringVar(value=self.step_data.get('action_params', {}).get('text', ''))
        self.target_window_title = tk.StringVar(value=self.step_data.get('window_title', ''))
        self.target_color_bgr = self.step_data.get('detection_target', [0,0,255])
        self.template_var = tk.StringVar(value=os.path.basename(self.step_data.get('detection_target', '')) if self.step_data.get('detection_mode') == 'Image' else '')

        # --- WIDGETS ---
        # Window
        window_frame = tk.LabelFrame(self, text="1. Select Target Window", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        window_frame.pack(pady=10, padx=10, fill="x")
        self.window_label = tk.Label(window_frame, textvariable=self.target_window_title, bg=self.master.widget_bg_color, fg=self.master.text_color, wraplength=250)
        self.window_label.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(window_frame, text="Select...", command=self.select_window, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(side="left")
        if not self.target_window_title.get(): self.target_window_title.set("(None Selected)")


        # Detection Mode
        mode_frame = tk.LabelFrame(self, text="2. Choose What to Look For", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        mode_frame.pack(pady=10, padx=10, fill="x")
        tk.Radiobutton(mode_frame, text="Color", variable=self.detection_mode, value="Color", command=self.on_mode_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")
        tk.Radiobutton(mode_frame, text="Image", variable=self.detection_mode, value="Image", command=self.on_mode_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")

        # Detection Target
        self.color_frame = tk.Frame(self, bg=self.master.bg_color)
        self.image_frame = tk.Frame(self, bg=self.master.bg_color)

        # Color Target UI
        tk.Button(self.color_frame, text="Sample Color", command=self.sample_color, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack()
        self.color_preview = tk.Frame(self.color_frame, bg=self.master._bgr_to_hex(self.target_color_bgr), width=25, height=25, relief=tk.SUNKEN, borderwidth=1)
        self.color_preview.pack(pady=5)

        # Image Target UI
        tk.Button(self.image_frame, text="Take Screenshot", command=self.take_screenshot, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack()
        self.template_dropdown = tk.OptionMenu(self.image_frame, self.template_var, "")
        self.template_dropdown.pack(pady=5)
        self.update_template_list()


        # Action
        action_frame = tk.LabelFrame(self, text="3. Choose Action", bg=self.master.bg_color, fg=self.master.text_color, padx=5, pady=5)
        action_frame.pack(pady=10, padx=10, fill="x")
        tk.Radiobutton(action_frame, text="Click", variable=self.action_type, value="Click", command=self.on_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")
        tk.Radiobutton(action_frame, text="Type", variable=self.action_type, value="Type", command=self.on_action_change, bg=self.master.bg_color, fg=self.master.text_color, selectcolor=self.master.widget_bg_color).pack(anchor="w")
        self.type_entry = tk.Entry(action_frame, textvariable=self.text_to_type, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT)

        # Save/Cancel
        button_frame = tk.Frame(self, bg=self.master.bg_color)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="Save Step", command=self.on_save, bg=self.master.button_color, fg=self.master.button_text_color, relief=tk.FLAT).pack(side="left", padx=10)
        tk.Button(button_frame, text="Cancel", command=self.destroy, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT).pack(side="left", padx=10)

        self.on_mode_change()
        self.on_action_change()

    def on_mode_change(self):
        if self.detection_mode.get() == "Color":
            self.image_frame.pack_forget()
            self.color_frame.pack(pady=10, padx=10, fill="x")
        else:
            self.color_frame.pack_forget()
            self.image_frame.pack(pady=10, padx=10, fill="x")

    def on_action_change(self):
        if self.action_type.get() == "Type":
            self.type_entry.pack(fill="x", padx=5, pady=5)
        else:
            self.type_entry.pack_forget()

    def on_save(self):
        step = {
            "window_title": self.target_window_title.get(),
            "detection_mode": self.detection_mode.get(),
            "action_type": self.action_type.get(),
            "action_params": {},
            "detection_target": None,
            "detection_target_name": ""
        }
        if step['action_type'] == 'Type':
            step['action_params']['text'] = self.text_to_type.get()

        if step['detection_mode'] == 'Color':
            step['detection_target'] = self.target_color_bgr
            step['detection_target_name'] = self.master._bgr_to_hex(self.target_color_bgr)
        else: # Image
            target_name = self.template_var.get()
            step['detection_target'] = os.path.join("templates", target_name)
            step['detection_target_name'] = target_name

        self.master.on_step_saved(step, self.index)
        self.destroy()

    # These methods now act as proxies to the main App's tools
    def select_window(self): self.master.open_window_selector(parent=self)
    def on_window_selected(self, title): self.target_window_title.set(title)
    def sample_color(self): self.master.open_color_sampler(parent=self)
    def on_color_sampled(self, bgr):
        self.target_color_bgr = bgr
        self.color_preview.config(bg=self.master._bgr_to_hex(bgr))
    def take_screenshot(self): self.master.open_screenshot_taker(parent=self)
    def on_screenshot_taken(self, image):
        self.master.on_screenshot_taken(image, parent=self)
        self.update_template_list()

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

# ... (The other helper classes like WindowSelector, ColorSampler etc go here) ...
# Need to update them to handle the 'parent' argument if they need to be modal to the StepEditor

if __name__ == "__main__":
    app = App()
    app.mainloop()
