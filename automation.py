from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Controller as KeyboardController
import time

def click_at(x, y):
    """
    Moves the mouse to the given coordinates and performs a left click.

    :param x: The x-coordinate.
    :param y: The y-coordinate.
    """
    mouse = MouseController()
    mouse.position = (x, y)
    time.sleep(0.1) # Small delay to ensure mouse has moved
    mouse.click(Button.left, 1)
    print(f"Clicked at ({x}, {y})")

def type_text(text):
    """
    Types the given string using the keyboard.

    :param text: The string to type.
    """
    keyboard = KeyboardController()
    time.sleep(0.1)
    keyboard.type(text)
    print(f"Typed text: '{text}'")


if __name__ == '__main__':
    print("Running automation tests...")
    print("This test will simulate a click and typing in 3 seconds.")
    print("It will happen on the virtual display. There is no visual feedback here.")

    time.sleep(3)

    # Test click
    # In our 1280x720 virtual display, let's click near the center.
    click_at(640, 360)

    time.sleep(1)

    # Test typing
    type_text("Hello from the automation script!")

    print("\nAutomation test script finished.")
