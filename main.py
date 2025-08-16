import tkinter as tk
from tkinter import scrolledtext, colorchooser, filedialog
import time

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
from automation import click_at

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pixel Bot")
        self.geometry("400x650")

        # --- Color Theme ---
        self.bg_color = "#2C3E50"
        self.widget_bg_color = "#34495E"
        self.text_color = "#ECF0F1"
        self.button_color = "#3498DB"
        self.button_text_color = "#ECF0F1"

        self.configure(bg=self.bg_color)

        self.running = False
        self.scan_job = None
        self.hotkey_listener = None
        self.target_window_title = None
        self.selected_template_path = None
        self.target_color_bgr = [0, 0, 255] # Default to Red

        # Ensure templates directory exists
        if not os.path.exists("templates"):
            os.makedirs("templates")

        # --- WIDGET CREATION ORDER IS IMPORTANT ---
        # 1. Create Log Area first, so other widgets can log during init.
        self.log_area = scrolledtext.ScrolledText(
            self, width=45, height=10,
            bg=self.widget_bg_color, fg=self.text_color,
            relief=tk.FLAT, insertbackground=self.text_color
        )

        # 2. Create main config frame
        config_frame = tk.Frame(self, bg=self.bg_color)
        config_frame.pack(pady=10, padx=10, fill="x", anchor="n")

        # 3. Create all other widgets inside the config frame
        # Mode Selection
        mode_frame = tk.Frame(config_frame, bg=self.bg_color)
        mode_frame.pack(fill="x", pady=5)
        self.detection_mode = tk.StringVar(value="Color")

        tk.Label(mode_frame, text="Mode:", bg=self.bg_color, fg=self.text_color).pack(side="left")

        color_radio = tk.Radiobutton(mode_frame, text="Color", variable=self.detection_mode, value="Color", bg=self.bg_color, fg=self.text_color, selectcolor=self.widget_bg_color, command=self.on_mode_change)
        color_radio.pack(side="left", padx=5)

        image_radio = tk.Radiobutton(mode_frame, text="Image", variable=self.detection_mode, value="Image", bg=self.bg_color, fg=self.text_color, selectcolor=self.widget_bg_color, command=self.on_mode_change)
        image_radio.pack(side="left", padx=5)

        # Window Selection
        window_frame = tk.Frame(config_frame, bg=self.bg_color)
        window_frame.pack(fill="x", pady=(0, 5))
        self.select_window_button = tk.Button(
            window_frame, text="Select Window", command=self.open_window_selector,
            bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT
        )
        self.select_window_button.pack(side="left", expand=True, padx=(0, 5))

        self.window_label = tk.Label(
            window_frame, text="Window: (None Selected)",
            bg=self.bg_color, fg=self.text_color, wraplength=180, justify="left"
        )
        self.window_label.pack(side="left", expand=True, padx=(5, 0))

        # Color Selection
        self.color_config_frame = tk.Frame(config_frame, bg=self.bg_color)

        color_buttons_frame = tk.Frame(self.color_config_frame, bg=self.bg_color)
        color_buttons_frame.pack(side="left", expand=True, fill="x")

        self.sample_color_button = tk.Button(
            color_buttons_frame, text="Sample Color", command=self.open_color_sampler,
            bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT
        )
        self.sample_color_button.pack(fill="x", pady=(0, 5))

        self.select_color_button = tk.Button(
            color_buttons_frame, text="Select from Palette", command=self.open_color_picker,
            bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT
        )
        self.select_color_button.pack(fill="x")

        color_display_frame = tk.Frame(self.color_config_frame, bg=self.bg_color)
        color_display_frame.pack(side="left", expand=True, padx=(10, 0))

        self.color_preview = tk.Frame(color_display_frame, bg="#FF0000", width=25, height=25, relief=tk.SUNKEN, borderwidth=1)
        self.color_preview.pack()
        self.color_label = tk.Label(
            color_display_frame, text="#FF0000",
            bg=self.bg_color, fg=self.text_color
        )
        self.color_label.pack(pady=5)

        # Template Frame
        self.template_config_frame = tk.Frame(config_frame, bg=self.bg_color)

        self.screenshot_button = tk.Button(
            self.template_config_frame, text="Take Screenshot for Template", command=self.open_screenshot_taker,
            bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT
        )
        self.screenshot_button.pack(fill="x", pady=(0, 5))

        template_selection_frame = tk.Frame(self.template_config_frame, bg=self.bg_color)
        template_selection_frame.pack(fill="x", pady=(5, 0))

        self.template_var = tk.StringVar(self)
        self.template_dropdown = tk.OptionMenu(template_selection_frame, self.template_var, "", command=self.on_template_selected)
        self.template_dropdown.config(bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT)
        self.template_dropdown["menu"].config(bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT)
        self.template_dropdown.pack(side="left", expand=True, fill="x")

        self.refresh_templates_button = tk.Button(
            template_selection_frame, text="Refresh", command=self.update_template_list,
            bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT
        )
        self.refresh_templates_button.pack(side="left", padx=(5, 0))

        self.template_preview = tk.Label(self.template_config_frame, bg=self.widget_bg_color)
        self.template_preview.pack(pady=10, fill="x")

        # 4. Pack the log area and start button at the end
        self.start_button = tk.Button(
            self, text="Start Bot", command=self.toggle_bot,
            bg=self.button_color, fg=self.button_text_color,
            activebackground="#2980B9", activeforeground=self.text_color,
            relief=tk.FLAT, padx=10, pady=5
        )
        self.start_button.pack(pady=10)
        self.log_area.pack(pady=10, padx=10)

        # 5. Now that all widgets exist, set initial state
        self.log("Welcome! Press 'Start Bot' to begin.")
        self.update_template_list()
        self.on_mode_change() # Set initial UI state based on mode

    def on_mode_change(self, *args):
        mode = self.detection_mode.get()
        if mode == "Color":
            self.template_config_frame.pack_forget()
            self.color_config_frame.pack(fill="x", pady=10)
        elif mode == "Image":
            self.color_config_frame.pack_forget()
            self.template_config_frame.pack(fill="x", pady=10)

    def toggle_bot(self):
        if self.running:
            # --- STOP THE BOT ---
            self.running = False
            self.start_button.config(text="Start Bot")
            if self.scan_job:
                self.after_cancel(self.scan_job)
            self.scan_job = None

            if self.hotkey_listener:
                self.hotkey_listener.stop()
            self.hotkey_listener = None

            self.log("Bot stopped by user.")
            self.deiconify()
        else:
            # --- START THE BOT ---
            self.running = True
            self.start_button.config(text="Stop Bot")
            self.start_hotkey_listener()
            self.withdraw()
            self.run_scan_loop()

    def run_scan_loop(self):
        if not self.running:
            return

        if not self.target_window_title:
            self.log("Error: No target window selected. Stopping bot.")
            self.toggle_bot()
            return

        try:
            target_windows = gw.getWindowsWithTitle(self.target_window_title)
            if not target_windows:
                self.log(f"Error: Window '{self.target_window_title}' not found. Stopping bot.")
                self.toggle_bot()
                return
            target_window = target_windows[0]
            scan_region = {'top': target_window.top, 'left': target_window.left, 'width': target_window.width, 'height': target_window.height}
        except Exception as e:
            self.log(f"Error getting window details: {e}. Stopping bot.")
            self.toggle_bot()
            return

        self.log(f"Scanning window '{self.target_window_title}'...")

        haystack_img = capture_screen(scan_region)

        target_pos = None
        mode = self.detection_mode.get()

        if mode == "Color":
            locations = find_color(haystack_img, self.target_color_bgr)
            if locations:
                target_pos = locations[0]
                self.log(f"SUCCESS: Found target color at {target_pos} (relative).")

        elif mode == "Image":
            if not self.selected_template_path:
                self.log("Error: No template image selected. Stopping bot.")
                self.toggle_bot()
                return

            try:
                needle_img = cv2.imread(self.selected_template_path, cv2.IMREAD_UNCHANGED)
                if needle_img is None:
                    raise IOError("Template image could not be read.")
            except Exception as e:
                self.log(f"Error loading template image: {e}")
                self.toggle_bot()
                return

            target_pos = find_image(haystack_img, needle_img)
            if target_pos:
                self.log(f"SUCCESS: Found template image at {target_pos} (relative).")

        if target_pos:
            abs_x = scan_region['left'] + target_pos[0]
            abs_y = scan_region['top'] + target_pos[1]

            self.log(f"Performing click at absolute position ({abs_x}, {abs_y}).")
            click_at(abs_x, abs_y)

            self.log("Action complete. Stopping bot.")
            self.toggle_bot()

        else:
            self.log("Target not found. Re-scanning in 2 seconds...")
            self.scan_job = self.after(2000, self.run_scan_loop)

    def open_area_selector(self):
        self.log("Opening area selector...")
        AreaSelector(self)

    def on_area_selected(self, region):
        self.log(f"New scan area selected: {region}")
        # self.scan_region = region # This is now dynamic based on window
        self.area_label.config(
            text=f"Area: {region['width']}x{region['height']} at ({region['left']},{region['top']})"
        )

    def open_window_selector(self):
        self.log("Opening window selector...")
        WindowSelector(self)

    def on_window_selected(self, title):
        self.log(f"Target window set to: {title}")
        self.target_window_title = title
        display_title = (title[:25] + '...') if len(title) > 25 else title
        self.window_label.config(text=f"Window: {display_title}")

    def open_screenshot_taker(self):
        self.log("Opening screenshot taker...")
        ScreenshotTaker(self)

    def on_screenshot_taken(self, image):
        self.log("Screenshot captured.")
        filepath = filedialog.asksaveasfilename(
            initialdir="templates",
            title="Save Template",
            filetypes=(("PNG files", "*.png"), ("All files", "*.*")),
            defaultextension=".png"
        )
        if filepath:
            try:
                cv2.imwrite(filepath, image)
                self.log(f"Template saved to {filepath}")
                self.update_template_list() # Refresh the list after saving
            except Exception as e:
                self.log(f"Error saving template: {e}")

    def open_color_sampler(self):
        self.log("Opening color sampler...")
        ColorSampler(self)

    def on_color_sampled(self, bgr_color):
        self.log(f"New color sampled: BGR={bgr_color}")
        self.target_color_bgr = bgr_color
        hex_color = self._bgr_to_hex(bgr_color)
        self.color_preview.config(bg=hex_color)
        self.color_label.config(text=hex_color)

    def open_color_picker(self):
        chosen_color = colorchooser.askcolor(color=self.color_label.cget("text"))
        if chosen_color and chosen_color[0] and chosen_color[1]:
            rgb, hex_color = chosen_color
            self.target_color_bgr = [rgb[2], rgb[1], rgb[0]]
            self.log(f"New target color selected: {hex_color.upper()}")
            self.color_preview.config(bg=hex_color)
            self.color_label.config(text=hex_color.upper())

    def update_template_list(self):
        self.log("Refreshing template list...")
        menu = self.template_dropdown["menu"]
        menu.delete(0, "end")

        try:
            templates = [f for f in os.listdir("templates") if f.endswith(".png")]
            if templates:
                for template in templates:
                    menu.add_command(label=template, command=lambda value=template: self.template_var.set(value))
                self.template_var.set(templates[0])
                self.on_template_selected(templates[0])
            else:
                self.template_var.set("No templates found")
                self.selected_template_path = None
                self.template_preview.config(image=None)
        except FileNotFoundError:
            self.template_var.set("No templates found")
            self.selected_template_path = None
            self.template_preview.config(image=None)


    def on_template_selected(self, template_name):
        self.log(f"Template selected: {template_name}")
        if template_name == "No templates found":
            self.selected_template_path = None
            self.template_preview.config(image=None)
            return

        self.selected_template_path = os.path.join("templates", template_name)

        try:
            img = Image.open(self.selected_template_path)
            max_size = 100
            img.thumbnail((max_size, max_size))
            photo = ImageTk.PhotoImage(img)
            self.template_preview.config(image=photo)
            self.template_preview.image = photo
        except Exception as e:
            self.log(f"Error loading preview: {e}")
            self.template_preview.config(image=None)

    def _bgr_to_hex(self, bgr_color):
        b, g, r = bgr_color
        return f"#{r:02x}{g:02x}{b:02x}".upper()

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

