import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
import random, time


# Function to generate random placeholder images
def create_random_image(label, size=(200, 100)):
    colors = ["lightblue", "lightgreen", "lightyellow", "pink", "orange", "lavender"]
    color = random.choice(colors)

    img = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(img)
    text = f"{label}\n{random.randint(1000,9999)}"
    try:
        # Use anchor positioning for modern Pillow versions
        draw.text((size[0]//2, size[1]//2), text, fill="black", anchor="mm")
    except TypeError:
        # Fallback for older Pillow versions
        w, h = draw.textsize(text)
        draw.text(((size[0]-w)//2, (size[1]-h)//2), text, fill="black")
    return ImageTk.PhotoImage(img)


# Function to generate random text
def random_text():
    samples = [
        "The quick brown fox jumps over the lazy dog.",
        "Artificial Intelligence is reshaping the world.",
        "1234567890 OCR TEST DATA HERE.",
        "Python is a powerful language for automation.",
        "Every test should include some random noise.",
        "ZEBRAS and APPLES make good OCR stress tests.",
        "Current timestamp: " + time.strftime("%Y-%m-%d %H:%M:%S")
    ]
    return random.choice(samples)


class TestApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Robust OCR & Automation Test App")
        self.minsize(600, 700)

        # Store images (regenerate each refresh)
        self.images = {}
        self.refresh_content()

        # Container for multiple pages
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        self.frames = {}
        for Page in (PageOne, PageTwo, PageThree):
            frame = Page(parent=container, controller=self)
            self.frames[Page] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(PageOne)

    def refresh_content(self):
        self.images = {
            "page1": create_random_image("Page 1"),
            "page2": create_random_image("Page 2"),
            "page3": create_random_image("Page 3"),
        }
        self.random_text1 = random_text()
        self.random_text2 = random_text()
        self.random_text3 = random_text()

        # If pages exist, update them on refresh
        for frame in getattr(self, "frames", {}).values():
            if hasattr(frame, "refresh_page"):
                frame.refresh_page()

    def show_frame(self, page_class):
        frame = self.frames[page_class]
        frame.tkraise()


class PageOne(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.label_title = ttk.Label(self, text="This is Page 1", font=("Arial", 16))
        self.label_title.pack(pady=10)

        self.image_label = ttk.Label(self, image=controller.images["page1"])
        self.image_label.pack(pady=5)

        self.text_label = ttk.Label(self, text=controller.random_text1, wraplength=500)
        self.text_label.pack(pady=5)

        ttk.Label(self, text="Enter your name:").pack(pady=2)
        self.name_entry = ttk.Entry(self)
        self.name_entry.pack(pady=2)

        ttk.Button(self, text="Submit Name", command=self.submit_name).pack(pady=5)

        nav_frame = ttk.Frame(self)
        nav_frame.pack(pady=20)
        ttk.Button(nav_frame, text="Go to Page 2", command=lambda: controller.show_frame(PageTwo)).grid(row=0, column=0, padx=5)
        ttk.Button(nav_frame, text="Refresh Content", command=controller.refresh_content).grid(row=0, column=1, padx=5)

    def refresh_page(self):
        self.image_label.config(image=self.controller.images["page1"])
        self.text_label.config(text=self.controller.random_text1)

    def submit_name(self):
        name = self.name_entry.get()
        messagebox.showinfo("Submitted", f"Hello, {name}!")


class PageTwo(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ttk.Label(self, text="This is Page 2", font=("Arial", 16)).pack(pady=10)

        self.image_label = ttk.Label(self, image=controller.images["page2"])
        self.image_label.pack(pady=5)

        self.text_label = ttk.Label(self, text=controller.random_text2, wraplength=500)
        self.text_label.pack(pady=5)

        ttk.Label(self, text="Enter a number:").pack(pady=2)
        self.num_entry = ttk.Entry(self)
        self.num_entry.pack(pady=2)

        ttk.Button(self, text="Double It", command=self.double_number).pack(pady=5)

        nav_frame = ttk.Frame(self)
        nav_frame.pack(pady=20)
        ttk.Button(nav_frame, text="Back to Page 1", command=lambda: controller.show_frame(PageOne)).grid(row=0, column=0, padx=5)
        ttk.Button(nav_frame, text="Go to Page 3", command=lambda: controller.show_frame(PageThree)).grid(row=0, column=1, padx=5)
        ttk.Button(nav_frame, text="Refresh Content", command=controller.refresh_content).grid(row=0, column=2, padx=5)

    def refresh_page(self):
        self.image_label.config(image=self.controller.images["page2"])
        self.text_label.config(text=self.controller.random_text2)

    def double_number(self):
        try:
            val = int(self.num_entry.get())
            result = val * 2
            messagebox.showinfo("Result", f"Double is {result}")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number.")


class PageThree(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ttk.Label(self, text="This is Page 3", font=("Arial", 16)).pack(pady=10)

        self.image_label = ttk.Label(self, image=controller.images["page3"])
        self.image_label.pack(pady=5)

        self.text_label = ttk.Label(self, text=controller.random_text3, wraplength=500)
        self.text_label.pack(pady=5)

        # Checkboxes
        ttk.Label(self, text="Select your favorite fruits:").pack(pady=5)
        self.var_apple = tk.BooleanVar()
        self.var_banana = tk.BooleanVar()
        self.var_cherry = tk.BooleanVar()
        ttk.Checkbutton(self, text="Apple", variable=self.var_apple).pack(anchor="w")
        ttk.Checkbutton(self, text="Banana", variable=self.var_banana).pack(anchor="w")
        ttk.Checkbutton(self, text="Cherry", variable=self.var_cherry).pack(anchor="w")

        # Radio buttons
        ttk.Label(self, text="Choose your gender:").pack(pady=5)
        self.gender = tk.StringVar(value="None")
        ttk.Radiobutton(self, text="Male", variable=self.gender, value="Male").pack(anchor="w")
        ttk.Radiobutton(self, text="Female", variable=self.gender, value="Female").pack(anchor="w")
        ttk.Radiobutton(self, text="Other", variable=self.gender, value="Other").pack(anchor="w")

        # Text box
        ttk.Label(self, text="Enter a paragraph of text:").pack(pady=5)
        self.text_box = tk.Text(self, width=50, height=5)
        self.text_box.pack(pady=5)

        ttk.Button(self, text="Submit Form", command=self.submit_form).pack(pady=10)

        nav_frame = ttk.Frame(self)
        nav_frame.pack(pady=20)
        ttk.Button(nav_frame, text="Back to Page 2", command=lambda: controller.show_frame(PageTwo)).grid(row=0, column=0, padx=5)
        ttk.Button(nav_frame, text="Go to Page 1", command=lambda: controller.show_frame(PageOne)).grid(row=0, column=1, padx=5)
        ttk.Button(nav_frame, text="Refresh Content", command=controller.refresh_content).grid(row=0, column=2, padx=5)

    def refresh_page(self):
        self.image_label.config(image=self.controller.images["page3"])
        self.text_label.config(text=self.controller.random_text3)

    def submit_form(self):
        fruits = []
        if self.var_apple.get(): fruits.append("Apple")
        if self.var_banana.get(): fruits.append("Banana")
        if self.var_cherry.get(): fruits.append("Cherry")

        gender = self.gender.get()
        text_content = self.text_box.get("1.0", "end").strip()

        summary = f"Fruits: {', '.join(fruits) if fruits else 'None'}\nGender: {gender}\nText: {text_content}"
        messagebox.showinfo("Form Submitted", summary)


if __name__ == "__main__":
    app = TestApp()
    app.mainloop()
