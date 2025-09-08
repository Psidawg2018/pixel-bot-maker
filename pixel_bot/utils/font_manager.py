import tkinter.font as tkFont
import os

class FontManager:
    def __init__(self):
        self.fonts = {}
        self.load_custom_fonts()

    def load_custom_fonts(self):
        """Load Inter and JetBrains Mono with fallbacks"""
        try:
            # Try to load custom fonts from assets/fonts/
            # For now, we will use system fallbacks as per the instructions.
            # A future implementation could load the fonts from the assets directory.
            self.fonts = {
                "primary": ("Segoe UI", 10),      # Fallback for Inter
                "heading": ("Segoe UI", 12, "bold"),
                "mono": ("Consolas", 9),          # Fallback for JetBrains Mono
                "button": ("Segoe UI", 9)
            }
        except Exception:
            # If even system fonts fail, use tkinter's default fonts.
            # This ensures the application can always run.
            self.fonts = {
                "primary": tkFont.nametofont("TkDefaultFont").actual(),
                "heading": tkFont.nametofont("TkDefaultFont").actual(),
                "mono": tkFont.nametofont("TkTextFont").actual(),
                "button": tkFont.nametofont("TkDefaultFont").actual(),
            }
            if "bold" not in self.fonts["heading"]:
                self.fonts["heading"] = (self.fonts["heading"]["family"], self.fonts["heading"]["size"], "bold")

            print("Could not load custom or system fonts, falling back to tkinter defaults.")
