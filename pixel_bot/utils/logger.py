import logging
import tkinter as tk

class ScrolledTextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.text_widget.config(state=tk.NORMAL)

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.see(tk.END)
        self.text_widget.update_idletasks()

def setup_logging(log_widget):
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Prevent handlers from being added multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- File Handler ---
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler('pixel_bot.log')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # --- Console Handler (for debugging) ---
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # --- GUI Handler ---
    gui_formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
    gui_handler = ScrolledTextHandler(log_widget)
    gui_handler.setFormatter(gui_formatter)
    logger.addHandler(gui_handler)
