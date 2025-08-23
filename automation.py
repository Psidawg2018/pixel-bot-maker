from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
import time

# --- Key Mapping ---
# Maps string representations to pynput Key objects
KEY_MAP = {
    'alt': Key.alt, 'alt_l': Key.alt_l, 'alt_r': Key.alt_r,
    'alt_gr': Key.alt_gr, 'backspace': Key.backspace, 'caps_lock': Key.caps_lock,
    'cmd': Key.cmd, 'cmd_l': Key.cmd_l, 'cmd_r': Key.cmd_r,
    'ctrl': Key.ctrl, 'ctrl_l': Key.ctrl_l, 'ctrl_r': Key.ctrl_r,
    'delete': Key.delete, 'down': Key.down, 'end': Key.end,
    'enter': Key.enter, 'esc': Key.esc, 'f1': Key.f1, 'f2': Key.f2,
    'f3': Key.f3, 'f4': Key.f4, 'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7,
    'f8': Key.f8, 'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11,
    'f12': Key.f12, 'f13': Key.f13, 'f14': Key.f14, 'f15': Key.f15,
    'f16': Key.f16, 'f17': Key.f17, 'f18': Key.f18, 'f19': Key.f19,
    'f20': Key.f20, 'home': Key.home, 'left': Key.left,
    'page_down': Key.page_down, 'page_up': Key.page_up, 'right': Key.right,
    'shift': Key.shift, 'shift_l': Key.shift_l, 'shift_r': Key.shift_r,
    'space': Key.space, 'tab': Key.tab, 'up': Key.up,
    'media_play_pause': Key.media_play_pause, 'media_volume_mute': Key.media_volume_mute,
    'media_volume_down': Key.media_volume_down, 'media_volume_up': Key.media_volume_up,
    'media_previous': Key.media_previous, 'media_next': Key.media_next,
    'insert': Key.insert, 'menu': Key.menu, 'num_lock': Key.num_lock,
    'pause': Key.pause, 'print_screen': Key.print_screen, 'scroll_lock': Key.scroll_lock
}

def _parse_key_string(key_string):
    """
    Parses a user-friendly key combination string (e.g., 'ctrl+alt+delete')
    into a list of modifier keys and a single main key.
    """
    parts = [part.strip().lower() for part in key_string.split('+')]
    modifiers = []
    main_key = None

    for part in parts:
        if part in KEY_MAP:
            # It's a special key, check if it's a modifier
            key_obj = KEY_MAP[part]
            if key_obj in [Key.ctrl, Key.alt, Key.shift, Key.cmd]:
                modifiers.append(key_obj)
            else:
                # It's a special key but not a modifier (e.g., 'delete', 'enter')
                if main_key is not None:
                    raise ValueError(f"Invalid key combination: Cannot have more than one non-modifier key. Found '{main_key}' and '{part}'.")
                main_key = key_obj
        elif len(part) == 1:
            # It's a regular character key
            if main_key is not None:
                raise ValueError(f"Invalid key combination: Cannot have more than one non-modifier key. Found '{main_key}' and '{part}'.")
            main_key = part
        else:
            raise ValueError(f"Invalid key part: '{part}' in '{key_string}'")

    if main_key is None:
        raise ValueError(f"Invalid key combination: No main key found in '{key_string}'.")

    return modifiers, main_key


def press_key_combination(key_string):
    """
    Presses a combination of keys, like "ctrl+c" or "alt+f4".

    :param key_string: A string representing the key combination (e.g., "ctrl+alt+delete").
    """
    keyboard = KeyboardController()
    try:
        modifiers, main_key = _parse_key_string(key_string)

        # Press all modifier keys
        for mod in modifiers:
            keyboard.press(mod)

        # Press and release the main key
        keyboard.press(main_key)
        keyboard.release(main_key)

        # Release all modifier keys in reverse order
        for mod in reversed(modifiers):
            keyboard.release(mod)

        print(f"Pressed key combination: '{key_string}'")
        return True
    except ValueError as e:
        print(f"Error pressing key combination '{key_string}': {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while pressing keys: {e}")
        return False


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


def scroll_wheel(direction, amount):
    """
    Simulates scrolling the mouse wheel up or down.

    :param direction: 'up' or 'down'.
    :param amount: The number of steps to scroll.
    """
    mouse = MouseController()
    # Based on pynput documentation, a positive dy scrolls down, negative scrolls up.
    dy = amount if direction == 'down' else -amount
    mouse.scroll(0, dy)
    print(f"Scrolled {direction} by {amount} steps.")


if __name__ == '__main__':
    print("Running automation tests...")
    print("This test will simulate actions in 3 seconds.")
    print("Please focus a window where you can observe the actions (e.g., a text editor).")
    time.sleep(3)

    # Test click
    print("\nTesting click...")
    click_at(640, 360)
    time.sleep(1)

    # Test typing
    print("\nTesting typing...")
    type_text("Hello from the automation script!")
    time.sleep(1)

    # Test scrolling
    print("\nTesting scroll down...")
    scroll_wheel('down', 5)
    time.sleep(1)

    print("\nTesting scroll up...")
    scroll_wheel('up', 5)
    time.sleep(1)

    # Test key combinations
    print("\nTesting key combinations...")
    print("Test 1: 'ctrl+a' (select all)")
    press_key_combination('ctrl+a')
    time.sleep(1)

    print("Test 2: 'delete'")
    press_key_combination('delete')
    time.sleep(1)

    print("Test 3: 'alt+f4' (This would close the window, so we'll just print)")
    print("(Skipping alt+f4 to not close the test)...")
    # press_key_combination('alt+f4')
    time.sleep(1)

    print("Test 4: Invalid combo 'ctrl+alt+shift'")
    press_key_combination('ctrl+alt+shift')
    time.sleep(1)

    print("\nAutomation test script finished.")
