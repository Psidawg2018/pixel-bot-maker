import logging
import tkinter as tk
from tkinter import ttk
import time

import cv2
import mss
import numpy as np
from PIL import Image, ImageTk
from pynput import keyboard


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


class ActionPreview(tk.Toplevel):
    def __init__(self, master, x, y, width=None, height=None, duration=1000):
        super().__init__(master)

        self.attributes('-topmost', True)
        self.overrideredirect(True) # No window decorations
        self.after(duration, self.destroy)

        # For image matches, show a yellow border around the found area
        if width and height and width > 0 and height > 0:
            border_thickness = 3
            # The received x,y is the center of the found image.
            # We need to calculate the top-left corner for the window geometry.
            top_left_x = x - width // 2
            top_left_y = y - height // 2

            self.geometry(f"{width}x{height}+{top_left_x}+{top_left_y}")

            # Create a canvas that fills the window
            canvas = tk.Canvas(self, highlightthickness=0, bg='white')
            # Make the canvas background transparent
            self.wm_attributes('-transparentcolor', 'white')
            canvas.pack(fill="both", expand=True)

            # Draw a rectangle on the canvas, this will be the visible border
            canvas.create_rectangle(
                border_thickness // 2,
                border_thickness // 2,
                width - border_thickness // 2,
                height - border_thickness // 2,
                outline='yellow',
                width=border_thickness
            )
        else:
            # Fallback to the red dot for color finds or other point-based actions
            size = 30
            self.geometry(f"{size}x{size}+{x - size // 2}+{y - size // 2}")
            self.attributes('-alpha', 0.6)
            dot_canvas = tk.Canvas(self, bg='red', highlightthickness=0)
            dot_canvas.pack(fill="both", expand=True)

class HotkeyChangeDialog(tk.Toplevel):
    def __init__(self, master, callback):
        super().__init__(master)
        self.master = master
        self.callback = callback
        self.title("Set Hotkey")
        self.geometry("300x150")
        self.configure(bg=self.master.bg_color)
        self.transient(self.master)
        self.grab_set()

        self.hotkey_str = tk.StringVar(value="Press any key...")

        ttk.Label(self, text="Press any key to set it as the new hotkey.", wraplength=280).pack(pady=10)
        ttk.Label(self, textvariable=self.hotkey_str, style="Card.TLabel", width=20, font=("Arial", 12), anchor="center").pack(pady=10, ipady=10)
        ttk.Button(self, text="Cancel", command=self.on_close).pack(pady=10)

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
                # Use the callback to update the main app
                self.callback(key_name)
        except Exception as e:
            logging.error(f"Could not set hotkey: {e}")
        finally:
            self.after(100, self.on_close)

    def on_close(self):
        if self.listener.running:
            self.listener.stop()
        self.destroy()
