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

def right_click_at(x, y):
    """
    Moves the mouse to the given coordinates and performs a right click.

    :param x: The x-coordinate.
    :param y: The y-coordinate.
    """
    mouse = MouseController()
    mouse.position = (x, y)
    time.sleep(0.1) # Small delay to ensure mouse has moved
    mouse.click(Button.right, 1)
    print(f"Right-clicked at ({x}, {y})")

def type_text(text):
    """
    Types the given string using the keyboard.

    :param text: The string to type.
    """
    keyboard = KeyboardController()
    time.sleep(0.1)
    keyboard.type(text)
    print(f"Typed text: '{text}'")


def click_and_drag(start_x, start_y, end_x, end_y, duration=0.5):
    """
    Simulates a click and drag from a start point to an end point.

    :param start_x: The starting x-coordinate.
    :param start_y: The starting y-coordinate.
    :param end_x: The ending x-coordinate.
    :param end_y: The ending y-coordinate.
    :param duration: The time in seconds the drag should take.
    """
    mouse = MouseController()

    # Move to the start position and press the button
    mouse.position = (start_x, start_y)
    time.sleep(0.1)
    mouse.press(Button.left)
    time.sleep(0.1)

    # Interpolate the drag path
    num_steps = int(duration / 0.01)
    if num_steps < 1:
        num_steps = 1

    dx = (end_x - start_x) / num_steps
    dy = (end_y - start_y) / num_steps

    for i in range(num_steps):
        new_x = start_x + (dx * (i + 1))
        new_y = start_y + (dy * (i + 1))
        mouse.position = (int(new_x), int(new_y))
        time.sleep(0.01)

    # Ensure the final position is set and release the button
    mouse.position = (end_x, end_y)
    time.sleep(0.1)
    mouse.release(Button.left)
    print(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")

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
