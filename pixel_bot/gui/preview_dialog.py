import tkinter as tk
from tkinter import ttk
from ..core.preview_engine import ScriptPreviewEngine

class PreviewDialog(tk.Toplevel):
    def __init__(self, parent, sequence):
        super().__init__(parent)
        self.parent = parent
        self.sequence = sequence
        # The parent of this dialog is the App instance, which is what the engine needs
        self.preview_engine = ScriptPreviewEngine(self.parent)

        self.setup_dialog()
        self.generate_preview()

    def setup_dialog(self):
        """Create modern preview dialog interface"""
        self.title("Script Preview")
        self.geometry("900x700")
        self.configure(bg=self.parent.bg_color)
        self.transient(self.parent)
        self.grab_set()

        # Main frame
        main_frame = tk.Frame(self, bg=self.parent.bg_color)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        main_frame.columnconfigure(0, weight=3, uniform="group1")
        main_frame.columnconfigure(1, weight=2, uniform="group1")
        main_frame.rowconfigure(1, weight=1)

        # Header
        self.create_preview_header(main_frame)

        # Main content area
        self.create_preview_content(main_frame)

        # Footer
        self.create_preview_footer(main_frame)

    def create_preview_header(self, parent):
        header_frame = tk.Frame(parent, bg=self.parent.bg_color)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15))

        title_label = tk.Label(header_frame, text="Script Execution Preview",
                               bg=self.parent.bg_color, fg=self.parent.accent_color,
                               font=self.parent.font_manager.fonts["heading"])
        title_label.pack()

    def create_preview_content(self, parent):
        """Create the main preview visualization area"""
        # Left Panel - Timeline
        left_panel = self.parent.create_modern_card(parent, "📋 Execution Timeline")
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        # Use a Treeview for the timeline
        self.timeline_tree = ttk.Treeview(left_panel,
                                          columns=('Time', 'Action', 'Status'),
                                          show='headings')
        self.timeline_tree.heading("Time", text="Time")
        self.timeline_tree.heading("Action", text="Action")
        self.timeline_tree.heading("Status", text="Status")

        self.timeline_tree.column("Time", width=60, anchor='center')
        self.timeline_tree.column("Action", width=300, anchor='w')
        self.timeline_tree.column("Status", width=100, anchor='center')

        # Add a scrollbar
        scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=self.timeline_tree.yview)
        self.timeline_tree.configure(yscrollcommand=scrollbar.set)

        self.timeline_tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scrollbar.pack(side='right', fill='y')

        self.timeline_tree.bind("<<TreeviewSelect>>", self.show_step_details)

        # Right Panel - Details
        right_panel = self.parent.create_modern_card(parent, "🔍 Step Details")
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 0))

        self.details_text = tk.Text(right_panel,
                                    bg=self.parent.widget_bg_color,
                                    fg=self.parent.text_color,
                                    font=self.parent.font_manager.fonts["mono"],
                                    relief='flat', bd=0, wrap='word',
                                    padx=10, pady=10)
        self.details_text.pack(fill='both', expand=True, padx=1, pady=1)
        self.details_text.config(state=tk.DISABLED)

    def create_preview_footer(self, parent):
        footer_frame = tk.Frame(parent, bg=self.parent.bg_color)
        footer_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(15, 0))

        self.summary_label = tk.Label(footer_frame, text="Calculating...",
                                      bg=self.parent.bg_color, fg=self.parent.text_secondary,
                                      font=self.parent.font_manager.fonts["primary"])
        self.summary_label.pack(side='left')

        close_button = self.parent.create_modern_button(footer_frame, "Close", self.destroy, self.parent.button_color)
        close_button.pack(side='right')

    def generate_preview(self):
        """Generate comprehensive preview data"""
        self.preview_results = self.preview_engine.preview_sequence(self.sequence)
        self.populate_timeline()
        self.calculate_total_estimates()

    def populate_timeline(self):
        """Fill timeline with step previews"""
        # Clear existing items
        for item in self.timeline_tree.get_children():
            self.timeline_tree.delete(item)

        total_time = 0
        for result in self.preview_results:
            step_num = result['step_number']
            duration = result['estimated_duration']

            time_str = f"{total_time:.1f}s"
            action_desc = result['description']

            if result['potential_issues']:
                status = "⚠️ Warning"
                tag = 'warning'
            else:
                status = "✅ Ready"
                tag = 'ready'

            # Use step_num as a unique IID for each row
            self.timeline_tree.insert('', 'end',
                                      iid=step_num,
                                      text=f"Step {step_num}", # This won't be visible with show='headings'
                                      values=(time_str, action_desc, status),
                                      tags=(tag,))

            total_time += duration

        self.timeline_tree.tag_configure('warning', foreground=self.parent.warning_color)
        # A nice green for the 'Ready' status
        self.timeline_tree.tag_configure('ready', foreground='#32CD32')

    def calculate_total_estimates(self):
        total_duration = sum(r['estimated_duration'] for r in self.preview_results)
        total_issues = sum(1 for r in self.preview_results if r['potential_issues'])

        duration_str = f"{total_duration:.1f} seconds"
        issues_str = f"{total_issues} potential issue(s)"

        summary_text = f"Total Estimated Time: {duration_str}  |  Found: {issues_str}"
        self.summary_label.config(text=summary_text)

    def show_step_details(self, event=None):
        """Show detailed info when step is selected"""
        selection = self.timeline_tree.selection()
        if not selection:
            return

        item_id = int(selection[0])
        # The preview_results is a 0-indexed list, but our IID starts from 1
        result = self.preview_results[item_id - 1]

        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete('1.0', tk.END)

        details = f"--- Step {result['step_number']}: {result['step_type']} ---\n"
        details += f"Description: {result['description']}\n"
        details += f"Est. Duration: {result['estimated_duration']:.2f}s\n\n"

        details += "--- Potential Issues ---\n"
        if result['potential_issues']:
            for issue in result['potential_issues']:
                details += f"- {issue}\n"
        else:
            details += "No issues detected.\n"

        details += "\n--- Visual Info ---\n"
        if result['visual_info']:
            for key, value in result['visual_info'].items():
                if value: # Only show if there's data
                    details += f"{key.replace('_', ' ').title()}: {value}\n"
        else:
            details += "No visual elements for this step.\n"

        self.details_text.insert('1.0', details)
        self.details_text.config(state=tk.DISABLED)
