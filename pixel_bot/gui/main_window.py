import json
import logging
import os
import time
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import copy

from pynput import keyboard

from ..core.execution_engine import ExecutionEngine
from ..core.variable_manager import VariableManager
from ..core.template_manager import TemplateManager
from ..utils.logger import setup_logging
from ..utils.font_manager import FontManager
from ..utils.settings_manager import SettingsManager
from .dialogs import HotkeyChangeDialog
from .step_editor import StepEditor
from .window_selector import WindowSelector
from tkinter import messagebox


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pixel Bot")
        self.settings_manager = SettingsManager()
        self.geometry("1000x900")

        # --- Color Theme ---
        self.sleek_blue_theme = {
            "bg_color": "#1a1625",           # Changed from #0A192F
            "widget_bg_color": "#252339",    # Changed from #1E3A5F
            "text_color": "#e2e8f0",        # Changed from #E6F1FF
            "accent_color": "#10b981",       # Changed from #64FFDA
            "button_color": "#3b82f6",       # Changed from #007BFF
            "button_text_color": "#ffffff"   # Keep same
        }
        # For now, we'll just have one theme. We can add a light theme later if needed.
        self.dark_theme = self.sleek_blue_theme
        self.light_theme = self.sleek_blue_theme
        self._configure_theme()
        self.configure(bg=self.bg_color)

        self.font_manager = FontManager()

        # --- App State ---
        self.running = False
        self.scan_job = None
        self.hotkey_listener = None
        self.hotkey_str = self.settings_manager.get_setting('hotkey')
        self.action_sequence = []
        self.variables = {} # For the new variable system
        self.execution_stack = [] # (sequence, index)
        self.conditional_loop_retry_counts = {}
        self.step_retry_counts = {} # To track retries on a per-step basis
        self.time_condition_executed = set() # To prevent re-triggering
        self.loop_counters = {} # To track 'repeat x times' loops
        self.max_execution_depth = 1000
        self.execution_depth = 0
        self.toggling = False # Debounce flag for hotkey
        self.hide_window_var = tk.BooleanVar(value=self.settings_manager.get_setting('hide_bot_default'))
        self.dry_run_var = tk.BooleanVar(value=False)
        self.target_window_title = tk.StringVar()
        self.target_window_title.set("") # Set to empty string initially
        self.template_map = {}

        # --- Main Layout Frames ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1, uniform="group1")
        main_frame.columnconfigure(1, weight=1, uniform="group1")
        main_frame.rowconfigure(0, weight=1)

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        # --- WIDGET CREATION (Right Panel) ---
        self.log_area = scrolledtext.ScrolledText(right_frame, width=45, height=10, relief=tk.FLAT, insertbackground=self.text_color)
        self.log_area.grid(row=0, column=0, sticky="nsew")
        right_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        # --- Logging Setup ---
        setup_logging(self.log_area)

        # --- Core Logic ---
        self.variable_manager = VariableManager(self.variables, logging.info)
        self.execution_engine = ExecutionEngine(self)
        self.template_manager = TemplateManager()
        self.template_manager.load_templates()


        # Ensure templates directory exists
        if not os.path.exists("pixel_bot/templates"):
            os.makedirs("pixel_bot/templates")

        # --- WIDGET CREATION (Left Panel) ---
        self.style = ttk.Style()
        self.style.theme_use('default')
        self._apply_custom_styles()


        notebook = ttk.Notebook(left_frame, style='TNotebook')
        notebook.pack(expand=True, fill='both')

        main_tab = ttk.Frame(notebook, padding="10")
        templates_tab = ttk.Frame(notebook, padding="10")
        settings_tab = ttk.Frame(notebook, padding="10")

        notebook.add(main_tab, text='Main')
        notebook.add(templates_tab, text='Templates')
        notebook.add(settings_tab, text='Settings')


        # --- Main Tab Content ---
        main_tab.columnconfigure(0, weight=1)
        main_tab.rowconfigure(0, weight=3) # Make the sequence frame expandable
        main_tab.rowconfigure(4, weight=2) # Make the validation frame expandable

        # --- Templates Tab Content ---
        self.setup_templates_tab(templates_tab)

        # --- Sequence Editor UI ---
        sequence_frame = ttk.LabelFrame(main_tab, text="Action Sequence", padding="10")
        sequence_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        sequence_frame.columnconfigure(0, weight=1)
        sequence_frame.rowconfigure(1, weight=1)

        # Frame for Save/Load buttons
        file_io_frame = ttk.Frame(sequence_frame)
        file_io_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Button(file_io_frame, text="Load Sequence", command=self.load_sequence).pack(side="left", padx=(0,5))
        ttk.Button(file_io_frame, text="Save Sequence", command=self.save_sequence).pack(side="left")

        list_container = ttk.Frame(sequence_frame)
        list_container.grid(row=1, column=0, columnspan=2, sticky="nsew")
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)

        self.sequence_listbox = tk.Listbox(
            list_container,
            bg=self.widget_bg_color,
            fg=self.text_color,
            relief=tk.FLAT,
            height=10,
            selectbackground=self.accent_color,    # Green selection
            selectforeground=self.bg_color,        # Dark text on green
            activestyle='none',                    # Remove default active style
            borderwidth=0,                         # Remove border
            highlightthickness=1,                  # Add subtle highlight
            highlightcolor=self.accent_color,      # Green highlight on focus
            highlightbackground=self.widget_bg_color,
            font=self.font_manager.fonts["primary"]  # Use consistent font
        )
        self.sequence_listbox.grid(row=0, column=0, sticky="nsew")
        self.sequence_listbox.bind("<<ListboxSelect>>", self.on_sequence_select)

        seq_button_frame = ttk.Frame(list_container)
        seq_button_frame.grid(row=0, column=1, sticky="ns", padx=(5,0))
        self.add_step_button = ttk.Button(seq_button_frame, text="Add", command=self.add_step, state=tk.DISABLED)
        self.add_step_button.pack(pady=3, fill="x", padx=2)
        self.edit_step_button = ttk.Button(seq_button_frame, text="Edit", command=self.edit_step, state=tk.DISABLED)
        self.edit_step_button.pack(pady=3, fill="x", padx=2)
        self.move_up_button = ttk.Button(seq_button_frame, text="Move Up", command=self.move_step_up, state=tk.DISABLED)
        self.move_up_button.pack(pady=3, fill="x", padx=2)
        self.move_down_button = ttk.Button(seq_button_frame, text="Move Down", command=self.move_step_down, state=tk.DISABLED)
        self.move_down_button.pack(pady=3, fill="x", padx=2)
        self.remove_step_button = ttk.Button(seq_button_frame, text="Remove", command=self.remove_step, state=tk.DISABLED)
        self.remove_step_button.pack(pady=3, fill="x", padx=2)

        # --- Final Controls ---
        controls_frame = ttk.LabelFrame(main_tab, text="Global Target", padding="10")
        controls_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.target_window_label = ttk.Label(controls_frame, textvariable=self.target_window_title, wraplength=380, justify="left", style="Card.TLabel")
        self.target_window_label.pack(pady=5, fill="x", expand=True, ipady=5)
        ttk.Button(controls_frame, text="Change Target Window", command=self.prompt_for_window_selection).pack(pady=(10,5))

        # --- Most Loaded Sequences ---
        most_loaded_frame = ttk.LabelFrame(main_tab, text="Frequently Used", padding="10")
        most_loaded_frame.grid(row=2, column=0, sticky="ew")
        self.most_loaded_container = ttk.Frame(most_loaded_frame)
        self.most_loaded_container.pack(fill="x", pady=5)

        bot_controls_frame = ttk.Frame(main_tab)
        bot_controls_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        bot_controls_frame.columnconfigure(0, weight=1)

        self.hide_window_check = ttk.Checkbutton(bot_controls_frame, text="Hide window when bot is running", variable=self.hide_window_var)
        self.hide_window_check.pack()

        self.dry_run_check = ttk.Checkbutton(bot_controls_frame, text="Dry Run (log actions without executing)", variable=self.dry_run_var)
        self.dry_run_check.pack(pady=5)

        self.start_button = ttk.Button(bot_controls_frame, text="Start Bot", command=self.toggle_bot, style="Accent.TButton")
        self.start_button.pack(pady=10)

        # --- Validation Panel ---
        validation_frame = ttk.LabelFrame(main_tab, text="Validation Results", padding="10")
        validation_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        validation_frame.columnconfigure(0, weight=1)
        validation_frame.rowconfigure(0, weight=1)

        self.validation_tree = ttk.Treeview(validation_frame, height=7, columns=("Severity", "Description"), show="headings")
        self.validation_tree.heading("Severity", text="Severity")
        self.validation_tree.heading("Description", text="Description")
        self.validation_tree.column("Severity", width=80, anchor='w')
        self.validation_tree.column("Description", width=300, anchor='w')
        self.validation_tree.grid(row=0, column=0, sticky="nsew", pady=(0,5))

        # Add tags for coloring
        self.validation_tree.tag_configure('error', foreground='red')
        self.validation_tree.tag_configure('warning', foreground='orange')
        self.validation_tree.tag_configure('suggestion', foreground='lightblue')

        ttk.Button(validation_frame, text="Validate Sequence", command=self.run_full_validation).grid(row=1, column=0, sticky="w")

        # --- Settings Tab Content ---
        settings_content_frame = ttk.Frame(settings_tab)
        settings_content_frame.pack(fill="both", expand=True)

        # --- General Settings ---
        general_frame = ttk.LabelFrame(settings_content_frame, text="General", padding="10")
        general_frame.pack(fill="x", pady=5, anchor="n")

        self.hide_bot_default_var = tk.BooleanVar(value=self.settings_manager.get_setting('hide_bot_default'))
        hide_bot_check = ttk.Checkbutton(general_frame, text="Hide window by default when bot is running", variable=self.hide_bot_default_var, command=self.save_hide_bot_default)
        hide_bot_check.pack(anchor="w", padx=5, pady=2)

        # --- Appearance Settings ---
        # Theme selection is removed as we now have a single, unified theme.

        # --- Image Matching Settings ---
        matching_frame = ttk.LabelFrame(settings_content_frame, text="Image Matching", padding="10")
        matching_frame.pack(fill="x", pady=5, anchor="n")

        self.similarity_threshold_var = tk.DoubleVar(value=self.settings_manager.get_setting('image_similarity_threshold'))

        threshold_inner_frame = ttk.Frame(matching_frame)
        threshold_inner_frame.pack(fill="x", pady=2)

        ttk.Label(threshold_inner_frame, text="Similarity Threshold:").pack(side="left", padx=5)
        self.similarity_label_var = tk.StringVar(value=f"{self.similarity_threshold_var.get():.2f}")
        ttk.Label(threshold_inner_frame, textvariable=self.similarity_label_var, style="Card.TLabel", width=5).pack(side="left")

        similarity_slider = ttk.Scale(
            threshold_inner_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.similarity_threshold_var,
            command=self.save_similarity_threshold,
        )
        similarity_slider.pack(side="left", fill="x", expand=True, padx=5)


        # --- Hotkey Settings ---
        hotkey_frame = ttk.LabelFrame(settings_content_frame, text="Hotkey", padding="10")
        hotkey_frame.pack(fill="x", pady=5, anchor="n")

        hotkey_inner_frame = ttk.Frame(hotkey_frame)
        hotkey_inner_frame.pack(fill="x", pady=2)
        ttk.Label(hotkey_inner_frame, text="Start/Stop Hotkey:").pack(side="left", padx=5)
        self.hotkey_label_var = tk.StringVar(value=self.settings_manager.get_setting('hotkey'))
        ttk.Label(hotkey_inner_frame, textvariable=self.hotkey_label_var, style="Card.TLabel", padding=(10, 5), width=12, anchor="center").pack(side="left")
        self.change_hotkey_button = ttk.Button(hotkey_inner_frame, text="Change...", command=self.change_hotkey)
        self.change_hotkey_button.pack(side="left", padx=5)

        # --- Default Wait Times UI ---
        self.wait_frame = ttk.LabelFrame(settings_content_frame, text="Default Post-Action Wait", padding="10")
        self.wait_frame.pack(fill="x", pady=5, anchor="n")

        default_wait_settings = self.settings_manager.get_setting('default_wait_times')
        self.default_wait_type = tk.StringVar(value=default_wait_settings.get('type', 'Fixed'))
        self.default_fixed_wait = tk.StringVar(value=str(default_wait_settings.get('fixed_time', 1)))
        self.default_min_wait = tk.StringVar(value=str(default_wait_settings.get('min_time', 1)))
        self.default_max_wait = tk.StringVar(value=str(default_wait_settings.get('max_time', 2)))

        wait_type_frame = ttk.Frame(self.wait_frame)
        ttk.Radiobutton(wait_type_frame, text="Fixed", variable=self.default_wait_type, value="Fixed", command=self.on_default_wait_type_change).pack(side="left")
        ttk.Radiobutton(wait_type_frame, text="Random", variable=self.default_wait_type, value="Random", command=self.on_default_wait_type_change).pack(side="left")
        wait_type_frame.pack(fill="x", pady=(0,5))

        self.default_fixed_wait_frame = ttk.Frame(self.wait_frame)
        ttk.Label(self.default_fixed_wait_frame, text="Default Fixed Wait (sec):").pack(side="left", padx=5)
        ttk.Entry(self.default_fixed_wait_frame, textvariable=self.default_fixed_wait, width=7).pack(side="left")

        self.default_random_wait_frame = ttk.Frame(self.wait_frame)
        ttk.Label(self.default_random_wait_frame, text="Min (sec):").pack(side="left", padx=5)
        ttk.Entry(self.default_random_wait_frame, textvariable=self.default_min_wait, width=7).pack(side="left")
        ttk.Label(self.default_random_wait_frame, text="Max (sec):").pack(side="left", padx=(10,5))
        ttk.Entry(self.default_random_wait_frame, textvariable=self.default_max_wait, width=7).pack(side="left")

        ttk.Button(self.wait_frame, text="Save Default Waits", command=self.save_default_wait_times).pack(pady=(10,0))

        self.on_default_wait_type_change()

        logging.info("Welcome! Please select a target window to begin.")
        try:
            # Attempt to get local timezone for user-friendliness
            local_tz = time.tzname[time.daylight] if time.daylight and len(time.tzname) > 1 else time.tzname[0]
            logging.info(f"Bot's current time is {time.strftime('%Y-%m-%d %H:%M:%S')} ({local_tz}). Time conditions use the bot's system clock.")
        except Exception:
            # Fallback for environments where tzname might not be available
            logging.info(f"Bot's current time is {time.strftime('%Y-%m-%d %H:%M:%S')}. Time conditions use the bot's system clock.")
        self.update_most_loaded_list()
        self.after(200, lambda: self.prompt_for_window_selection(is_splash=True))

        self.start_persistent_hotkey_listener()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        logging.info("Closing application and stopping listener...")
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.destroy()

    def _configure_theme(self):
        theme = self.settings_manager.get_setting('theme')
        colors = self.dark_theme if theme == 'dark' else self.light_theme

        self.bg_color = colors['bg_color']
        self.widget_bg_color = colors['widget_bg_color']
        self.text_color = colors['text_color']
        self.button_color = colors['button_color']
        self.button_text_color = colors['button_text_color']

    def _apply_custom_styles(self):
        theme = self.settings_manager.get_setting('theme')
        colors = self.dark_theme if theme == 'dark' else self.light_theme
        fonts = self.font_manager.fonts

        # General widget styling
        self.style.configure('TFrame', background=colors['bg_color'])
        self.style.configure('TLabel', background=colors['bg_color'], foreground=colors['text_color'], padding=5, font=fonts["primary"])

        # In _apply_custom_styles method:
        self.style.configure('TButton',
            background=colors['widget_bg_color'],
            foreground=colors['text_color'],
            font=self.font_manager.fonts["button"],
            relief='flat',
            borderwidth=1,
            focuscolor='none')

        self.style.map('TButton',
            background=[
                ('active', colors['button_color']),      # Hover state
                ('pressed', colors['accent_color'])      # Pressed state
            ],
            bordercolor=[
                ('active', colors['accent_color']),      # Hover border
                ('focus', colors['accent_color'])        # Focus border
            ])

        self.style.configure('TCheckbutton', background=colors['bg_color'], foreground=colors['text_color'], font=fonts["primary"])
        self.style.map('TCheckbutton', background=[('active', colors['bg_color'])])
        self.style.configure('TRadiobutton', background=colors['bg_color'], foreground=colors['text_color'], font=fonts["primary"])
        self.style.map('TRadiobutton', background=[('active', colors['bg_color'])])

        self.style.configure('TEntry',
            fieldbackground=colors['widget_bg_color'],
            foreground=colors['text_color'],
            insertcolor=colors['text_color'],
            relief='flat',
            borderwidth=1)

        self.style.map('TEntry',
            focuscolor=[('focus', colors['accent_color'])])

        self.style.configure('TLabelFrame',
            background=colors['bg_color'],
            relief='flat',
            borderwidth=1,
            lightcolor=colors['widget_bg_color'],       # Use widget bg as border
            darkcolor=colors['widget_bg_color'])        # Use widget bg as border

        self.style.configure('TLabelFrame.Label', background=colors['bg_color'], foreground=colors['text_color'], font=fonts["heading"])


        # Special "Card" style for labels that need a background
        self.style.configure("Card.TLabel", background=colors['widget_bg_color'], relief=tk.SOLID, borderwidth=1, font=fonts["primary"])

        # Accent Button (Start Bot)
        self.style.configure("Accent.TButton",
            background=colors['accent_color'],
            foreground=colors['button_text_color'],     # Use existing white
            font=self.font_manager.fonts["button"],
            relief='flat',
            borderwidth=0,
            focuscolor='none')

        self.style.map("Accent.TButton",
            background=[
                ('active', colors['button_color']),      # Hover to blue
                ('pressed', colors['accent_color'])      # Keep same on press
            ])

        # Notebook styling
        self.style.configure('TNotebook', background=colors['bg_color'], borderwidth=0)
        self.style.configure('TNotebook.Tab', background=colors['bg_color'], foreground=colors['text_color'], padding=[10, 5], font=fonts["primary"])
        self.style.map('TNotebook.Tab', background=[('selected', colors['widget_bg_color'])], foreground=[('selected', colors['accent_color'])])

        # Table/Treeview Styling (if applicable)
        self.style.configure('Treeview',
            background=colors['widget_bg_color'],
            foreground=colors['text_color'],
            fieldbackground=colors['widget_bg_color'],
            relief='flat',
            borderwidth=1)

        self.style.configure('Treeview.Heading',
            background=colors['bg_color'],              # Use main background
            foreground=colors['text_color'],            # Use main text color
            relief='flat')


        # Apply background and foreground to the log area specifically
        self.log_area.config(
            bg=colors['widget_bg_color'],
            fg=colors['text_color'],
            font=self.font_manager.fonts["mono"]
        )


    def prompt_for_window_selection(self, is_splash=False):
        logging.info("Prompting for target window selection...")
        WindowSelector(self, is_splash=is_splash)

    def on_window_selected(self, title):
        self.target_window_title.set(title)
        self.add_step_button.state(['!disabled'])
        logging.info(f"Global target window set to: {title}")

    def on_sequence_select(self, event):
        selected_indices = self.sequence_listbox.curselection()
        if selected_indices:
            index = selected_indices[0]
            self.edit_step_button.state(['!disabled'])
            self.remove_step_button.state(['!disabled'])

            # Enable/disable Move Up button
            if index > 0:
                self.move_up_button.state(['!disabled'])
            else:
                self.move_up_button.state(['disabled'])

            # Enable/disable Move Down button
            if index < len(self.action_sequence) - 1:
                self.move_down_button.state(['!disabled'])
            else:
                self.move_down_button.state(['disabled'])
        else:
            self.edit_step_button.state(['disabled'])
            self.remove_step_button.state(['disabled'])
            self.move_up_button.state(['disabled'])
            self.move_down_button.state(['disabled'])

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
        logging.info(f"Removed step {index+1}.")

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
            text = self.format_step_for_display(i + 1, step)
            self.sequence_listbox.insert(tk.END, text)
        self.on_sequence_select(None)

    def save_sequence(self):
        if not self.action_sequence:
            logging.info("Cannot save an empty sequence.")
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
            logging.info(f"Sequence saved to {os.path.basename(filepath)}")
        except Exception as e:
            logging.error(f"Error saving sequence: {e}")

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
            label = ttk.Label(self.most_loaded_container, text=label_text, style="Card.TLabel", anchor="w", cursor="hand2")
            label.pack(fill="x", pady=(0, 2))
            label.bind("<Button-1>", lambda e, path=filepath: self.load_sequence(path))


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
            logging.info(f"Sequence loaded from {os.path.basename(filepath)}")

            # Increment load count and update the list
            self.settings_manager.increment_sequence_load_count(filepath)
            self.update_most_loaded_list()
        except json.JSONDecodeError:
            logging.error("The selected file is not a valid JSON file.")
        except TypeError as e:
            logging.error(f"Error loading sequence: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred while loading: {e}")

    def save_hide_bot_default(self):
        self.settings_manager.set_setting('hide_bot_default', self.hide_bot_default_var.get())
        logging.info("Default 'Hide Bot' setting saved.")

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
        logging.info("Theme changed. Please restart the application for the changes to take full effect.")

    def on_default_wait_type_change(self):
        wait_type = self.default_wait_type.get()
        if wait_type == "Fixed":
            self.default_fixed_wait_frame.pack(fill="x", pady=2)
            self.default_random_wait_frame.pack_forget()
        elif wait_type == "Random":
            self.default_fixed_wait_frame.pack_forget()
            self.default_random_wait_frame.pack(fill="x", pady=2)
        else: # Should not happen with radio buttons
            self.default_fixed_wait_frame.pack_forget()
            self.default_random_wait_frame.pack_forget()

    def save_default_wait_times(self):
        try:
            new_settings = {
                "type": self.default_wait_type.get(),
                "fixed_time": float(self.default_fixed_wait.get()),
                "min_time": float(self.default_min_wait.get()),
                "max_time": float(self.default_max_wait.get())
            }
            if new_settings['min_time'] >= new_settings['max_time']:
                logging.error("Min wait time must be less than max wait time.")
                return

            self.settings_manager.set_setting('default_wait_times', new_settings)
            logging.info("Default wait times saved successfully.")
        except ValueError:
            logging.error("Wait times must be valid numbers.")

    def change_hotkey(self):
        # The listener is persistent now, so we just need to update the string it checks against.
        # The HotkeyChangeDialog will call on_hotkey_changed when a new key is pressed.
        HotkeyChangeDialog(self, self.on_hotkey_changed)

    def on_hotkey_changed(self, new_hotkey_str):
        """Callback from the hotkey dialog to update the hotkey."""
        self.hotkey_str = new_hotkey_str
        self.hotkey_label_var.set(new_hotkey_str)
        self.settings_manager.set_setting('hotkey', new_hotkey_str)
        logging.info(f"Hotkey changed to: {new_hotkey_str.upper()}")

    def on_hotkey_press(self, key):
        """The single callback for the persistent listener."""
        try:
            key_name = None
            if isinstance(key, keyboard.Key):
                key_name = key.name
            elif isinstance(key, keyboard.KeyCode):
                key_name = key.char

            if key_name and key_name.lower() == self.hotkey_str.lower():
                self.after(0, self.toggle_bot)
        except Exception as e:
            logging.error(f"Error processing hotkey press: {e}")

    def start_persistent_hotkey_listener(self):
        """Starts the single, persistent hotkey listener."""
        try:
            self.hotkey_listener = keyboard.Listener(on_press=self.on_hotkey_press)
            self.hotkey_listener.start()
            logging.info("Persistent hotkey listener started.")
        except Exception as e:
            logging.error(f"Failed to start hotkey listener: {e}")
            messagebox.showerror("Hotkey Error", f"Failed to start hotkey listener: {e}\nHotkeys will be disabled.")

    def toggle_bot(self):
        if self.toggling:
            logging.warning("Toggle ignored, already in progress.")
            return

        self.toggling = True

        try:
            if self.running:
                # --- STOPPING THE BOT ---
                self.running = False
                if self.scan_job:
                    self.after_cancel(self.scan_job)
                self.scan_job = None
                self.start_button.config(text="Start Bot")
                logging.info("Bot stopped.")
                if self.hide_window_var.get():
                    self.deiconify()
            else:
                # --- STARTING THE BOT ---
                if not self.action_sequence:
                    logging.info("Cannot start: Action sequence is empty.")
                    self.run_full_validation() # Show "empty" status
                    return

                # Run validation before starting
                validation_result = self.run_full_validation()
                if not validation_result.is_valid:
                    messagebox.showerror("Validation Error", "Cannot start bot. Please fix the critical errors listed in the validation panel.")
                    return

                if validation_result.warnings:
                    if not messagebox.askyesno("Validation Warning", "There are warnings for this sequence that could cause issues.\n\nAre you sure you want to continue?"):
                        return

                self.variables.clear()
                self.execution_stack = [(self.action_sequence, 0)]
                self.conditional_loop_retry_counts.clear()
                self.step_retry_counts.clear()
                self.time_condition_executed.clear()
                self.loop_counters.clear()

                self.running = True
                self.start_button.config(text="Stop Bot")
                logging.info(f"Bot starting... Press '{self.hotkey_str.upper()}' to stop.")
                if self.hide_window_var.get():
                    self.withdraw()
                self.execution_engine.run_scan_loop()
        finally:
            # Simple debounce to prevent too-rapid toggles
            self.after(200, lambda: setattr(self, 'toggling', False))

    def _bgr_to_hex(self, bgr_color):
        b, g, r = bgr_color
        return f"#{r:02x}{g:02x}{b:02x}".upper()

    def setup_templates_tab(self, parent_frame):
        parent_frame.columnconfigure(0, weight=1)
        parent_frame.rowconfigure(0, weight=1)

        # --- Treeview for categories and templates ---
        gallery_frame = ttk.LabelFrame(parent_frame, text="Template Gallery", padding="10")
        gallery_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        gallery_frame.columnconfigure(0, weight=1)
        gallery_frame.rowconfigure(0, weight=1)

        self.template_tree = ttk.Treeview(gallery_frame, show="tree headings", selectmode="browse")
        self.template_tree.heading("#0", text="Name", anchor='w')
        self.template_tree.grid(row=0, column=0, sticky="nsew")
        self.template_tree.bind("<<TreeviewSelect>>", self.on_template_selected)

        # --- Preview Panel ---
        preview_frame = ttk.LabelFrame(parent_frame, text="Template Preview", padding="10")
        preview_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.template_preview_text = scrolledtext.ScrolledText(preview_frame, height=8, wrap=tk.WORD, bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT)
        self.template_preview_text.grid(row=0, column=0, sticky="nsew")
        self.template_preview_text.config(state=tk.DISABLED)

        # --- Controls ---
        template_controls_frame = ttk.Frame(parent_frame)
        template_controls_frame.grid(row=2, column=0, sticky="ew")

        self.insert_template_button = ttk.Button(template_controls_frame, text="Insert Template into Sequence", command=self.insert_selected_template, state=tk.DISABLED)
        self.insert_template_button.pack(pady=5)

        self.populate_template_treeview()

    def populate_template_treeview(self):
        # Clear existing items
        for i in self.template_tree.get_children():
            self.template_tree.delete(i)

        # Create categories
        self.template_map.clear()
        category_nodes = {}
        for category_name in self.template_manager.categories:
            node = self.template_tree.insert("", "end", text=category_name, open=True)
            category_nodes[category_name] = node

        # Add templates to categories
        for template in self.template_manager.templates:
            if template.category in category_nodes:
                parent_node = category_nodes[template.category]

                # Determine status icon
                status_icon = "✓"
                tag = 'valid'
                if not template.validation_result.is_valid:
                    status_icon = "✗"
                    tag = 'error'
                elif template.validation_result.warnings:
                    status_icon = "⚠"
                    tag = 'warning'

                display_name = f"{status_icon} {template.name}"
                item_id = self.template_tree.insert(parent_node, "end", text=display_name, tags=(tag,))
                self.template_map[item_id] = template

        self.template_tree.tag_configure('error', foreground='red')
        self.template_tree.tag_configure('warning', foreground='orange')
        self.template_tree.tag_configure('valid', foreground='green')


    def on_template_selected(self, event):
        selection = self.template_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        template = self.template_map.get(item_id)

        # Check if a template (child node) is selected, not a category
        if template:
            self.template_preview_text.config(state=tk.NORMAL)
            self.template_preview_text.delete('1.0', tk.END)

            preview_content = f"Name: {template.name}\n"
            preview_content += f"Category: {template.category}\n"
            preview_content += f"Difficulty: {template.difficulty}\n"
            preview_content += f"Est. Time: {template.estimated_time}\n\n"
            preview_content += f"Description:\n{template.description}\n"

            # --- Validation Section ---
            preview_content += f"\n--- Validation Status ---\n"
            result = template.validation_result
            if result.is_valid and not result.warnings:
                preview_content += "✓ This template is valid.\n"
            else:
                for error in result.errors:
                    preview_content += f"✗ Error: {error}\n"
                for warning in result.warnings:
                    preview_content += f"⚠ Warning: {warning}\n"

            # --- Steps Section ---
            preview_content += f"\n--- Steps ({len(template.steps)}) ---\n"
            for i, step in enumerate(template.steps):
                preview_content += self.format_step_for_display(i + 1, step) + "\n"

            self.template_preview_text.insert('1.0', preview_content)
            self.template_preview_text.config(state=tk.DISABLED)

            self.insert_template_button.config(state=tk.NORMAL)
        else:
            # It's a category, clear preview and disable button
            self.template_preview_text.config(state=tk.NORMAL)
            self.template_preview_text.delete('1.0', tk.END)
            self.template_preview_text.config(state=tk.DISABLED)
            self.insert_template_button.config(state=tk.DISABLED)

    def insert_selected_template(self):
        selection = self.template_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        template = self.template_map.get(item_id)

        if template:
            # Use deepcopy to ensure templates can be reused without modification issues
            steps_to_insert = copy.deepcopy(template.steps)

            self.action_sequence.extend(steps_to_insert)
            self.update_sequence_listbox()
            logging.info(f"Inserted template '{template.name}' with {len(steps_to_insert)} steps.")

            # Optional: Switch back to the main tab to show the result
            # self.notebook.select(self.main_tab)

    def format_step_for_display(self, number, step):
        """Enhanced step formatting with visual indicators"""
        step_type = step.get('step_type', 'simple')
        action_type = step.get('action_type')

        # Add visual indicators
        icon = "❓" # Default icon
        if step_type == 'simple':
            if action_type == 'Click':
                icon = "🖱️"
            elif action_type == 'Type':
                icon = "⌨️"
            elif action_type == 'Set Variable':
                icon = "📝"
            elif action_type == 'Modify Variable':
                 icon = "📝" # Also fits here
            elif action_type == 'OCR':
                icon = "👁️"
            else:
                icon = "⚡" # For other simple actions like Find Image, etc.
        elif step_type == 'conditional_loop':
            icon = "🔄"
        elif step_type == 'loop':
            icon = "🔄"
        elif step_type == 'time_based_condition':
            icon = "⏱️"
        elif step_type == 'wait':
            icon = "⏱️"
        elif step_type == 'conditional_branch':
            icon = "🔀"

        # Format with icon and better spacing
        text = f"  {icon} {number}: "

        # Existing formatting logic
        if step_type == 'simple':
            if action_type == 'Set Variable':
                params = step.get('action_params', {})
                text += f"Set Var: '{params.get('variable_name', 'N/A')}' = '{params.get('variable_value', 'N/A')}'"
            elif action_type == 'Modify Variable':
                params = step.get('action_params', {})
                text += f"Modify Var: '{params.get('modify_variable_name', 'N/A')}' {params.get('modify_variable_operation', '?')} {params.get('modify_variable_value', '?')}"
            elif action_type == 'OCR':
                params = step.get('action_params', {})
                text += f"OCR to Var: '{params.get('output_variable_name', 'N/A')}'"
            else:
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
        elif step_type == 'time_based_condition':
            time_cond = step.get('time_condition', {})
            hour = time_cond.get('hour', '??')
            minute = time_cond.get('minute', '??')
            text += f"TIME CONDITION: at {hour:02d}:{minute:02d}"
        elif step_type == 'wait':
            duration = step.get('duration', 0)
            text += f"Wait for {duration:.2f} seconds"
        elif step_type == 'conditional_branch':
            condition = step.get('condition', {})
            var = condition.get('variable', '?').replace('{', '').replace('}', '')
            op = condition.get('operator', '?')
            val = condition.get('value', '?')
            text += f"IF {var} {op} {val}"
        else:
            text += "Unknown Step Type"

        return text

    def run_full_validation(self):
        """Runs the validator on the current sequence and updates the UI."""
        if not self.action_sequence:
            logging.info("Validation: Sequence is empty.")
            self.populate_validation_tree(None)
            return None

        logging.info("Running full sequence validation...")
        # Use the validator from the execution engine instance
        result = self.execution_engine.validator.validate_sequence(self.action_sequence)
        self.populate_validation_tree(result)
        return result

    def populate_validation_tree(self, result):
        """Clears and populates the validation results treeview."""
        for i in self.validation_tree.get_children():
            self.validation_tree.delete(i)

        if result is None:
            self.validation_tree.insert("", "end", values=("Info", "Sequence is empty."), tags=('suggestion',))
            return

        if result.is_valid and not result.warnings and not result.suggestions:
            self.validation_tree.insert("", "end", values=("Success", "No issues found."), tags=('success',))
            self.validation_tree.tag_configure('success', foreground='green')
            return

        for error in result.errors:
            self.validation_tree.insert("", "end", values=("Error", error), tags=('error',))
        for warning in result.warnings:
            self.validation_tree.insert("", "end", values=("Warning", warning), tags=('warning',))
        for suggestion in result.suggestions:
            self.validation_tree.insert("", "end", values=("Suggestion", suggestion), tags=('suggestion',))