class WindowSelector(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.title("Select a Window")
        self.geometry("400x400")
        self.configure(bg=self.master.bg_color)
        label = tk.Label(self, text="Select the target window:", bg=self.master.bg_color, fg=self.master.text_color)
        label.pack(pady=10)
        list_frame = tk.Frame(self)
        list_frame.pack(pady=5, padx=10, fill="both", expand=True)
        self.listbox = tk.Listbox(list_frame, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.window_titles = [title for title in gw.getAllTitles() if title and title != self.master.title()]
        for title in self.window_titles:
            self.listbox.insert(tk.END, title)
        button_frame = tk.Frame(self, bg=self.master.bg_color)
        button_frame.pack(pady=10)
        select_button = tk.Button(button_frame, text="Select", command=self.on_select, bg=self.master.button_color, fg=self.master.button_text_color, relief=tk.FLAT)
        select_button.pack(side="left", padx=10)
        cancel_button = tk.Button(button_frame, text="Cancel", command=self.on_cancel, bg=self.master.widget_bg_color, fg=self.master.text_color, relief=tk.FLAT)
        cancel_button.pack(side="left", padx=10)
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.transient(self.master)
        self.grab_set()

    def on_select(self):
        selection_indices = self.listbox.curselection()
        if not selection_indices:
            return
        selected_title = self.listbox.get(selection_indices[0])
        self.destroy()
        self.master.on_window_selected(selected_title)

    def on_cancel(self):
        self.destroy()

class ColorSampler(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.attributes("-fullscreen", True)
        self.attributes("-alpha", 0.1)
        self.attributes("-topmost", True)
        self.canvas = tk.Canvas(self, cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)

    def on_mouse_press(self, event):
        x, y = event.x_root, event.y_root
        with mss.mss() as sct:
            region = {'top': y, 'left': x, 'width': 1, 'height': 1}
            img = sct.grab(region)
        bgr_color = np.array(img)[0, 0]
        b, g, r = bgr_color[0], bgr_color[1], bgr_color[2]
        self.master.on_color_sampled([b, g, r])
        self.destroy()

class AreaSelector(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.attributes("-fullscreen", True)
        self.attributes("-alpha", 0.3)
        self.attributes("-topmost", True)
        self.configure(bg="grey")
        self.canvas = tk.Canvas(self, cursor="cross", bg="grey")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)

    def on_mouse_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = None

    def on_mouse_drag(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, cur_x, cur_y,
            outline='red', width=2, fill="red"
        )
        self.canvas.itemconfig(self.rect, stipple="gray12")

    def on_mouse_release(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        left = int(min(self.start_x, end_x))
        top = int(min(self.start_y, end_y))
        width = int(abs(end_x - self.start_x))
        height = int(abs(end_y - self.start_y))
        region = {'top': top, 'left': left, 'width': width, 'height': height}
        self.destroy()
        self.master.on_area_selected(region)

class ScreenshotTaker(AreaSelector):
    """A tool to take a screenshot of a region of the screen."""
    def on_mouse_release(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        left = int(min(self.start_x, end_x))
        top = int(min(self.start_y, end_y))
        width = int(abs(end_x - self.start_x))
        height = int(abs(end_y - self.start_y))

        self.withdraw()
        region = {'top': top, 'left': left, 'width': width, 'height': height}
        image = capture_screen(region)
        self.master.on_screenshot_taken(image)
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
