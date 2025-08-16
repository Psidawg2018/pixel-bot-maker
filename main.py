import tkinter as tk
from tkinter import scrolledtext, colorchooser
import time

# Import our custom modules
import numpy as np
import mss
from pynput import keyboard
import threading
import pygetwindow as gw
from screen_capture import capture_screen
from image_analyzer import find_color, find_text
from automation import click_at

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pixel Bot")
        self.geometry("400x450")

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
        # Set default scan region and color
        self.target_color_bgr = [0, 0, 255] # Default to Red

        # --- Configuration Frame ---
        config_frame = tk.Frame(self, bg=self.bg_color)
        config_frame.pack(pady=10, padx=10, fill="x", anchor="n")

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

        # Area Selection (now disabled)
        area_frame = tk.Frame(config_frame, bg=self.bg_color)
        area_frame.pack(fill="x")
        self.select_area_button = tk.Button(
            area_frame, text="Select Scan Area", command=self.open_area_selector,
            bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT,
            state=tk.DISABLED
        )
        self.select_area_button.pack(side="left", expand=True, padx=(0, 5))

        self.area_label = tk.Label(
            area_frame, text="Area: (Set by Window)",
            bg=self.bg_color, fg=self.text_color
        )
        self.area_label.pack(side="left", expand=True, padx=(5, 0))

        # Color Selection
        color_frame = tk.Frame(config_frame, bg=self.bg_color)
        color_frame.pack(fill="x", pady=10)

        color_buttons_frame = tk.Frame(color_frame, bg=self.bg_color)
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

        color_display_frame = tk.Frame(color_frame, bg=self.bg_color)
        color_display_frame.pack(side="left", expand=True, padx=(10, 0))

        self.color_preview = tk.Frame(color_display_frame, bg="#FF0000", width=25, height=25, relief=tk.SUNKEN, borderwidth=1)
        self.color_preview.pack()
        self.color_label = tk.Label(
            color_display_frame, text="#FF0000",
            bg=self.bg_color, fg=self.text_color
        )
        self.color_label.pack(pady=5)


        self.start_button = tk.Button(
            self, text="Start Bot", command=self.toggle_bot,
            bg=self.button_color, fg=self.button_text_color,
            activebackground="#2980B9", activeforeground=self.text_color,
            relief=tk.FLAT, padx=10, pady=5
        )
        self.start_button.pack(pady=10)

        self.log_area = scrolledtext.ScrolledText(
            self, width=45, height=15,
            bg=self.widget_bg_color, fg=self.text_color,
            relief=tk.FLAT, insertbackground=self.text_color
        )
        self.log_area.pack(pady=10, padx=10)
        self.log("Welcome! Press 'Start Bot' to begin.")

    def toggle_bot(self):
        if self.running:
            # --- STOP THE BOT ---
            self.running = False
            self.start_button.config(text="Start Bot")
            if self.scan_job:
                self.after_cancel(self.scan_job)
                self.scan_job = None

            # Stop the hotkey listener
            if self.hotkey_listener:
                self.hotkey_listener.stop()
                self.hotkey_listener = None

            self.log("Bot stopped by user.")

            # Show the GUI
            self.deiconify()
        else:
            # --- START THE BOT ---
            self.running = True
            self.start_button.config(text="Stop Bot")

            self.start_hotkey_listener()

            # Hide the GUI
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

            # Use the first window found
            target_window = target_windows[0]

            # Get window geometry
            scan_region = {
                'top': target_window.top,
                'left': target_window.left,
                'width': target_window.width,
                'height': target_window.height
            }

        except Exception as e:
            self.log(f"Error getting window details: {e}. Stopping bot.")
            self.toggle_bot()
            return

        self.log(f"Scanning window '{self.target_window_title}' at {scan_region}")

        # 1. Capture the screen area
        image = capture_screen(scan_region)

        # 2. Analyze for the color
        locations = find_color(image, self.target_color_bgr)

        if locations:
            target_pos = locations[0]
            self.log(f"SUCCESS: Found target color at {target_pos} (relative).")

            # Convert relative coordinates to absolute screen coordinates
            abs_x = scan_region['left'] + target_pos[0]
            abs_y = scan_region['top'] + target_pos[1]

            # 3. Perform the action
            self.log(f"Performing click at absolute position ({abs_x}, {abs_y}).")
            click_at(abs_x, abs_y)

            # For the MVP, we stop the bot after one successful action
            self.log("Action complete. Stopping bot.")
            self.toggle_bot() # This will stop the bot and show the GUI

        else:
            self.log("Target color not found. Re-scanning in 2 seconds...")
            # 4. Schedule the next scan
            self.scan_job = self.after(2000, self.run_scan_loop)

    def open_area_selector(self):
        self.log("Opening area selector...")
        AreaSelector(self)

    def on_area_selected(self, region):
        self.log(f"New scan area selected: {region}")
        self.scan_region = region
        self.area_label.config(
            text=f"Area: {region['width']}x{region['height']} at ({region['left']},{region['top']})"
        )

    def open_window_selector(self):
        self.log("Opening window selector...")
        WindowSelector(self)

    def on_window_selected(self, title):
        self.log(f"Target window set to: {title}")
        self.target_window_title = title
        # Truncate title if too long for the label
        display_title = (title[:25] + '...') if len(title) > 25 else title
        self.window_label.config(text=f"Window: {display_title}")

    def open_color_sampler(self):
        self.log("Opening color sampler...")
        ColorSampler(self)

    def on_color_sampled(self, bgr_color):
        self.log(f"New color sampled: BGR={bgr_color}")
        self.target_color_bgr = bgr_color

        hex_color = self._bgr_to_hex(bgr_color)

        # Update GUI
        self.color_preview.config(bg=hex_color)
        self.color_label.config(text=hex_color)

    def open_color_picker(self):
        # The askcolor function returns a tuple: ((R, G, B), '#RRGGBB')
        chosen_color = colorchooser.askcolor(color=self.color_label.cget("text"))

        if chosen_color and chosen_color[0] and chosen_color[1]:
            rgb, hex_color = chosen_color

            # Convert RGB from color chooser (0-255) to BGR for OpenCV
            self.target_color_bgr = [rgb[2], rgb[1], rgb[0]]

            self.log(f"New target color selected: {hex_color.upper()}")

            # Update GUI
            self.color_preview.config(bg=hex_color)
            self.color_label.config(text=hex_color.upper())

    def _bgr_to_hex(self, bgr_color):
        """Converts a BGR color list to a hex string."""
        b, g, r = bgr_color
        return f"#{r:02x}{g:02x}{b:02x}".upper()

    def start_hotkey_listener(self):
        """Starts a background thread to listen for the F9 stop hotkey."""
        if self.hotkey_listener:
            return

        def on_press(key):
            if key == keyboard.Key.f9:
                # Schedule toggle_bot to be run in the main GUI thread
                # This is crucial for thread safety with tkinter
                self.after(0, self.toggle_bot)

        # The listener runs in its own thread, so we use a thread object
        self.hotkey_listener = keyboard.Listener(on_press=on_press)

        # Using a daemon thread to ensure it exits when the main app exits
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

        # Populate listbox
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

        # Make fullscreen, transparent, and stay on top
        self.attributes("-fullscreen", True)
        self.attributes("-alpha", 0.1) # Very transparent
        self.attributes("-topmost", True)

        self.canvas = tk.Canvas(self, cursor="cross")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)

    def on_mouse_press(self, event):
        x, y = event.x_root, event.y_root

        # Capture 1x1 pixel at the cursor's location
        with mss.mss() as sct:
            region = {'top': y, 'left': x, 'width': 1, 'height': 1}
            img = sct.grab(region)

        # mss gives BGRA, convert to NumPy array to get the color
        bgr_color = np.array(img)[0, 0]
        # Extract BGR and ignore Alpha channel
        b, g, r = bgr_color[0], bgr_color[1], bgr_color[2]

        # Pass color back to master
        # The master needs an on_color_sampled method
        self.master.on_color_sampled([b, g, r])

        # Close the sampler
        self.destroy()


class AreaSelector(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.start_x = None
        self.start_y = None
        self.rect = None

        # Make fullscreen, transparent, and stay on top
        self.attributes("-fullscreen", True)
        self.attributes("-alpha", 0.3) # Transparency
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
        # We need to update the fill to be transparent
        # This is a bit of a hack for tkinter transparency on canvas items
        self.canvas.itemconfig(self.rect, stipple="gray12")


    def on_mouse_release(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)

        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        width = abs(end_x - self.start_x)
        height = abs(end_y - self.start_y)

        region = {
            'top': int(top),
            'left': int(left),
            'width': int(width),
            'height': int(height)
        }

        # Close the selector and pass data back to master
        self.destroy()
        self.master.on_area_selected(region)


if __name__ == "__main__":
    # Note: This app needs a virtual display to run in this environment.
    # The Xvfb instance started earlier should still be running.
    app = App()
    app.mainloop()
