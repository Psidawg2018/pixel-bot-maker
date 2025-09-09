import tkinter as tk
import logging

class PreviewOverlay(tk.Toplevel):
    """Overlay window that shows preview steps on actual screen"""
    def __init__(self, parent, sequence):
        super().__init__(parent)
        logging.info("Initializing Live Preview Overlay...")
        self.parent = parent
        self.sequence = sequence

        self.setup_overlay()
        # Use the preview engine to get visual info
        self.preview_engine = self.parent.preview_engine
        logging.info(f"Live Preview: Received sequence with {len(self.sequence)} steps.")
        self.preview_results = self.preview_engine.preview_sequence(self.sequence)
        logging.info(f"Live Preview: Generated {len(self.preview_results)} preview results.")

        self.run_live_preview()

    def setup_overlay(self):
        """Create transparent overlay for visual preview"""
        self.attributes('-fullscreen', True)
        self.attributes('-alpha', 0.6) # A bit of transparency
        self.attributes('-topmost', True)
        self.configure(bg='grey')
        self.wm_attributes('-transparentcolor', 'grey')

        self.canvas = tk.Canvas(self, bg='grey', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        # Instructions
        self.canvas.create_text(
            self.winfo_screenwidth() / 2, 30,
            text="Live Preview Running... Press ESC to close.",
            fill="white", font=("Segoe UI", 16, "bold")
        )

        self.bind("<Escape>", lambda e: self.destroy())

    def run_live_preview(self):
        logging.info("Live Preview: Starting sequence.")
        self.after(500, self._preview_step, 0)

    def _preview_step(self, index):
        if index >= len(self.preview_results):
            logging.info("Live Preview: End of sequence. Closing overlay.")
            self.destroy()
            return

        logging.info(f"Live Preview: Displaying step {index + 1}.")
        self.canvas.delete("preview_element") # Clear only the previous preview drawing

        result = self.preview_results[index]
        visual_info = result.get('visual_info', {})
        region = visual_info.get('search_region') or visual_info.get('ocr_region')

        if region:
            # Note: these are absolute screen coordinates
            x, y, w, h = region['x'], region['y'], region['width'], region['height']

            # Draw a highlighted rectangle
            self.canvas.create_rectangle(
                x, y, x + w, y + h,
                outline='cyan', width=4,
                tags="preview_element"
            )
            # Add a semi-transparent fill
            self.canvas.create_rectangle(
                x, y, x + w, y + h,
                fill='blue', stipple='gray50',
                outline='',
                tags="preview_element"
            )

            # Display step description
            desc_text = f"Step {index + 1}: {result['description']}"
            text_x, text_y = x + w / 2, y + h + 20

            # Simple bounds check to keep text on screen
            if text_y > self.winfo_screenheight() - 50:
                text_y = y - 20

            self.canvas.create_text(
                text_x, text_y, text=desc_text,
                fill='white', font=("Segoe UI", 12, "bold"),
                tags="preview_element"
            )

        # Schedule next step
        self.after(1500, self._preview_step, index + 1)
