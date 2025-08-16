import tkinter as tk
from tkinter import scrolledtext, colorchooser
import time

# Import our custom modules
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
        self.test_window = None
        # Set default scan region and color
        self.scan_region = {'top': 0, 'left': 0, 'width': 500, 'height': 500}
        self.target_color_bgr = [0, 0, 255] # Default to Red

        # --- Configuration Frame ---
        config_frame = tk.Frame(self, bg=self.bg_color)
        config_frame.pack(pady=10, padx=10, fill="x", anchor="n")

        # Area Selection
        area_frame = tk.Frame(config_frame, bg=self.bg_color)
        area_frame.pack(fill="x")
        self.select_area_button = tk.Button(
            area_frame, text="Select Scan Area", command=self.open_area_selector,
            bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT
        )
        self.select_area_button.pack(side="left", expand=True, padx=(0, 5))

        self.area_label = tk.Label(
            area_frame, text=f"Area: {self.scan_region['width']}x{self.scan_region['height']}",
            bg=self.bg_color, fg=self.text_color
        )
        self.area_label.pack(side="left", expand=True, padx=(5, 0))

        # Color Selection
        color_frame = tk.Frame(config_frame, bg=self.bg_color)
        color_frame.pack(fill="x", pady=10)
        self.select_color_button = tk.Button(
            color_frame, text="Select Target Color", command=self.open_color_picker,
            bg=self.widget_bg_color, fg=self.text_color, relief=tk.FLAT
        )
        self.select_color_button.pack(side="left", expand=True, padx=(0, 5))

        self.color_preview = tk.Frame(color_frame, bg="#FF0000", width=20, height=20, relief=tk.SUNKEN, borderwidth=1)
        self.color_preview.pack(side="left", padx=5)
        self.color_label = tk.Label(
            color_frame, text="#FF0000",
            bg=self.bg_color, fg=self.text_color, width=15
        )
        self.color_label.pack(side="left", expand=True, padx=(5, 0))


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
            self.log("Bot stopped by user.")
            if self.test_window:
                self.test_window.destroy()
                self.test_window = None
        else:
            # --- START THE BOT ---
            self.running = True
            self.start_button.config(text="Stop Bot")
            self.log("Bot started...")
            self.create_test_window()
            self.run_scan_loop()

    def create_test_window(self):
        """Creates a small red window to act as a target for the bot."""
        self.log("Creating a red target window at (100, 100).")
        self.test_window = tk.Toplevel(self)
        self.test_window.title("Target")
        self.test_window.geometry("50x50+100+100") # 50x50 window at x=100, y=100
        self.test_window.configure(bg="red")
        # Prevent user from closing it manually, only bot can
        self.test_window.protocol("WM_DELETE_WINDOW", lambda: None)

    def run_scan_loop(self):
        if not self.running:
            return

        self.log(f"Scanning region: {self.scan_region}")

        # 1. Capture the screen area
        image = capture_screen(self.scan_region)

        # 2. Analyze for the color
        locations = find_color(image, self.target_color_bgr)

        if locations:
            target_pos = locations[0]
            self.log(f"SUCCESS: Found target color at {target_pos} (relative).")

            # Convert relative coordinates to absolute screen coordinates
            abs_x = self.scan_region['left'] + target_pos[0]
            abs_y = self.scan_region['top'] + target_pos[1]

            # 3. Perform the action
            self.log(f"Performing click at absolute position ({abs_x}, {abs_y}).")
            click_at(abs_x, abs_y)

            # For the MVP, we stop the bot after one successful action
            self.log("Action complete. Stopping bot.")
            self.toggle_bot() # This will toggle the state to off

        else:
            self.log("Target color not found. Re-scanning in 2 seconds...")
            # 4. Schedule the next scan
            self.scan_job = self.after(2000, self.run_scan_loop)

    def open_area_selector(self):
        self.log("Opening area selector...")
        # Hide main window
        self.withdraw()
        # Give a moment for window to hide
        self.after(100, lambda: AreaSelector(self))

    def on_area_selected(self, region):
        self.log(f"New scan area selected: {region}")
        self.scan_region = region
        self.area_label.config(
            text=f"Area: {region['width']}x{region['height']} at ({region['left']},{region['top']})"
        )
        # Show main window again
        self.deiconify()

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

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_area.see(tk.END)

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
