import logging
import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2

# App is imported locally in __init__ to avoid circular dependency.
from .dialogs import RegionSelector, ColorSampler, ScreenshotTaker
from .window_selector import WindowSelector


class StepEditor(tk.Toplevel):
    def __init__(self, master, step_data=None, index=None, target_sequence_list=None, on_save_callback=None, is_sub_editor=False):
        super().__init__(master)
        from pixel_bot.gui.main_window import App

        self.master = master # This is the App instance
        self.step_data = step_data if step_data else {}
        self.index = index
        self.target_sequence_list = target_sequence_list
        self.on_save_callback = on_save_callback
        self.is_sub_editor = is_sub_editor

        self.title("Action Editor" if is_sub_editor else "Step Editor")

        # Find the root App instance to access theme colors correctly in sub-editors
        app = self.master
        while not isinstance(app, App):
            app = app.master
        self.app = app # Store it for later use if needed

        self.configure(bg=app.bg_color)
        self.transient(self.master)

        # Make the window resizable
        self.resizable(True, True)

        self.grab_set()

        # --- VARS ---
        self.step_type = tk.StringVar(value=self.step_data.get('step_type', 'simple'))
        self.wait_duration = tk.StringVar(value=str(self.step_data.get('duration', '1.0')))

        # Vars for Simple Action
        self.detection_mode = tk.StringVar(value=self.step_data.get('detection_mode', 'Image'))
        self.action_type = tk.StringVar(value=self.step_data.get('action_type', 'Click'))
        self.simple_click_offset_x = tk.StringVar(value=self.step_data.get('action_params', {}).get('click_offset_x', '0'))
        self.simple_click_offset_y = tk.StringVar(value=self.step_data.get('action_params', {}).get('click_offset_y', '0'))
        self.text_to_type = tk.StringVar(value=self.step_data.get('action_params', {}).get('text', ''))
        self.key_combo_text = tk.StringVar(value=self.step_data.get('action_params', {}).get('key_combo', 'ctrl+c'))
        self.variable_name = tk.StringVar(value=self.step_data.get('action_params', {}).get('variable_name', ''))
        self.variable_value = tk.StringVar(value=self.step_data.get('action_params', {}).get('variable_value', ''))
        self.modify_variable_name = tk.StringVar(value=self.step_data.get('action_params', {}).get('modify_variable_name', ''))
        self.modify_variable_operation = tk.StringVar(value=self.step_data.get('action_params', {}).get('modify_variable_operation', 'add'))
        self.modify_variable_value = tk.StringVar(value=self.step_data.get('action_params', {}).get('modify_variable_value', '1'))
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

        # Vars for Conditional Branch (If/Else)
        condition = self.step_data.get('condition', {})
        self.if_variable = tk.StringVar(value=condition.get('variable', ''))
        self.if_operator = tk.StringVar(value=condition.get('operator', 'equals'))
        self.if_value = tk.StringVar(value=condition.get('value', ''))
        self.if_branch = self.step_data.get('if_branch', [])
        self.else_branch = self.step_data.get('else_branch', [])

        # Vars for Loop Step
        self.loop_mode = tk.StringVar(value=self.step_data.get('loop_mode', 'repeat'))
        self.loop_repeat_count = tk.StringVar(value=self.step_data.get('loop_repeat_count', '5'))
        self.loop_actions = self.step_data.get('loop_actions', [])
        self.loop_max_retries = tk.StringVar(value=self.step_data.get('max_retries', '10'))

        # Vars for Time-based Condition
        self.time_condition_hour = tk.StringVar(value=self.step_data.get('time_condition', {}).get('hour', '12'))
        self.time_condition_minute = tk.StringVar(value=self.step_data.get('time_condition', {}).get('minute', '00'))
        self.time_based_actions = self.step_data.get('actions', [])

        # Vars for Post-Action Wait
        wait_params = self.step_data.get('wait_params')
        if wait_params is None: # It's a new step, so load the defaults from settings
            default_wait_params = self.app.settings_manager.get_setting('default_wait_times')
            self.wait_type = tk.StringVar(value='None') # Default to None for new steps
            self.fixed_wait = tk.StringVar(value=str(default_wait_params.get('fixed_time', 1)))
            self.min_wait = tk.StringVar(value=str(default_wait_params.get('min_time', 1)))
            self.max_wait = tk.StringVar(value=str(default_wait_params.get('max_time', 2)))
        else: # It's an existing step, load its saved values
            self.wait_type = tk.StringVar(value=wait_params.get('type', 'None'))
            self.fixed_wait = tk.StringVar(value=str(wait_params.get('fixed_time', 1)))
            self.min_wait = tk.StringVar(value=str(wait_params.get('min_time', 1)))
            self.max_wait = tk.StringVar(value=str(wait_params.get('max_time', 2)))

        # Vars for On Failure
        on_failure_params = self.step_data.get('on_failure', {})
        self.on_failure_policy = tk.StringVar(value=on_failure_params.get('policy', 'Stop'))
        self.on_failure_retries = tk.StringVar(value=on_failure_params.get('retries', '3'))


        # --- LAYOUT FRAMES ---
        # A bottom frame for buttons that never gets pushed out of view
        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", fill="x", pady=10, padx=10)

        # A main content frame that can expand and scroll
        content_frame = ttk.Frame(self, padding="10")
        content_frame.pack(side="top", fill="both", expand=True)
        content_frame.columnconfigure(0, weight=1)

        # --- WIDGETS ---
        # --- Step Type Selection ---
        step_type_frame = ttk.LabelFrame(content_frame, text="Step Type", padding="10")
        step_type_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        step_type_frame.columnconfigure(0, weight=1) # Allow radio buttons to space out

        self.step_type_radios = {}
        step_types = [
            ("Simple Action", "simple"),
            ("Wait", "wait"),
            ("If/Else", "conditional_branch"),
            ("Loop", "loop"),
            ("Time-based Condition", "time_based_condition"),
            ("Conditional (Legacy)", "conditional_loop")
        ]
        for i, (text, value) in enumerate(step_types):
            radio = ttk.Radiobutton(step_type_frame, text=text, variable=self.step_type, value=value, command=self.on_step_type_change)
            radio.grid(row=0, column=i, sticky="ew", padx=5)
            self.step_type_radios[value] = radio

        # --- Main Frames for each step type (parented to content_frame) ---
        self.simple_action_frame = ttk.Frame(content_frame, padding="10")
        self.conditional_loop_frame = ttk.Frame(content_frame, padding="10")
        self.loop_frame = ttk.Frame(content_frame, padding="10")
        self.conditional_branch_frame = ttk.Frame(content_frame, padding="10")
        self.time_based_condition_frame = ttk.Frame(content_frame, padding="10")
        self.wait_step_frame = ttk.Frame(content_frame, padding="10")

        # --- UI for Simple Action Frame ---
        self.build_simple_action_ui(self.simple_action_frame)

        # --- UI for Conditional Loop Frame ---
        self.build_conditional_loop_ui(self.conditional_loop_frame)

        # --- UI for Loop Frame ---
        self.build_loop_ui(self.loop_frame)

        # --- UI for Conditional Branch Frame ---
        self.build_conditional_branch_ui(self.conditional_branch_frame)

        # --- UI for Time-based Condition Frame ---
        self.build_time_based_condition_ui(self.time_based_condition_frame)

        # --- UI for Wait Step Frame ---
        self.build_wait_step_ui(self.wait_step_frame)

        # --- Save/Cancel Buttons (parented to button_frame) ---
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="right", padx=10)
        ttk.Button(button_frame, text="Save Step", command=self.on_save, style="Accent.TButton").pack(side="right")

        self.on_step_type_change() # Set initial view

    def build_simple_action_ui(self, parent_frame):
        # This function builds the UI for a simple action, parented to the given frame.
        parent_frame.columnconfigure(1, weight=1) # Allow labels and entries to expand

        window_frame = ttk.LabelFrame(parent_frame, text="1. Select Target Window", padding="10")
        window_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        window_frame.columnconfigure(0, weight=1)
        self.window_label = ttk.Label(window_frame, textvariable=self.target_window_title, wraplength=250)
        self.window_label.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(window_frame, text="Select...", command=self.select_window).grid(row=0, column=1)
        if not self.target_window_title.get(): self.target_window_title.set("(None Selected)")

        region_frame = ttk.LabelFrame(parent_frame, text="2. Set Search Region (Optional)", padding="10")
        region_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        region_frame.columnconfigure(0, weight=1)
        self.region_label = ttk.Label(region_frame, textvariable=self.search_region_label_var, wraplength=350)
        self.region_label.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(region_frame, text="Set Region", command=self.set_search_region).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(region_frame, text="Clear", command=self.clear_search_region).grid(row=0, column=2)


        mode_frame = ttk.LabelFrame(parent_frame, text="3. Choose What to Look For", padding="10")
        mode_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Radiobutton(mode_frame, text="Color", variable=self.detection_mode, value="Color", command=self.on_mode_change).pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="Image", variable=self.detection_mode, value="Image", command=self.on_mode_change).pack(anchor="w")

        self.color_frame = ttk.Frame(parent_frame)
        self.image_frame = ttk.Frame(parent_frame)

        ttk.Button(self.color_frame, text="Sample Color", command=self.sample_color).pack()
        self.color_preview = tk.Frame(self.color_frame, bg=self.app._bgr_to_hex(self.target_color_bgr), width=25, height=25, relief=tk.SUNKEN, borderwidth=1)
        self.color_preview.pack(pady=5)

        ttk.Button(self.image_frame, text="Take Screenshot", command=self.take_screenshot).pack(pady=(0,5))

        # --- Image List ---
        image_list_frame = ttk.Frame(self.image_frame)
        image_list_frame.pack(fill="x", expand=True, pady=5)
        image_list_frame.columnconfigure(0, weight=1)

        self.image_listbox = tk.Listbox(image_list_frame, bg=self.app.widget_bg_color, fg=self.app.text_color, relief=tk.FLAT, height=4, selectmode=tk.EXTENDED)
        self.image_listbox.grid(row=0, column=0, sticky="ew", rowspan=2)

        image_button_frame = ttk.Frame(image_list_frame)
        image_button_frame.grid(row=0, column=1, rowspan=2, sticky="ns", padx=(5,0))
        ttk.Button(image_button_frame, text="Add", command=lambda: self._add_image_template_to_listbox(self.image_listbox)).pack(fill="x", pady=2)
        ttk.Button(image_button_frame, text="Remove", command=lambda: self._remove_image_template_from_listbox(self.image_listbox)).pack(fill="x", pady=2)

        self._update_image_listbox()

        action_frame = ttk.LabelFrame(parent_frame, text="4. Choose Action", padding="10")
        action_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        action_types = ["Click", "Right-click", "Click with Offset", "Type", "Key Combo", "Scroll", "Set Variable", "Modify Variable", "OCR"]
        for i, action in enumerate(action_types):
            ttk.Radiobutton(action_frame, text=action, variable=self.action_type, value=action, command=self.on_action_change).grid(row=i, column=0, sticky="w")

        self.type_entry_frame = ttk.Frame(action_frame)
        self.type_entry = ttk.Entry(self.type_entry_frame, textvariable=self.text_to_type)
        self.type_entry.pack(fill="x", padx=5, pady=5)

        self.key_combo_frame = ttk.Frame(action_frame)
        ttk.Label(self.key_combo_frame, text="Keys (e.g., ctrl+alt+delete):").pack(side="left", padx=5)
        self.key_combo_entry = ttk.Entry(self.key_combo_frame, textvariable=self.key_combo_text, width=20)
        self.key_combo_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        self.set_variable_frame = ttk.Frame(action_frame)
        ttk.Label(self.set_variable_frame, text="Name:").pack(side="left", padx=5)
        ttk.Entry(self.set_variable_frame, textvariable=self.variable_name, width=15).pack(side="left", padx=5)
        ttk.Label(self.set_variable_frame, text="Value:").pack(side="left", padx=5)
        ttk.Entry(self.set_variable_frame, textvariable=self.variable_value, width=20).pack(side="left", padx=5)

        self.modify_variable_frame = ttk.Frame(action_frame)
        ttk.Label(self.modify_variable_frame, text="Name:").pack(side="left", padx=5)
        ttk.Entry(self.modify_variable_frame, textvariable=self.modify_variable_name, width=15).pack(side="left", padx=5)
        operations = ["add", "subtract", "set"]
        ttk.OptionMenu(self.modify_variable_frame, self.modify_variable_operation, *operations).pack(side="left", padx=5)
        ttk.Label(self.modify_variable_frame, text="Value:").pack(side="left", padx=5)
        ttk.Entry(self.modify_variable_frame, textvariable=self.modify_variable_value, width=15).pack(side="left", padx=5)

        self.ocr_frame = ttk.Frame(action_frame)
        ocr_var_frame = ttk.Frame(self.ocr_frame)
        ttk.Label(ocr_var_frame, text="Save Text to Variable:").pack(side="left", padx=5)
        ttk.Entry(ocr_var_frame, textvariable=self.output_variable_name, width=20).pack(side="left", padx=5)
        ocr_var_frame.pack(fill="x", pady=2)

        ocr_region_frame = ttk.Frame(self.ocr_frame)
        self.ocr_region_label = ttk.Label(ocr_region_frame, textvariable=self.ocr_region_label_var, wraplength=350)
        self.ocr_region_label.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(ocr_region_frame, text="Set Region", command=self.set_ocr_region).pack(side="left", padx=(0, 5))
        ocr_region_frame.pack(fill="x", pady=2)


        self.simple_offset_frame = ttk.Frame(action_frame)
        simple_offset_x_frame = ttk.Frame(self.simple_offset_frame)
        ttk.Label(simple_offset_x_frame, text="X Offset:").pack(side="left", padx=5)
        ttk.Entry(simple_offset_x_frame, textvariable=self.simple_click_offset_x, width=7).pack(side="left")
        simple_offset_x_frame.pack(fill="x", pady=2)
        simple_offset_y_frame = ttk.Frame(self.simple_offset_frame)
        ttk.Label(simple_offset_y_frame, text="Y Offset:").pack(side="left", padx=5)
        ttk.Entry(simple_offset_y_frame, textvariable=self.simple_click_offset_y, width=7).pack(side="left")
        simple_offset_y_frame.pack(fill="x", pady=2)

        self.scroll_frame = ttk.Frame(action_frame)
        scroll_direction_frame = ttk.Frame(self.scroll_frame)
        ttk.Label(scroll_direction_frame, text="Direction:").pack(side="left", padx=5)
        ttk.OptionMenu(scroll_direction_frame, self.scroll_direction, "Down", "Up").pack(side="left")
        scroll_direction_frame.pack(fill="x", pady=2)
        scroll_amount_frame = ttk.Frame(self.scroll_frame)
        ttk.Label(scroll_amount_frame, text="Amount:").pack(side="left", padx=5)
        ttk.Entry(scroll_amount_frame, textvariable=self.scroll_amount, width=7).pack(side="left")
        scroll_amount_frame.pack(fill="x", pady=2)

        self.on_mode_change()
        self.on_action_change()
        self._build_on_failure_ui(parent_frame).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self._build_wait_ui(parent_frame).grid(row=6, column=0, columnspan=2, sticky="ew")

    def _build_on_failure_ui(self, parent_frame):
        on_failure_frame = ttk.LabelFrame(parent_frame, text="On Failure", padding="10")

        # --- Policy ---
        policy_frame = ttk.Frame(on_failure_frame)
        ttk.Label(policy_frame, text="Action on Failure:").pack(side="left", padx=(0,10))
        ttk.Radiobutton(policy_frame, text="Stop Bot", variable=self.on_failure_policy, value="Stop", command=self.on_failure_policy_change).pack(side="left")
        ttk.Radiobutton(policy_frame, text="Skip Step", variable=self.on_failure_policy, value="Skip", command=self.on_failure_policy_change).pack(side="left")
        ttk.Radiobutton(policy_frame, text="Retry Step", variable=self.on_failure_policy, value="Retry", command=self.on_failure_policy_change).pack(side="left")
        policy_frame.pack(fill="x", pady=(0,5))

        # --- Retries Frame ---
        self.retries_frame = ttk.Frame(on_failure_frame)
        ttk.Label(self.retries_frame, text="Number of Retries:").pack(side="left", padx=5)
        self.retries_entry = ttk.Entry(self.retries_frame, textvariable=self.on_failure_retries, width=7)
        self.retries_entry.pack(side="left")

        self.on_failure_policy_change() # Set initial visibility
        return on_failure_frame

    def on_failure_policy_change(self):
        if self.on_failure_policy.get() == "Retry":
            self.retries_frame.pack(fill="x", pady=2)
        else:
            self.retries_frame.pack_forget()

    def build_conditional_loop_ui(self, parent_frame):
        # --- Loop Settings ---
        retries_frame = ttk.LabelFrame(parent_frame, text="Loop Settings", padding="10")
        retries_frame.pack(pady=5, padx=10, fill="x")
        ttk.Label(retries_frame, text="Max Retries:").pack(side="left", padx=5)
        ttk.Entry(retries_frame, textvariable=self.max_retries, width=5).pack(side="left", padx=5)

        # --- Primary Target ---
        primary_target_frame = ttk.LabelFrame(parent_frame, text="Primary Target (Image(s) to find)", padding="10")
        primary_target_frame.pack(pady=5, padx=10, fill="x")

        primary_list_frame = ttk.Frame(primary_target_frame)
        primary_list_frame.pack(fill="x", expand=True, pady=5)

        self.primary_image_listbox = tk.Listbox(primary_list_frame, bg=self.app.widget_bg_color, fg=self.app.text_color, relief=tk.FLAT, height=4, selectmode=tk.EXTENDED)
        self.primary_image_listbox.pack(side="left", fill="x", expand=True)

        primary_button_frame = ttk.Frame(primary_list_frame)
        primary_button_frame.pack(side="left", padx=(5,0))
        ttk.Button(primary_button_frame, text="Add", command=lambda: self._add_image_template_to_listbox(self.primary_image_listbox)).pack(fill="x", pady=2)
        ttk.Button(primary_button_frame, text="Remove", command=lambda: self._remove_image_template_from_listbox(self.primary_image_listbox)).pack(fill="x", pady=2)

        # --- Fallback Action ---
        fallback_action_frame = ttk.LabelFrame(parent_frame, text="Fallback Action (If primary target not found)", padding="10")
        fallback_action_frame.pack(pady=5, padx=10, fill="x")

        # --- Fallback Action Type ---
        fallback_action_type_frame = ttk.Frame(fallback_action_frame)
        ttk.Label(fallback_action_type_frame, text="Action:").pack(side="left", pady=2, padx=5)
        ttk.Radiobutton(fallback_action_type_frame, text="Click", variable=self.fallback_action_type, value="Click", command=self.on_fallback_action_change).pack(side="left")
        ttk.Radiobutton(fallback_action_type_frame, text="Click with Offset", variable=self.fallback_action_type, value="Click with Offset", command=self.on_fallback_action_change).pack(side="left")
        ttk.Radiobutton(fallback_action_type_frame, text="Click and Drag", variable=self.fallback_action_type, value="Click and Drag", command=self.on_fallback_action_change).pack(side="left")
        ttk.Radiobutton(fallback_action_type_frame, text="Do Nothing", variable=self.fallback_action_type, value="Do Nothing", command=self.on_fallback_action_change).pack(side="left")
        fallback_action_type_frame.pack(fill="x")

        # --- Fallback Action Params ---
        self.fallback_drag_frame = ttk.Frame(fallback_action_frame)
        drag_x_frame = ttk.Frame(self.fallback_drag_frame)
        ttk.Label(drag_x_frame, text="X Offset:").pack(side="left", padx=5)
        ttk.Entry(drag_x_frame, textvariable=self.fallback_drag_offset_x, width=7).pack(side="left")
        drag_x_frame.pack(fill="x", pady=2)
        drag_y_frame = ttk.Frame(self.fallback_drag_frame)
        ttk.Label(drag_y_frame, text="Y Offset:").pack(side="left", padx=5)
        ttk.Entry(drag_y_frame, textvariable=self.fallback_drag_offset_y, width=7).pack(side="left")
        drag_y_frame.pack(fill="x", pady=2)

        # --- Fallback Target ---
        self.fallback_target_frame = ttk.Frame(fallback_action_frame)
        ttk.Label(self.fallback_target_frame, text="Target for Fallback Action:").pack(pady=2, anchor="w", padx=5)

        fallback_list_frame = ttk.Frame(self.fallback_target_frame)
        fallback_list_frame.pack(fill="x", expand=True)

        self.fallback_image_listbox = tk.Listbox(fallback_list_frame, bg=self.app.widget_bg_color, fg=self.app.text_color, relief=tk.FLAT, height=4, selectmode=tk.EXTENDED)
        self.fallback_image_listbox.pack(side="left", fill="x", expand=True)

        fallback_button_frame = ttk.Frame(fallback_list_frame)
        fallback_button_frame.pack(side="left", padx=(5,0))
        ttk.Button(fallback_button_frame, text="Add", command=lambda: self._add_image_template_to_listbox(self.fallback_image_listbox)).pack(fill="x", pady=2)
        ttk.Button(fallback_button_frame, text="Remove", command=lambda: self._remove_image_template_from_listbox(self.fallback_image_listbox)).pack(fill="x", pady=2)

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
        loop_mode_frame = ttk.LabelFrame(parent_frame, text="Loop Mode", padding="10")
        loop_mode_frame.pack(pady=5, padx=10, fill="x")
        ttk.Radiobutton(loop_mode_frame, text="Repeat X Times", variable=self.loop_mode, value="repeat", command=self.on_loop_mode_change).pack(side="left")
        ttk.Radiobutton(loop_mode_frame, text="Until Condition Met", variable=self.loop_mode, value="until", command=self.on_loop_mode_change).pack(side="left")

        # --- Loop Settings ---
        self.loop_settings_frame = ttk.Frame(parent_frame)
        self.loop_settings_frame.pack(pady=5, padx=10, fill="x")

        self.repeat_frame = ttk.Frame(self.loop_settings_frame)
        ttk.Label(self.repeat_frame, text="Repetitions:").pack(side="left", padx=5)
        ttk.Entry(self.repeat_frame, textvariable=self.loop_repeat_count, width=5).pack(side="left")

        self.until_frame = ttk.Frame(self.loop_settings_frame)
        ttk.Label(self.until_frame, text="Condition (Image):").pack(anchor="w", padx=5)

        until_list_frame = ttk.Frame(self.until_frame)
        until_list_frame.pack(fill="x", expand=True)

        self.until_image_listbox = tk.Listbox(until_list_frame, bg=self.app.widget_bg_color, fg=self.app.text_color, relief=tk.FLAT, height=4, selectmode=tk.EXTENDED)
        self.until_image_listbox.pack(side="left", fill="x", expand=True)

        until_button_frame = ttk.Frame(until_list_frame)
        until_button_frame.pack(side="left", padx=(5,0))
        ttk.Button(until_button_frame, text="Add", command=lambda: self._add_image_template_to_listbox(self.until_image_listbox)).pack(fill="x", pady=2)
        ttk.Button(until_button_frame, text="Remove", command=lambda: self._remove_image_template_from_listbox(self.until_image_listbox)).pack(fill="x", pady=2)

        max_retries_frame = ttk.Frame(self.until_frame)
        max_retries_frame.pack(fill="x", pady=2, side="bottom")
        ttk.Label(max_retries_frame, text="Max Retries:").pack(side="left", padx=5)
        ttk.Entry(max_retries_frame, textvariable=self.loop_max_retries, width=5).pack(side="left")

        # --- Actions Frame ---
        actions_frame = ttk.LabelFrame(parent_frame, text="Actions to Loop", padding="10")
        actions_frame.pack(pady=5, padx=10, fill="both", expand=True)

        list_container = ttk.Frame(actions_frame)
        list_container.pack(fill="both", expand=True)

        self.loop_actions_listbox = tk.Listbox(list_container, bg=self.app.widget_bg_color, fg=self.app.text_color, relief=tk.FLAT, height=6)
        self.loop_actions_listbox.pack(side="left", fill="both", expand=True)
        self.loop_actions_listbox.bind("<<ListboxSelect>>", self.on_loop_action_select)

        seq_button_frame = ttk.Frame(list_container)
        seq_button_frame.pack(side="left", padx=(5,0), fill="y")

        ttk.Button(seq_button_frame, text="Add", command=self._add_loop_action).pack(pady=2, fill="x")
        self.edit_loop_action_button = ttk.Button(seq_button_frame, text="Edit", command=self._edit_loop_action, state=tk.DISABLED)
        self.edit_loop_action_button.pack(pady=2, fill="x")
        self.remove_loop_action_button = ttk.Button(seq_button_frame, text="Remove", command=self._remove_loop_action, state=tk.DISABLED)
        self.remove_loop_action_button.pack(pady=2, fill="x")

        # Disable loop/conditional step types if this is a sub-editor
        if self.is_sub_editor:
            self.step_type_radios['loop'].config(state=tk.DISABLED)
            self.step_type_radios['conditional_loop'].config(state=tk.DISABLED)
            self.step_type.set('simple') # Default to simple action for sub-steps


        self.on_loop_mode_change()
        self._update_loop_actions_listbox()
        self._update_until_image_listbox()

    def build_conditional_branch_ui(self, parent_frame):
        # --- Condition Builder ---
        condition_frame = ttk.LabelFrame(parent_frame, text="Condition", padding="10")
        condition_frame.pack(pady=5, padx=10, fill="x")

        ttk.Label(condition_frame, text="If variable").pack(side="left", padx=5)
        ttk.Entry(condition_frame, textvariable=self.if_variable, width=15).pack(side="left", padx=5)

        operators = ["equals", "not equals", "contains", "not contains", "is greater than", "is less than"]
        ttk.OptionMenu(condition_frame, self.if_operator, *operators).pack(side="left", padx=5)

        ttk.Label(condition_frame, text="value").pack(side="left", padx=5)
        ttk.Entry(condition_frame, textvariable=self.if_value, width=15).pack(side="left", padx=5)

        # --- Branch Frames ---
        branch_parent_frame = ttk.Frame(parent_frame)
        branch_parent_frame.pack(pady=5, padx=10, fill="both", expand=True)

        # --- IF Branch ---
        if_frame = self._create_branch_frame(branch_parent_frame, "IF Actions (if condition is true)")
        self.if_listbox = self._create_branch_listbox(if_frame, self.on_if_action_select)
        self.if_edit_button, self.if_remove_button = self._create_branch_buttons(
            if_frame,
            self._add_if_action,
            self._edit_if_action,
            self._remove_if_action
        )
        if_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # --- ELSE Branch ---
        else_frame = self._create_branch_frame(branch_parent_frame, "ELSE Actions (optional)")
        self.else_listbox = self._create_branch_listbox(else_frame, self.on_else_action_select)
        self.else_edit_button, self.else_remove_button = self._create_branch_buttons(
            else_frame,
            self._add_else_action,
            self._edit_else_action,
            self._remove_else_action
        )
        else_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        self._update_if_actions_listbox()
        self._update_else_actions_listbox()


    def _create_branch_frame(self, parent, title):
        frame = ttk.LabelFrame(parent, text=title, padding="10")
        return frame

    def _create_branch_listbox(self, parent, select_callback):
        list_container = ttk.Frame(parent)
        list_container.pack(fill="both", expand=True)
        listbox = tk.Listbox(list_container, bg=self.app.widget_bg_color, fg=self.app.text_color, relief=tk.FLAT, height=8)
        listbox.pack(side="left", fill="both", expand=True)
        listbox.bind("<<ListboxSelect>>", select_callback)
        return listbox

    def _create_branch_buttons(self, parent, add_cmd, edit_cmd, remove_cmd):
        button_frame = ttk.Frame(parent.winfo_children()[0]) # Get the list_container
        button_frame.pack(side="left", padx=(5,0), fill="y")
        ttk.Button(button_frame, text="Add", command=add_cmd).pack(pady=2, fill="x")
        edit_button = ttk.Button(button_frame, text="Edit", command=edit_cmd, state=tk.DISABLED)
        edit_button.pack(pady=2, fill="x")
        remove_button = ttk.Button(button_frame, text="Remove", command=remove_cmd, state=tk.DISABLED)
        remove_button.pack(pady=2, fill="x")
        return edit_button, remove_button

    def _add_if_action(self):
        self._open_sub_editor(self.if_branch, self._update_if_actions_listbox)
    def _edit_if_action(self):
        self._open_sub_editor(self.if_branch, self._update_if_actions_listbox, self.if_listbox.curselection())
    def _remove_if_action(self):
        self._remove_action_from_branch(self.if_branch, self.if_listbox.curselection(), self._update_if_actions_listbox)

    def _add_else_action(self):
        self._open_sub_editor(self.else_branch, self._update_else_actions_listbox)
    def _edit_else_action(self):
        self._open_sub_editor(self.else_branch, self._update_else_actions_listbox, self.else_listbox.curselection())
    def _remove_else_action(self):
        self._remove_action_from_branch(self.else_branch, self.else_listbox.curselection(), self._update_else_actions_listbox)

    def _open_sub_editor(self, branch_list, update_callback, selection=None):
        index = None
        step_data = {}
        if selection:
            index = selection[0]
            step_data = branch_list[index]
        StepEditor(
            master=self,
            step_data=step_data,
            index=index,
            target_sequence_list=branch_list,
            on_save_callback=update_callback,
            is_sub_editor=True
        )

    def _remove_action_from_branch(self, branch_list, selection, update_callback):
        if not selection: return
        index = selection[0]
        branch_list.pop(index)
        update_callback()
        logging.info(f"Removed sub-action {index+1}.")

    def on_if_action_select(self, event):
        self._update_button_state(self.if_listbox.curselection(), self.if_edit_button, self.if_remove_button)
    def on_else_action_select(self, event):
        self._update_button_state(self.else_listbox.curselection(), self.else_edit_button, self.else_remove_button)

    def _update_button_state(self, selection, edit_button, remove_button):
        if selection:
            edit_button.config(state=tk.NORMAL)
            remove_button.config(state=tk.NORMAL)
        else:
            edit_button.config(state=tk.DISABLED)
            remove_button.config(state=tk.DISABLED)

    def _update_if_actions_listbox(self):
        self._update_branch_listbox(self.if_listbox, self.if_branch)
    def _update_else_actions_listbox(self):
        self._update_branch_listbox(self.else_listbox, self.else_branch)

    def _update_branch_listbox(self, listbox, branch):
        listbox.delete(0, tk.END)
        for i, step in enumerate(branch):
            action = step.get('action_type', '?')
            target = step.get('detection_target_name', 'Unknown')
            text = f"{i+1}: {action} on '{target}'"
            listbox.insert(tk.END, text)
        # Manually trigger select event to update buttons
        self.on_if_action_select(None)
        self.on_else_action_select(None)


    def _add_time_based_action(self):
        self._open_sub_editor(self.time_based_actions, self._update_time_based_actions_listbox)

    def _edit_time_based_action(self):
        self._open_sub_editor(self.time_based_actions, self._update_time_based_actions_listbox, self.time_based_actions_listbox.curselection())

    def _remove_time_based_action(self):
        self._remove_action_from_branch(self.time_based_actions, self._update_time_based_actions_listbox)

    def _update_time_based_actions_listbox(self):
        self._update_branch_listbox(self.time_based_actions_listbox, self.time_based_actions)
        self.time_based_actions_listbox.bind("<<ListboxSelect>>", self.on_time_based_action_select)

    def on_time_based_action_select(self, event):
        self._update_button_state(self.time_based_actions_listbox.curselection(), self.edit_time_based_action_button, self.remove_time_based_action_button)

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
        logging.info(f"Removed sub-action {index+1}.")

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



    def build_time_based_condition_ui(self, parent_frame):
        # --- Time Settings ---
        time_frame = ttk.LabelFrame(parent_frame, text="Time Condition", padding="10")
        time_frame.pack(pady=5, padx=10, fill="x")
        ttk.Label(time_frame, text="Hour (0-23):").pack(side="left", padx=5)
        ttk.Entry(time_frame, textvariable=self.time_condition_hour, width=5).pack(side="left", padx=5)
        ttk.Label(time_frame, text="Minute (0-59):").pack(side="left", padx=5)
        ttk.Entry(time_frame, textvariable=self.time_condition_minute, width=5).pack(side="left", padx=5)

        # Add a real-time clock label
        self.current_time_label_var = tk.StringVar()
        current_time_label = ttk.Label(time_frame, textvariable=self.current_time_label_var)
        current_time_label.pack(side="left", padx=20)
        self._update_clock()

        actions_frame = ttk.LabelFrame(parent_frame, text="Actions to run at specified time", padding="10")
        actions_frame.pack(pady=5, padx=10, fill="both", expand=True)

        list_container = ttk.Frame(actions_frame)
        list_container.pack(fill="both", expand=True)

        self.time_based_actions_listbox = tk.Listbox(list_container, bg=self.app.widget_bg_color, fg=self.app.text_color, relief=tk.FLAT, height=6)
        self.time_based_actions_listbox.pack(side="left", fill="both", expand=True)

        seq_button_frame = ttk.Frame(list_container)
        seq_button_frame.pack(side="left", padx=(5,0), fill="y")

        ttk.Button(seq_button_frame, text="Add", command=self._add_time_based_action).pack(pady=2, fill="x")
        self.edit_time_based_action_button = ttk.Button(seq_button_frame, text="Edit", command=self._edit_time_based_action, state=tk.DISABLED)
        self.edit_time_based_action_button.pack(pady=2, fill="x")
        self.remove_time_based_action_button = ttk.Button(seq_button_frame, text="Remove", command=self._remove_time_based_action, state=tk.DISABLED)
        self.remove_time_based_action_button.pack(pady=2, fill="x")

        self._update_time_based_actions_listbox()

    def _update_clock(self):
        now_str = time.strftime("%H:%M:%S")
        self.current_time_label_var.set(f"Bot Time: {now_str}")
        self._clock_job = self.after(1000, self._update_clock)

    def destroy(self):
        # Override destroy to cancel the clock job
        if hasattr(self, '_clock_job'):
            self.after_cancel(self._clock_job)
        super().destroy()

    def build_wait_step_ui(self, parent_frame):
        """Builds the UI for the 'Wait' step type."""
        wait_frame = ttk.LabelFrame(parent_frame, text="Wait Configuration", padding="10")
        wait_frame.pack(pady=5, padx=10, fill="x")

        ttk.Label(wait_frame, text="Duration (seconds):").pack(side="left", padx=5)
        ttk.Entry(wait_frame, textvariable=self.wait_duration, width=10).pack(side="left", padx=5)

    def on_step_type_change(self):
        step_type = self.step_type.get()
        # Hide all frames first
        self.simple_action_frame.grid_remove()
        self.conditional_loop_frame.grid_remove()
        self.loop_frame.grid_remove()
        self.conditional_branch_frame.grid_remove()
        self.time_based_condition_frame.grid_remove()
        self.wait_step_frame.grid_remove()

        if step_type == 'simple':
            self.simple_action_frame.grid(row=1, column=0, sticky="ew")
        elif step_type == 'loop':
            self.loop_frame.grid(row=1, column=0, sticky="ew")
        elif step_type == 'conditional_branch':
            self.conditional_branch_frame.grid(row=1, column=0, sticky="ew")
        elif step_type == 'time_based_condition':
            self.time_based_condition_frame.grid(row=1, column=0, sticky="ew")
        elif step_type == 'wait':
            self.wait_step_frame.grid(row=1, column=0, sticky="ew")
        else: # conditional_loop
            self.conditional_loop_frame.grid(row=1, column=0, sticky="ew")

    def on_mode_change(self):
        if self.detection_mode.get() == "Color":
            self.image_frame.grid_remove()
            self.color_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        else:
            self.color_frame.grid_remove()
            self.image_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))

    def on_action_change(self):
        action = self.action_type.get()

        # Hide all action-specific frames first
        self.type_entry_frame.grid_remove()
        self.simple_offset_frame.grid_remove()
        self.scroll_frame.grid_remove()
        self.key_combo_frame.grid_remove()
        self.set_variable_frame.grid_remove()
        self.modify_variable_frame.grid_remove()
        self.ocr_frame.grid_remove()

        # The grid row for these frames should be after the radio buttons
        action_row = 10 # A number greater than the number of radio buttons

        if action == "Type":
            self.type_entry_frame.grid(row=action_row, column=0, columnspan=2, sticky="ew", pady=5)
        elif action == "Click with Offset":
            self.simple_offset_frame.grid(row=action_row, column=0, columnspan=2, sticky="ew", pady=5, padx=20)
        elif action == "Key Combo":
            self.key_combo_frame.grid(row=action_row, column=0, columnspan=2, sticky="ew", pady=5)
        elif action == "Scroll":
            self.scroll_frame.grid(row=action_row, column=0, columnspan=2, sticky="ew", pady=5, padx=20)
        elif action == "Set Variable":
            self.set_variable_frame.grid(row=action_row, column=0, columnspan=2, sticky="ew", pady=5)
        elif action == "Modify Variable":
            self.modify_variable_frame.grid(row=action_row, column=0, columnspan=2, sticky="ew", pady=5)
        elif action == "OCR":
            self.ocr_frame.grid(row=action_row, column=0, columnspan=2, sticky="ew", pady=5)

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
        wait_frame = ttk.LabelFrame(parent_frame, text="Post-Action Wait", padding="10")

        # --- Wait Type ---
        wait_type_frame = ttk.Frame(wait_frame)
        ttk.Radiobutton(wait_type_frame, text="None", variable=self.wait_type, value="None", command=self.on_wait_type_change).pack(side="left")
        ttk.Radiobutton(wait_type_frame, text="Fixed", variable=self.wait_type, value="Fixed", command=self.on_wait_type_change).pack(side="left")
        ttk.Radiobutton(wait_type_frame, text="Random", variable=self.wait_type, value="Random", command=self.on_wait_type_change).pack(side="left")
        wait_type_frame.pack(fill="x", pady=(0,5))

        # --- Fixed Wait Frame ---
        self.fixed_wait_frame = ttk.Frame(wait_frame)
        ttk.Label(self.fixed_wait_frame, text="Wait (sec):").pack(side="left", padx=5)
        ttk.Entry(self.fixed_wait_frame, textvariable=self.fixed_wait, width=7).pack(side="left")

        # --- Random Wait Frame ---
        self.random_wait_frame = ttk.Frame(wait_frame)
        ttk.Label(self.random_wait_frame, text="Min (sec):").pack(side="left", padx=5)
        ttk.Entry(self.random_wait_frame, textvariable=self.min_wait, width=7).pack(side="left")
        ttk.Label(self.random_wait_frame, text="Max (sec):").pack(side="left", padx=(10,5))
        ttk.Entry(self.random_wait_frame, textvariable=self.max_wait, width=7).pack(side="left")

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
                "search_region": self.search_region,
                "on_failure": {}
            }

            # --- Save On Failure settings ---
            on_failure_policy = self.on_failure_policy.get()
            step['on_failure']['policy'] = on_failure_policy
            if on_failure_policy == 'Retry':
                try:
                    step['on_failure']['retries'] = int(self.on_failure_retries.get())
                except ValueError:
                    messagebox.showerror("Invalid Input", "'On Failure' retries must be an integer.")
                    return

            action_type = step['action_type']
            if action_type == 'Type':
                step['action_params']['text'] = self.text_to_type.get()
            elif action_type == 'Key Combo':
                step['action_params']['key_combo'] = self.key_combo_text.get()
            elif action_type == 'Set Variable':
                step['action_params']['variable_name'] = self.variable_name.get()
                step['action_params']['variable_value'] = self.variable_value.get()
            elif action_type == 'Modify Variable':
                step['action_params']['modify_variable_name'] = self.modify_variable_name.get()
                step['action_params']['modify_variable_operation'] = self.modify_variable_operation.get()
                step['action_params']['modify_variable_value'] = self.modify_variable_value.get()
            elif action_type == 'OCR':
                step['action_params']['output_variable_name'] = self.output_variable_name.get()
                step['action_params']['ocr_region'] = self.ocr_region
                if not self.ocr_region:
                    messagebox.showerror("Invalid Input", "OCR region is not set for this step.")
                    return
            elif action_type == 'Click with Offset':
                try:
                    step['action_params']['click_offset_x'] = int(self.simple_click_offset_x.get())
                    step['action_params']['click_offset_y'] = int(self.simple_click_offset_y.get())
                except ValueError:
                    messagebox.showerror("Invalid Input", "Click offsets must be integers.")
                    return
            elif action_type == 'Scroll':
                try:
                    step['action_params']['scroll_direction'] = self.scroll_direction.get()
                    step['action_params']['scroll_amount'] = int(self.scroll_amount.get())
                except ValueError:
                    messagebox.showerror("Invalid Input", "Scroll amount must be an integer.")
                    return

            if step['detection_mode'] == 'Color':
                step['detection_target'] = self.target_color_bgr
                step['detection_target_name'] = self.app._bgr_to_hex(self.target_color_bgr)
            else: # Image
                target_names = list(self.image_listbox.get(0, tk.END))
                if not target_names:
                    messagebox.showerror("Invalid Input", "No template images selected for this step.")
                    return
                # Save the list of full paths for later execution
                step['detection_target'] = [os.path.join("templates", name) for name in target_names]
                # Save just the names for display purposes
                step['detection_target_name'] = ", ".join(target_names)

        elif step_type == 'loop':
            try:
                repeat_count = int(self.loop_repeat_count.get())
            except ValueError:
                messagebox.showerror("Invalid Input", "Repetitions must be an integer.")
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
                    messagebox.showerror("Invalid Input", "Max retries must be an integer.")
                    return

                condition_target_names = list(self.until_image_listbox.get(0, tk.END))
                if not condition_target_names:
                    messagebox.showerror("Invalid Input", "At least one condition target image must be selected for an 'until' loop.")
                    return

                step['loop_condition_target'] = [os.path.join("templates", name) for name in condition_target_names]
                step['loop_condition_target_name'] = ", ".join(condition_target_names)
                step['max_retries'] = max_retries

        elif step_type == 'conditional_branch':
            step = {
                "step_type": "conditional_branch",
                "condition": {
                    "variable": self.if_variable.get(),
                    "operator": self.if_operator.get(),
                    "value": self.if_value.get()
                },
                "if_branch": self.if_branch,
                "else_branch": self.else_branch,
                "window_title": self.target_window_title.get(), # Retain for consistency, though not used by parent
            }

        elif step_type == 'wait':
            try:
                duration = float(self.wait_duration.get())
                if duration < 0:
                    messagebox.showerror("Invalid Input", "Wait duration cannot be negative.")
                    return
            except ValueError:
                messagebox.showerror("Invalid Input", "Wait duration must be a valid number.")
                return
            step = {
                "step_type": "wait",
                "duration": duration
            }
        elif step_type == 'time_based_condition':
            try:
                hour = int(self.time_condition_hour.get())
                minute = int(self.time_condition_minute.get())
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Hour must be between 0-23 and minute between 0-59.")
            except ValueError as e:
                messagebox.showerror("Invalid Input", f"Invalid time condition. {e}")
                return

            step = {
                "step_type": "time_based_condition",
                "time_condition": {"hour": hour, "minute": minute},
                "actions": self.time_based_actions,
                "window_title": self.target_window_title.get(),
            }
        else: # conditional_loop
            try:
                max_retries = int(self.max_retries.get())
            except ValueError:
                messagebox.showerror("Invalid Input", "Max retries must be an integer.")
                return

            # Primary Target
            primary_target_names = list(self.primary_image_listbox.get(0, tk.END))
            if not primary_target_names:
                messagebox.showerror("Invalid Input", "At least one primary target image must be selected.")
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
                    messagebox.showerror("Invalid Input", f"At least one fallback target image must be selected for a '{fallback_action_type}' action.")
                    return
                on_fail_dict["detection_mode"] = "Image"
                on_fail_dict["detection_target"] = [os.path.join("templates", name) for name in fallback_target_names]
                on_fail_dict["detection_target_name"] = ", ".join(fallback_target_names)

            if fallback_action_type == "Click with Offset":
                try:
                    on_fail_dict['action_params']['click_offset_x'] = int(self.fallback_drag_offset_x.get())
                    on_fail_dict['action_params']['click_offset_y'] = int(self.fallback_drag_offset_y.get())
                except ValueError:
                    messagebox.showerror("Invalid Input", "Fallback click offsets must be integers.")
                    return
            elif fallback_action_type == "Click and Drag":
                try:
                    on_fail_dict['action_params']['drag_offset_x'] = int(self.fallback_drag_offset_x.get())
                    on_fail_dict['action_params']['drag_offset_y'] = int(self.fallback_drag_offset_y.get())
                except ValueError:
                    messagebox.showerror("Invalid Input", "Fallback drag offsets must be integers.")
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
                    messagebox.showerror("Invalid Input", "Min wait time must be less than max wait time.")
                    return
        except ValueError:
            messagebox.showerror("Invalid Input", "Wait times must be valid numbers.")
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
        logging.info(f"Step editor window target set to: {title}")

    def sample_color(self):
        sampler = ColorSampler(self)
        self.wait_window(sampler)
        self.grab_set() # Re-grab focus

    def on_color_sampled(self, bgr_color):
        self.target_color_bgr = bgr_color
        hex_color = self.app._bgr_to_hex(bgr_color)
        self.color_preview.config(bg=hex_color)
        logging.info(f"Step color changed to {hex_color}")

    def take_screenshot(self):
        taker = ScreenshotTaker(self)
        self.wait_window(taker)
        self.grab_set() # Re-grab focus

    def on_screenshot_taken(self, image):
        logging.info("Screenshot captured for step.")
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
                logging.info(f"Template saved to {filepath}")

                # This method is now only called from the simple action editor,
                # so we can assume it's for the main image listbox.
                self.image_listbox.insert(tk.END, os.path.basename(filepath))

            except Exception as e:
                logging.error(f"Error saving template: {e}")

    def _get_region_display_text(self):
        region = self.search_region
        if region:
            return f"Region set: X={region['x']}, Y={region['y']}, W={region['width']}, H={region['height']}"
        return "Not set. The entire target window will be searched."

    def set_search_region(self):
        logging.info("Opening region selector...")
        selector = RegionSelector(self, self.on_region_selected)
        self.wait_window(selector)
        self.grab_set()

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
                    logging.info(f"Region coordinates adjusted to be relative to window '{win.title}'.")

        except Exception as e:
            logging.warning(f"Could not adjust region to window: {e}. Using absolute coordinates.")

        self.search_region = region
        self.search_region_label_var.set(self._get_region_display_text())
        logging.info(f"Search region set.")

    def clear_search_region(self):
        self.search_region = None
        self.search_region_label_var.set(self._get_region_display_text())
        logging.info("Search region has been cleared.")

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
        logging.info("Opening region selector for OCR...")
        selector = RegionSelector(self, self.on_ocr_region_selected)
        self.wait_window(selector)
        self.grab_set()

    def on_ocr_region_selected(self, region):
        self.ocr_region = region
        self.ocr_region_label_var.set(self._get_ocr_region_display_text())
        logging.info("OCR region set.")
