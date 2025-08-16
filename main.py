import tkinter as tk
from tkinter import scrolledtext
import time

# Import our custom modules
from screen_capture import capture_screen
from image_analyzer import find_color, find_text
from automation import click_at

# --- Constants for the MVP ---
# The screen region we will monitor (top, left, width, height)
SCAN_REGION = {'top': 0, 'left': 0, 'width': 500, 'height': 500}

# The color we are looking for (Red in BGR format for OpenCV)
TARGET_COLOR_BGR = [0, 0, 255]

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pixel Bot")
        self.geometry("400x350")

        self.running = False
        self.scan_job = None
        self.test_window = None

        self.start_button = tk.Button(self, text="Start Bot", command=self.toggle_bot)
        self.start_button.pack(pady=10)

        self.log_area = scrolledtext.ScrolledText(self, width=45, height=18)
        self.log_area.pack(pady=10)
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

        self.log(f"Scanning region: {SCAN_REGION}")

        # 1. Capture the screen area
        image = capture_screen(SCAN_REGION)

        # 2. Analyze for the color
        locations = find_color(image, TARGET_COLOR_BGR)

        if locations:
            target_pos = locations[0]
            self.log(f"SUCCESS: Found target color at {target_pos} (relative).")

            # Convert relative coordinates to absolute screen coordinates
            abs_x = SCAN_REGION['left'] + target_pos[0]
            abs_y = SCAN_REGION['top'] + target_pos[1]

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

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_area.see(tk.END)

if __name__ == "__main__":
    # Note: This app needs a virtual display to run in this environment.
    # The Xvfb instance started earlier should still be running.
    app = App()
    app.mainloop()
