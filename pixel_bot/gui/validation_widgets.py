"""
This file will contain reusable GUI components for displaying validation results,
such as icons, tooltips, and summary panels.
"""
import tkinter as tk
from tkinter import ttk

class ValidationIcon(ttk.Label):
    """
    A label that shows an error, warning, or success icon.
    This can be expanded to load and display actual image icons.
    """
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        # For now, use text placeholders.
        # In the future, we can load images for these states.
        self.config(text="[ ]")

    def set_state(self, state):
        """Sets the icon based on the validation state."""
        if state == 'error':
            self.config(text="[E]", foreground="red")
        elif state == 'warning':
            self.config(text="[W]", foreground="orange")
        elif state == 'valid':
            self.config(text="[✓]", foreground="green")
        else:
            self.config(text="[ ]", foreground="white")
