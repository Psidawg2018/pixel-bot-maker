import json
import logging
import os
import time
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import copy

from pynput import keyboard

from ..core.execution_engine import ExecutionEngine
from ..core.preview_engine import ScriptPreviewEngine
from ..core.variable_manager import VariableManager
from ..core.template_manager import TemplateManager
from ..utils.logger import setup_logging
from ..utils.font_manager import FontManager
from ..utils.settings_manager import SettingsManager
from .dialogs import HotkeyChangeDialog
from .step_editor import StepEditor
from .window_selector import WindowSelector
from .preview_dialog import PreviewDialog
from .preview_overlay import PreviewOverlay
from tkinter import messagebox


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pixel Bot")
        self.settings_manager = SettingsManager()
        self.geometry("1000x900")

        # --- Color Theme ---
        self.sleek_blue_theme = {
            "bg_color": "#1a1a1a",           # Main background (darker)
            "widget_bg_color": "#2d2d2d",    # Card backgrounds
            "card_header": "#353535",        # Card title bars
            "border_color": "#404040",       # Subtle borders
            "text_color": "#ffffff",         # Primary text
            "text_secondary": "#cccccc",     # Secondary text
            "accent_color": "#00d4aa",       # Green accent (success)
            "button_color": "#4a9eff",       # Blue buttons
            "warning_color": "#ffa500",      # Orange warnings
            "danger_color": "#ff4757",       # Red danger
            "button_text_color": "#ffffff"
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
        main_frame = tk.Frame(self, bg=self.bg_color)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        self.create_modern_header(main_frame)

        # --- Scrollable Content Area ---
        canvas_container = tk.Frame(main_frame, bg=self.bg_color)
        canvas_container.pack(fill='both', expand=True, pady=(20, 0))

        canvas = tk.Canvas(canvas_container, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.bg_color)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas = canvas # Save reference for scrolling

        # The old content_frame is now the scrollable_frame
        content_frame = scrollable_frame

        left_frame = tk.Frame(content_frame, bg=self.bg_color)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        right_frame = tk.Frame(content_frame, bg=self.bg_color)
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))

        # --- WIDGET CREATION (Right Panel) ---
        log_content = self.create_modern_card(right_frame, "📝 Log")
        self.log_area = scrolledtext.ScrolledText(log_content, width=45, height=10, relief=tk.FLAT, insertbackground=self.text_color, bg=self.widget_bg_color, fg=self.text_color, bd=0, font=self.font_manager.fonts['mono'])
        self.log_area.pack(fill='both', expand=True, padx=1, pady=1)

        # --- Logging Setup ---
        setup_logging(self.log_area)

        # --- Core Logic ---
        self.variable_manager = VariableManager(self.variables, logging.info)
        self.execution_engine = ExecutionEngine(self)
        self.preview_engine = ScriptPreviewEngine(self)
        self.template_manager = TemplateManager()
        self.template_manager.load_templates()


        # Ensure templates directory exists
        if not os.path.exists("pixel_bot/templates"):
            os.makedirs("pixel_bot/templates")

        # --- WIDGET CREATION (Left Panel) ---
        self.style = ttk.Style()
        self.style.theme_use('default')
        self._apply_custom_styles()


        # The notebook is removed. Content will be placed directly in left_frame or right_frame.
        # We create temporary frames to hold the content of the old tabs.
        # This content will be moved into cards in the next phase.
        templates_tab_content = tk.Frame(self) # Dummy parent for now
        settings_tab_content = tk.Frame(self) # Dummy parent for now


        # --- Main Tab Content (will be moved to cards) ---
        # The content that was in main_tab will now be parented to left_frame or right_frame.
        # --- Templates Tab Content ---
        self.setup_templates_tab(templates_tab_content)

        # --- Action Sequence Panel (Left Frame) ---
        sequence_content = self.create_modern_card(left_frame, "⚡ Action Sequence")

        # Frame for Save/Load buttons
        file_io_frame = tk.Frame(sequence_content, bg=self.widget_bg_color)
        file_io_frame.pack(fill="x", pady=5, padx=10)
        self.create_modern_button(file_io_frame, "Load Sequence", self.load_sequence, self.button_color).pack(side="left", padx=(0,5))
        self.create_modern_button(file_io_frame, "Save Sequence", self.save_sequence, self.button_color).pack(side="left", padx=(0,5))
        preview_btn = self.create_modern_button(
            file_io_frame, "👁️ Preview Sequence",
            self.show_preview_dialog,
            self.button_color
        )
        preview_btn.pack(side="left")

        list_container = tk.Frame(sequence_content, bg=self.widget_bg_color)
        list_container.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # Scrollbar
        scrollbar = tk.Scrollbar(list_container, relief='flat', troughcolor=self.widget_bg_color, bg=self.border_color, activebackground=self.card_header)
        scrollbar.pack(side='right', fill='y')

        self.sequence_listbox = tk.Listbox(
            list_container,
            bg=self.card_header, # Darker background like mockup
            fg=self.text_color,
            relief=tk.FLAT,
            height=10,
            selectbackground=self.accent_color,
            selectforeground="#000000", # Black text on selection
            activestyle='none',
            borderwidth=0,
            highlightthickness=0,
            font=self.font_manager.fonts["primary"],
            yscrollcommand=scrollbar.set
        )
        self.sequence_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.sequence_listbox.yview)

        self.sequence_listbox.bind("<<ListboxSelect>>", self.on_sequence_select)

        seq_button_frame = tk.Frame(list_container, bg=self.widget_bg_color)
        seq_button_frame.pack(side='right', fill='y', padx=(5,0))
        self.add_step_button = self.create_modern_button(seq_button_frame, "➕ Add", self.add_step, self.button_color)
        self.add_step_button.pack(pady=3, fill="x", padx=2)
        self.edit_step_button = self.create_modern_button(seq_button_frame, "✏️ Edit", self.edit_step, self.button_color)
        self.edit_step_button.pack(pady=3, fill="x", padx=2)
        self.move_up_button = self.create_modern_button(seq_button_frame, "🔼 Up", self.move_step_up, self.button_color)
        self.move_up_button.pack(pady=3, fill="x", padx=2)
        self.move_down_button = self.create_modern_button(seq_button_frame, "🔽 Down", self.move_step_down, self.button_color)
        self.move_down_button.pack(pady=3, fill="x", padx=2)
        self.remove_step_button = self.create_modern_button(seq_button_frame, "🗑️ Remove", self.remove_step, self.sleek_blue_theme['danger_color'])
        self.remove_step_button.pack(pady=3, fill="x", padx=2)

        # The state of these buttons is managed in on_sequence_select, which needs to be updated
        # to handle tk.Button state. For now, I'll disable them manually after creation.
        self.add_step_button.config(state=tk.DISABLED)
        self.edit_step_button.config(state=tk.DISABLED)
        self.move_up_button.config(state=tk.DISABLED)
        self.move_down_button.config(state=tk.DISABLED)
        self.remove_step_button.config(state=tk.DISABLED)

        # --- Bot Controls Panel (Left Frame) ---
        controls_content = self.create_modern_card(left_frame, "🎮 Bot Controls")

        self.hide_window_check = tk.Checkbutton(controls_content, text="Hide window when bot is running",
                                variable=self.hide_window_var,
                                bg=self.widget_bg_color, fg=self.text_color,
                                selectcolor=self.card_header,
                                activebackground=self.widget_bg_color,
                                activeforeground=self.text_color,
                                font=self.font_manager.fonts["primary"],
                                relief='flat', highlightthickness=0)
        self.hide_window_check.pack(anchor='w', padx=15, pady=(10, 5))

        self.dry_run_check = tk.Checkbutton(controls_content, text="Dry Run (log actions without executing)",
                               variable=self.dry_run_var,
                               bg=self.widget_bg_color, fg=self.text_color,
                               selectcolor=self.card_header,
                               activebackground=self.widget_bg_color,
                               activeforeground=self.text_color,
                               font=self.font_manager.fonts["primary"],
                               relief='flat', highlightthickness=0)
        self.dry_run_check.pack(anchor='w', padx=15, pady=5)

        bot_button_frame = tk.Frame(controls_content, bg=self.widget_bg_color)
        bot_button_frame.pack(pady=10)

        self.start_button = self.create_modern_button(bot_button_frame, "▶️ Start Bot", self.toggle_bot, self.sleek_blue_theme['accent_color'])
        self.start_button.pack(side="left", ipady=5, ipadx=10, padx=(0, 5))

        self.live_preview_button = self.create_modern_button(bot_button_frame, "▶️ Live Preview", self.start_live_preview, self.button_color)
        self.live_preview_button.pack(side="left", ipady=5, ipadx=10, padx=(5, 0))


        # --- Global Target Panel (Right Frame) ---
        target_content = self.create_modern_card(right_frame, "🎯 Global Target")
        self.target_window_label = ttk.Label(target_content, textvariable=self.target_window_title, wraplength=380, justify="left", style="Card.TLabel")
        self.target_window_label.pack(pady=5, fill="x", expand=True, ipady=5, padx=15)
        self.create_modern_button(target_content, "🔄 Change Target Window", self.prompt_for_window_selection, self.button_color).pack(pady=(10,5))

        # --- Validation Panel (Right Frame) ---
        validation_content = self.create_modern_card(right_frame, "✅ Validation Results")

        tree_container = tk.Frame(validation_content, bg=self.widget_bg_color)
        tree_container.pack(fill='both', expand=True, padx=15, pady=(10,0))

        tree_scroll = ttk.Scrollbar(tree_container, orient='vertical')

        self.validation_tree = ttk.Treeview(tree_container, height=7, columns=("Severity", "Description"), show="headings", yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=self.validation_tree.yview)

        self.validation_tree.heading("Severity", text="Severity")
        self.validation_tree.heading("Description", text="Description")
        self.validation_tree.column("Severity", width=100, minwidth=80)
        self.validation_tree.column("Description", width=300, minwidth=200)

        self.validation_tree.pack(side='left', fill='both', expand=True)
        tree_scroll.pack(side='right', fill='y')

        # Add tags for coloring
        self.validation_tree.tag_configure('error', foreground=self.sleek_blue_theme['danger_color'])
        self.validation_tree.tag_configure('warning', foreground=self.sleek_blue_theme['warning_color'])
        self.validation_tree.tag_configure('suggestion', foreground=self.sleek_blue_theme['text_secondary'])

        self.create_modern_button(validation_content, "🔍 Validate Sequence", self.run_full_validation, self.sleek_blue_theme['warning_color']).pack(pady=10)

        # --- Most Loaded Sequences (Left Frame) ---
        most_loaded_content = self.create_modern_card(left_frame, "⭐ Frequently Used")
        self.most_loaded_container = tk.Frame(most_loaded_content, bg=self.widget_bg_color)
        self.most_loaded_container.pack(fill="x", expand=True, pady=5, padx=15)

        # --- Templates Card (Right Frame) ---
        self.templates_card_content = self.create_modern_card(right_frame, "📚 Templates")
        self.setup_templates_tab(self.templates_card_content)

        # --- Settings Card (Right Frame) ---
        self.settings_card_content = self.create_modern_card(right_frame, "⚙️ Settings")

        # The various settings are now created in sub-frames parented to the card's content area
        settings_inner_frame = tk.Frame(self.settings_card_content, bg=self.widget_bg_color)
        settings_inner_frame.pack(fill='both', expand=True, padx=15, pady=10)

        # --- General Settings ---
        ttk.Label(settings_inner_frame, text="General", font=self.font_manager.fonts["heading"]).pack(anchor="w", pady=(0, 5))
        self.hide_bot_default_var = tk.BooleanVar(value=self.settings_manager.get_setting('hide_bot_default'))
        hide_bot_check = tk.Checkbutton(settings_inner_frame, text="Hide window by default when bot is running",
                                        variable=self.hide_bot_default_var, command=self.save_hide_bot_default,
                                        bg=self.widget_bg_color, fg=self.text_color,
                                        selectcolor=self.card_header,
                                        activebackground=self.widget_bg_color,
                                        activeforeground=self.text_color,
                                        font=self.font_manager.fonts["primary"],
                                        relief='flat', highlightthickness=0)
        hide_bot_check.pack(anchor="w", padx=5, pady=2)

        # --- Image Matching Settings ---
        ttk.Label(settings_inner_frame, text="Image Matching", font=self.font_manager.fonts["heading"]).pack(anchor="w", pady=(10, 5))
        self.similarity_threshold_var = tk.DoubleVar(value=self.settings_manager.get_setting('image_similarity_threshold'))
        threshold_inner_frame = tk.Frame(settings_inner_frame, bg=self.widget_bg_color)
        threshold_inner_frame.pack(fill="x", pady=2)
        ttk.Label(threshold_inner_frame, text="Similarity Threshold:").pack(side="left", padx=5)
        self.similarity_label_var = tk.StringVar(value=f"{self.similarity_threshold_var.get():.2f}")
        ttk.Label(threshold_inner_frame, textvariable=self.similarity_label_var, style="Card.TLabel", width=5).pack(side="left")
        similarity_slider = ttk.Scale(
            threshold_inner_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL,
            variable=self.similarity_threshold_var, command=self.save_similarity_threshold,
        )
        similarity_slider.pack(side="left", fill="x", expand=True, padx=5)

        # --- Hotkey Settings ---
        ttk.Label(settings_inner_frame, text="Hotkey", font=self.font_manager.fonts["heading"]).pack(anchor="w", pady=(10, 5))
        hotkey_inner_frame = tk.Frame(settings_inner_frame, bg=self.widget_bg_color)
        hotkey_inner_frame.pack(fill="x", pady=2)
        ttk.Label(hotkey_inner_frame, text="Start/Stop Hotkey:").pack(side="left", padx=5)
        self.hotkey_label_var = tk.StringVar(value=self.settings_manager.get_setting('hotkey'))
        ttk.Label(hotkey_inner_frame, textvariable=self.hotkey_label_var, style="Card.TLabel", padding=(10, 5), width=12, anchor="center").pack(side="left")
        self.change_hotkey_button = self.create_modern_button(hotkey_inner_frame, "Change...", self.change_hotkey, self.button_color)
        self.change_hotkey_button.pack(side="left", padx=5)

        # --- Default Wait Times UI ---
        ttk.Label(settings_inner_frame, text="Default Post-Action Wait", font=self.font_manager.fonts["heading"]).pack(anchor="w", pady=(10, 5))
        self.wait_frame = tk.Frame(settings_inner_frame, bg=self.widget_bg_color)
        self.wait_frame.pack(fill="x", pady=2)
        default_wait_settings = self.settings_manager.get_setting('default_wait_times')
        self.default_wait_type = tk.StringVar(value=default_wait_settings.get('type', 'Fixed'))
        self.default_fixed_wait = tk.StringVar(value=str(default_wait_settings.get('fixed_time', 1)))
        self.default_min_wait = tk.StringVar(value=str(default_wait_settings.get('min_time', 1)))
        self.default_max_wait = tk.StringVar(value=str(default_wait_settings.get('max_time', 2)))
        wait_type_frame = tk.Frame(self.wait_frame, bg=self.widget_bg_color)
        ttk.Radiobutton(wait_type_frame, text="Fixed", variable=self.default_wait_type, value="Fixed", command=self.on_default_wait_type_change).pack(side="left")
        ttk.Radiobutton(wait_type_frame, text="Random", variable=self.default_wait_type, value="Random", command=self.on_default_wait_type_change).pack(side="left")
        wait_type_frame.pack(fill="x", pady=(0,5))
        self.default_fixed_wait_frame = tk.Frame(self.wait_frame, bg=self.widget_bg_color)
        ttk.Label(self.default_fixed_wait_frame, text="Default Fixed Wait (sec):").pack(side="left", padx=5)
        ttk.Entry(self.default_fixed_wait_frame, textvariable=self.default_fixed_wait, width=7).pack(side="left")
        self.default_random_wait_frame = tk.Frame(self.wait_frame, bg=self.widget_bg_color)
        ttk.Label(self.default_random_wait_frame, text="Min (sec):").pack(side="left", padx=5)
        ttk.Entry(self.default_random_wait_frame, textvariable=self.default_min_wait, width=7).pack(side="left")
        ttk.Label(self.default_random_wait_frame, text="Max (sec):").pack(side="left", padx=(10,5))
        ttk.Entry(self.default_random_wait_frame, textvariable=self.default_max_wait, width=7).pack(side="left")
        self.create_modern_button(self.wait_frame, "Save Default Waits", self.save_default_wait_times, self.button_color).pack(pady=(10,0))

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

    def create_modern_card(self, parent, title, height=None):
        """Create a modern card-style container matching the mockup"""
        card = tk.Frame(parent, bg=self.widget_bg_color, relief='flat', bd=0)
        # Use fill='x' and expand=False (default) to allow vertical stacking
        card.pack(fill='x', pady=(0, 15))

        # Add subtle border effect
        border_frame = tk.Frame(card, bg=self.border_color, height=1)
        border_frame.pack(fill='x', side='top')

        # Title bar
        title_frame = tk.Frame(card, bg=self.card_header, height=40)
        title_frame.pack(fill='x', padx=1, pady=(1, 0))
        title_frame.pack_propagate(False)

        title_label = tk.Label(title_frame, text=title,
                              bg=self.card_header, fg=self.text_color,
                              font=self.font_manager.fonts["heading"])
        title_label.pack(side='left', padx=15, pady=10)

        # Content area
        content_frame = tk.Frame(card, bg=self.widget_bg_color)
        if height:
            content_frame.configure(height=height)
            content_frame.pack_propagate(False)
        content_frame.pack(fill='both', expand=True, padx=1, pady=(0, 1))

        return content_frame

    def create_modern_button(self, parent, text, command, bg_color, width=None):
        """Create a modern styled button matching the mockup"""
        btn = tk.Button(parent, text=text, command=command,
                       bg=bg_color, fg=self.button_text_color,
                       relief='flat', font=self.font_manager.fonts["button"],
                       cursor='hand2', activebackground=self.darken_color(bg_color))
        if width:
            btn.configure(width=width)
        return btn

    def darken_color(self, color):
        """Darken colors for hover effects"""
        color_map = {
            '#00d4aa': '#00c499',  # Green
            '#4a9eff': '#3a89ef',  # Blue
            '#ffa500': '#e6940a',  # Orange
            '#ff4757': '#e63946'   # Red
        }
        return color_map.get(color, color)

    def scroll_to_widget(self, widget):
        self.canvas.update_idletasks()

        scroll_region_str = self.canvas.cget("scrollregion")
        if not scroll_region_str: return

        try:
            scrollable_height = float(scroll_region_str.split(' ')[3])
        except (ValueError, IndexError):
            return # Invalid scrollregion format

        if scrollable_height <= 0: return

        # Y position of the top of the canvas viewport, relative to the root window
        canvas_root_y = self.canvas.winfo_rooty()

        # Y position of the top of the widget, relative to the root window
        widget_root_y = widget.winfo_rooty()

        # The widget's y-position relative to the canvas's top edge
        y_in_canvas = widget_root_y - canvas_root_y

        # The current scroll position (a tuple of fractions, e.g., (0.0, 0.5))
        current_scroll_fraction = self.canvas.yview()

        # The y-offset of the scrolled content
        scrolled_y_offset = current_scroll_fraction[0] * scrollable_height

        # The widget's "true" y-position within the entire scrollable content
        absolute_y = y_in_canvas + scrolled_y_offset

        # The fraction to scroll to, ensuring it's not more than 1.0
        fraction = min(absolute_y / scrollable_height, 1.0)

        self.canvas.yview_moveto(fraction)

    def create_modern_header(self, parent):
        header_frame = tk.Frame(parent, bg=self.bg_color, height=60)
        header_frame.pack(fill='x', pady=(0, 20))
        header_frame.pack_propagate(False)

        # App title with emoji
        title_label = tk.Label(header_frame, text="🤖 Pixel Bot",
                              bg=self.bg_color, fg=self.accent_color,
                              font=('Segoe UI', 20, 'bold'))
        title_label.pack(side='left', pady=15, padx=20)

        # Navigation buttons
        nav_frame = tk.Frame(header_frame, bg=self.bg_color)
        nav_frame.pack(side='right', pady=15, padx=20)

        self.create_modern_button(nav_frame, 'Templates', lambda: self.scroll_to_widget(self.templates_card_content), self.widget_bg_color).pack(side='left', padx=10)
        self.create_modern_button(nav_frame, 'Settings', lambda: self.scroll_to_widget(self.settings_card_content), self.widget_bg_color).pack(side='left')

    def on_closing(self):
        logging.info("Closing application and stopping listener...")
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.destroy()

    def show_preview_dialog(self):
        """Open the script preview dialog"""
        if not self.action_sequence:
            messagebox.showinfo("No Sequence", "Please add some steps to preview.")
            return

        PreviewDialog(self, self.action_sequence)

    def start_live_preview(self):
        """Start live preview mode - shows what bot would do in real-time"""
        if not self.action_sequence:
            messagebox.showinfo("No Sequence", "Please add some steps for a live preview.")
            return

        PreviewOverlay(self, self.action_sequence)

    def _configure_theme(self):
        theme = self.settings_manager.get_setting('theme')
        colors = self.dark_theme if theme == 'dark' else self.light_theme

        self.bg_color = colors['bg_color']
        self.widget_bg_color = colors['widget_bg_color']
        self.text_color = colors['text_color']
        self.accent_color = colors['accent_color']
        self.button_color = colors['button_color']
        self.button_text_color = colors['button_text_color']
        self.card_header = colors['card_header']
        self.border_color = colors['border_color']
        self.text_secondary = colors['text_secondary']
        self.warning_color = colors['warning_color']
        self.danger_color = colors['danger_color']

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

        # ttk.Checkbutton is no longer used, tk.Checkbutton is used instead for better styling.
        self.style.configure('TRadiobutton', background=colors['widget_bg_color'], foreground=colors['text_color'], font=fonts["primary"])
        self.style.map('TRadiobutton', background=[('active', colors['widget_bg_color'])])
        self.style.configure('Heading.TLabel', background=colors['bg_color'], foreground=colors['accent_color'], font=fonts["heading"])

        self.style.configure('TEntry',
            fieldbackground=colors['widget_bg_color'],
            foreground=colors['text_color'],
            insertcolor=colors['text_color'],
            relief='flat',
            borderwidth=1)

        self.style.map('TEntry',
            focuscolor=[('focus', colors['accent_color'])])

        # Style for OptionMenu
        self.style.configure('TMenubutton',
            background=colors['widget_bg_color'],
            foreground=colors['text_color'],
            arrowcolor=colors['text_color'],
            relief='flat',
            borderwidth=1,
            padding=5)
        self.style.map('TMenubutton',
            background=[('active', colors['button_color'])])

        self.style.configure('TLabelFrame',
            background=colors['bg_color'],
            relief='flat',
            borderwidth=1,
            lightcolor=colors['widget_bg_color'],       # Use widget bg as border
            darkcolor=colors['widget_bg_color'])        # Use widget bg as border

        self.style.configure('TLabelFrame.Label', background=colors['bg_color'], foreground=colors['text_color'], font=fonts["heading"])


        # Special "Card" style for labels that need a background
        self.style.configure("Card.TLabel", background=colors['widget_bg_color'], relief=tk.SOLID, borderwidth=1, font=fonts["primary"])

        # Accent Button (Start Bot) is now handled by create_modern_button, so this style is removed.

        # Notebook styling
        self.style.configure('TNotebook', background=colors['bg_color'], borderwidth=0)
        self.style.configure('TNotebook.Tab', background=colors['bg_color'], foreground=colors['text_color'], padding=[10, 5], font=fonts["primary"])
        self.style.map('TNotebook.Tab', background=[('selected', colors['widget_bg_color'])], foreground=[('selected', colors['accent_color'])])

        # Table/Treeview Styling
        self.style.theme_use('clam')
        self.style.configure('Treeview',
                       background=colors['widget_bg_color'],
                       foreground=colors['text_color'],
                       fieldbackground=colors['widget_bg_color'],
                       borderwidth=0,
                       relief='flat')
        self.style.configure('Treeview.Heading',
                       background=colors['border_color'],
                       foreground=colors['text_color'],
                       relief='flat')
        self.style.map('Treeview.Heading', background=[('active', colors['card_header'])])


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
        self.add_step_button.config(state=tk.NORMAL)
        logging.info(f"Global target window set to: {title}")

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
        parent_frame.rowconfigure(1, weight=1) # For the preview text

        # --- Treeview for categories and templates ---
        gallery_container = tk.Frame(parent_frame, bg=self.widget_bg_color)
        gallery_container.pack(fill='both', expand=True, padx=15, pady=(10,0))
        gallery_container.columnconfigure(0, weight=1)
        gallery_container.rowconfigure(0, weight=1)

        self.template_tree = ttk.Treeview(gallery_container, show="tree headings", selectmode="browse", height=5)
        self.template_tree.heading("#0", text="Name", anchor='w')
        self.template_tree.grid(row=0, column=0, sticky="nsew")
        self.template_tree.bind("<<TreeviewSelect>>", self.on_template_selected)

        # --- Preview Panel ---
        self.template_preview_text = scrolledtext.ScrolledText(parent_frame, height=6, wrap=tk.WORD, bg=self.bg_color, fg=self.text_color, relief=tk.FLAT, bd=1)
        self.template_preview_text.pack(fill='both', expand=True, padx=15, pady=10)
        self.template_preview_text.config(state=tk.DISABLED)

        # --- Controls ---
        self.insert_template_button = self.create_modern_button(parent_frame, "➕ Insert Template", self.insert_selected_template, self.sleek_blue_theme['accent_color'])
        self.insert_template_button.pack(pady=(0, 10))
        self.insert_template_button.config(state=tk.DISABLED)

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
