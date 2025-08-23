import tkinter as tk
from tkinter import ttk, messagebox, font
from PIL import Image, ImageTk, ImageDraw, ImageFont
import random
import time
import os

# --- UTILITY FUNCTIONS ---

def get_font_path(font_name="arial.ttf"):
    """Gets a path to a common font, checking system folders."""
    font_path = None
    if os.name == 'nt':  # Windows
        font_path = os.path.join(os.environ['SystemRoot'], 'Fonts', font_name)
    elif os.name == 'posix':  # macOS, Linux
        common_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Ubuntu
            '/System/Library/Fonts/Supplemental/Arial.ttf',      # macOS
            '/usr/share/fonts/corefonts/arial.ttf',              # Other Linux
        ]
        for path in common_paths:
            if os.path.exists(path):
                font_path = path
                break
    if not os.path.exists(font_path):
        return "sans-serif" # Fallback to a generic font
    return font_path

# --- IMAGE GENERATION ---

def create_text_image(text, size=(250, 80), bg_color=None, noise=False):
    """Creates an image with text, supporting different fonts, colors, and noise."""
    colors = ["#FFDDC1", "#C1FFD7", "#DDC1FF", "#FFC1C1", "#C1D7FF"]
    bg_color = bg_color if bg_color else random.choice(colors)
    img = Image.new("RGB", size, bg_color)
    draw = ImageDraw.Draw(img)

    # Add random noise
    if noise:
        for _ in range(random.randint(500, 1500)):
            x, y = random.randint(0, size[0]-1), random.randint(0, size[1]-1)
            noise_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            draw.point((x, y), fill=noise_color)

    font_size = random.randint(25, 35)
    try:
        # Use a real font file if available for better rendering
        font_path = get_font_path("arial.ttf")
        if font_path != "sans-serif":
            pil_font = ImageFont.truetype(font_path, font_size)
        else:
            pil_font = ImageFont.load_default() # Fallback
    except IOError:
        pil_font = ImageFont.load_default()

    text_color = random.choice(["#000000", "#D92027", "#3E4A61", "#5D2E8C"])
    draw.text((size[0]//2, size[1]//2), text, font=pil_font, fill=text_color, anchor="mm")

    return ImageTk.PhotoImage(img)


def create_fuzzy_image(size=(100, 100)):
    """Creates an image with a central shape that changes slightly."""
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    # Base shape
    draw.rectangle([20, 20, 80, 80], fill="blue")
    # Add a smaller, slightly offset shape to make it "fuzzy"
    offset_x = random.randint(-5, 5)
    offset_y = random.randint(-5, 5)
    draw.rectangle([45 + offset_x, 45 + offset_y, 55 + offset_x, 55 + offset_y], fill="yellow")
    return ImageTk.PhotoImage(img)

# --- MAIN APPLICATION ---

class TestBotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Advanced Bot Testbed")
        self.geometry("700x800")
        self.protocol("WM_DELETE_WINDOW", self.quit)

        self.images = {}
        self.dynamic_elements = {}
        self.refresh_all_content()

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (PageOCR, PageDynamicUI, PageScrolling):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("PageOCR")

    def refresh_all_content(self):
        # OCR Page content
        self.dynamic_number = random.randint(10000, 99999)
        self.images["ocr_easy"] = create_text_image(f"CODE: {self.dynamic_number}", bg_color="#E0E0E0")
        self.images["ocr_hard"] = create_text_image(f"ID: {self.dynamic_number}", bg_color="#333333", noise=True)

        # Dynamic UI Page content
        self.dynamic_elements["secret_button_visible"] = False
        self.dynamic_elements["conditional_image"] = random.choice(["success", "failure"])
        self.images["success"] = create_text_image("SUCCESS", size=(150,60), bg_color="lightgreen")
        self.images["failure"] = create_text_image("FAILURE", size=(150,60), bg_color="lightcoral")
        self.dynamic_elements["button_pos"] = random.choice([(0.2, 0.6), (0.4, 0.7), (0.6, 0.65)])

        # Scrolling Page content
        self.images["fuzzy"] = create_fuzzy_image()

        # Refresh visible frames
        for frame in getattr(self, "frames", {}).values():
            if hasattr(frame, "refresh_page"):
                frame.refresh_page()

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        self.title(f"Advanced Bot Testbed - {page_name}")


class PageOCR(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.counter_val = 0

        # --- Structure ---
        top_frame = ttk.Frame(self)
        top_frame.pack(pady=20, padx=20, fill="x")
        ttk.Label(top_frame, text="Page 1: OCR & Variables", font=("Arial", 18, "bold")).pack()
        ttk.Button(top_frame, text="Refresh Content", command=self.controller.refresh_all_content).pack(pady=5)

        # --- OCR Targets ---
        ocr_frame = ttk.LabelFrame(self, text="OCR Targets", padding=10)
        ocr_frame.pack(pady=10, padx=20, fill="x")
        ttk.Label(ocr_frame, text="Easy Target (Clean Background)").pack()
        self.ocr_easy_label = ttk.Label(ocr_frame)
        self.ocr_easy_label.pack(pady=5)

        ttk.Separator(ocr_frame, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(ocr_frame, text="Hard Target (Noisy Background, Different Font/Color)").pack()
        self.ocr_hard_label = ttk.Label(ocr_frame)
        self.ocr_hard_label.pack(pady=5)

        # --- Variable & Loop Test ---
        logic_frame = ttk.LabelFrame(self, text="Logic, Variables & Loops", padding=10)
        logic_frame.pack(pady=10, padx=20, fill="x")

        ttk.Label(logic_frame, text="Enter the 5-digit code from the images above:").pack()
        self.code_entry = ttk.Entry(logic_frame, font=("Courier", 12))
        self.code_entry.pack(pady=5)
        ttk.Button(logic_frame, text="Submit Code", command=self.check_code).pack()

        ttk.Separator(logic_frame, orient="horizontal").pack(fill="x", pady=15)

        ttk.Label(logic_frame, text="Click the button below to increment the counter.").pack()
        self.counter_btn = ttk.Button(logic_frame, text="Increment Counter", command=self.increment_counter)
        self.counter_btn.pack(pady=5)
        self.counter_label = ttk.Label(logic_frame, text="Counter: 0", font=("Arial", 14))
        self.counter_label.pack()

        # --- Navigation ---
        nav_frame = ttk.Frame(self)
        nav_frame.pack(side="bottom", pady=20)
        ttk.Button(nav_frame, text="Go to Page 2 (Dynamic UI)", command=lambda: controller.show_frame("PageDynamicUI")).pack()

        self.refresh_page()

    def refresh_page(self):
        self.ocr_easy_label.config(image=self.controller.images["ocr_easy"])
        self.ocr_hard_label.config(image=self.controller.images["ocr_hard"])
        self.counter_val = 0
        self.counter_label.config(text="Counter: 0")
        self.code_entry.delete(0, "end")

    def check_code(self):
        entered = self.code_entry.get()
        actual = str(self.controller.dynamic_number)
        if entered == actual:
            messagebox.showinfo("Success", "The code is correct!")
        else:
            messagebox.showerror("Failure", f"Incorrect. You entered {entered}, but the code was {actual}.")

    def increment_counter(self):
        self.counter_val += 1
        self.counter_label.config(text=f"Counter: {self.counter_val}")


class PageDynamicUI(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        top_frame = ttk.Frame(self)
        top_frame.pack(pady=20, padx=20, fill="x")
        ttk.Label(top_frame, text="Page 2: Dynamic UI & Conditionals", font=("Arial", 18, "bold")).pack()
        ttk.Button(top_frame, text="Refresh Content", command=self.controller.refresh_all_content).pack(pady=5)

        self.main_area = tk.Canvas(self, bg="#F0F0F0")
        self.main_area.pack(fill="both", expand=True, padx=20, pady=10)

        # --- Conditional Logic ---
        ttk.Label(self.main_area, text="Click 'Reveal' to show a conditional image.").place(relx=0.5, rely=0.1, anchor="center")
        self.reveal_btn = ttk.Button(self.main_area, text="Reveal Image", command=self.reveal_image)
        self.reveal_btn.place(relx=0.5, rely=0.15, anchor="center")
        self.conditional_image_label = ttk.Label(self.main_area)

        # --- Dynamic Positioning ---
        ttk.Label(self.main_area, text="This button moves on refresh.").place(relx=0.5, rely=0.55, anchor="center")
        self.moving_btn = ttk.Button(self.main_area, text="Find Me!")
        self.moving_btn.bind("<Button-1>", lambda e: messagebox.showinfo("Found!", "You clicked the moving button!"))

        # --- Hidden Element ---
        ttk.Label(self.main_area, text="Click the buttons in the correct order (A -> B -> C) to reveal a secret.").place(relx=0.5, rely=0.8, anchor="center")
        self.click_order = []
        btn_a = ttk.Button(self.main_area, text="A", command=lambda: self.log_click("A"))
        btn_a.place(relx=0.4, rely=0.85, anchor="center")
        btn_b = ttk.Button(self.main_area, text="B", command=lambda: self.log_click("B"))
        btn_b.place(relx=0.5, rely=0.85, anchor="center")
        btn_c = ttk.Button(self.main_area, text="C", command=lambda: self.log_click("C"))
        btn_c.place(relx=0.6, rely=0.85, anchor="center")
        self.secret_btn = ttk.Button(self.main_area, text="SECRET", command=lambda: messagebox.showinfo("Secret Found!", "You unlocked the secret!"))


        nav_frame = ttk.Frame(self)
        nav_frame.pack(side="bottom", pady=20)
        ttk.Button(nav_frame, text="Go to Page 1 (OCR)", command=lambda: controller.show_frame("PageOCR")).pack(side="left", padx=10)
        ttk.Button(nav_frame, text="Go to Page 3 (Scrolling)", command=lambda: controller.show_frame("PageScrolling")).pack(side="right", padx=10)

        self.refresh_page()

    def refresh_page(self):
        self.conditional_image_label.place_forget()
        self.secret_btn.place_forget()
        self.click_order = []
        pos = self.controller.dynamic_elements["button_pos"]
        self.moving_btn.place(relx=pos[0], rely=pos[1], anchor="center")

    def reveal_image(self):
        img_key = self.controller.dynamic_elements["conditional_image"]
        self.conditional_image_label.config(image=self.controller.images[img_key])
        self.conditional_image_label.place(relx=0.5, rely=0.3, anchor="center")

    def log_click(self, letter):
        self.click_order.append(letter)
        if len(self.click_order) > 3:
            self.click_order.pop(0)
        if self.click_order == ["A", "B", "C"]:
            self.secret_btn.place(relx=0.5, rely=0.92, anchor="center")


class PageScrolling(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        top_frame = ttk.Frame(self)
        top_frame.pack(pady=20, padx=20, fill="x")
        ttk.Label(top_frame, text="Page 3: Scrolling & Advanced Actions", font=("Arial", 18, "bold")).pack()
        ttk.Button(top_frame, text="Refresh Content", command=self.controller.refresh_all_content).pack(pady=5)

        # --- Scrollable Area ---
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        # --- Content for Scrolling ---
        for i in range(30):
            text = f"Item #{i+1}"
            if i == 24: text = "--- TARGET ITEM ---"
            label = ttk.Label(scrollable_frame, text=text, font=("Consolas", 12))
            label.pack(pady=8, padx=20, anchor="w")
            if i == 24:
                label.config(font=("Consolas", 14, "bold"), foreground="red")

        # --- Context Menu (Right-Click) Test ---
        ctx_frame = ttk.LabelFrame(scrollable_frame, text="Right-Click Test", padding=10)
        ctx_frame.pack(pady=20, padx=10, fill="x")
        self.ctx_label = ttk.Label(ctx_frame, text="Right-click me for options!", padding=20, relief="solid")
        self.ctx_label.pack()
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Option 1", command=lambda: self.ctx_action(1))
        self.context_menu.add_command(label="Option 2", command=lambda: self.ctx_action(2))
        self.ctx_label.bind("<Button-3>", self.show_context_menu)

        # --- Fuzzy Image Matching ---
        fuzzy_frame = ttk.LabelFrame(scrollable_frame, text="Fuzzy Image Matching", padding=10)
        fuzzy_frame.pack(pady=20, padx=10, fill="x")
        self.fuzzy_label = ttk.Label(fuzzy_frame)
        self.fuzzy_label.pack()

        # --- Navigation ---
        nav_frame = ttk.Frame(self)
        nav_frame.pack(side="bottom", pady=20)
        ttk.Button(nav_frame, text="Go to Page 2 (Dynamic UI)", command=lambda: controller.show_frame("PageDynamicUI")).pack()

        self.refresh_page()

    def refresh_page(self):
        self.fuzzy_label.config(image=self.controller.images["fuzzy"])

    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def ctx_action(self, option):
        messagebox.showinfo("Context Menu", f"You selected Option {option}.")


if __name__ == "__main__":
    app = TestBotApp()
    app.mainloop()
