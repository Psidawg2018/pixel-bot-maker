import tkinter as tk
from tkinter import ttk
import pygetwindow as gw

class WindowSelector(tk.Toplevel):
    def __init__(self, master, is_splash=False):
        super().__init__(master)
        from pixel_bot.gui.main_window import App

        self.master = master
        self.is_splash = is_splash
        self.title("Select Target Window")
        self.geometry("350x450")

        # Find the root App instance for theming
        app = self.master
        while not isinstance(app, App):
            app = app.master

        self.configure(bg=app.bg_color)
        self.transient(master)
        self.grab_set()

        self.listbox = tk.Listbox(self, bg=app.widget_bg_color, fg=app.text_color, relief=tk.FLAT)
        self.listbox.pack(pady=10, padx=10, fill="both", expand=True)

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Refresh", command=self.populate_windows).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Select", command=self.on_select, style="Accent.TButton").pack(side="left", padx=5)

        cancel_text = "Quit" if self.is_splash and isinstance(self.master, App) else "Cancel"
        ttk.Button(button_frame, text=cancel_text, command=self.on_cancel).pack(side="left", padx=5)

        self.populate_windows()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

    def populate_windows(self):
        self.listbox.delete(0, tk.END)
        titles = sorted([title for title in gw.getAllTitles() if title])
        for title in titles:
            self.listbox.insert(tk.END, title)

    def on_select(self):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            return
        selected_title = self.listbox.get(selected_indices[0])
        if hasattr(self.master, 'on_window_selected'):
            self.master.on_window_selected(selected_title)
        self.destroy()

    def on_cancel(self):
        from pixel_bot.gui.main_window import App

        # If this is the initial selection dialog and no selection has been made, closing it quits the app.
        if self.is_splash and isinstance(self.master, App) and not self.master.target_window_title.get():
            self.master.destroy()
        else:
            self.destroy()
