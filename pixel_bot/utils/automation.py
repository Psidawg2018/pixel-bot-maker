import time
import logging

# This is a list of all known special (non-character) keys.
# It's used by _parse_key_string to distinguish between, e.g., 'alt' and 'a'.
_SPECIAL_KEYS = [
    'alt', 'alt_l', 'alt_r', 'alt_gr', 'backspace', 'caps_lock', 'cmd',
    'cmd_l', 'cmd_r', 'ctrl', 'ctrl_l', 'ctrl_r', 'delete', 'down', 'end',
    'enter', 'esc', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9',
    'f10', 'f11', 'f12', 'f13', 'f14', 'f15', 'f16', 'f17', 'f18', 'f19',
    'f20', 'home', 'left', 'page_down', 'page_up', 'right', 'shift',
    'shift_l', 'shift_r', 'space', 'tab', 'up', 'media_play_pause',
    'media_volume_mute', 'media_volume_down', 'media_volume_up',
    'media_previous', 'media_next', 'insert', 'menu', 'num_lock', 'pause',
    'print_screen', 'scroll_lock'
]

def _get_key_map():
    """
    Returns a dictionary mapping key strings to pynput Key objects.
    The import and dictionary creation only happen on the first call.
    """
    from pynput.keyboard import Key
    # This is a comprehensive map, but _parse_key_string only needs the names.
    # We keep this function here for the automation functions that need the actual
    # pynput objects.
    return {
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
    into a list of modifier key strings and a single main key string.
    This function is now independent of pynput.
    """
    parts = [part.strip().lower() for part in key_string.split('+')]
    modifiers = []
    main_key = None

    for part in parts:
        if part in _SPECIAL_KEYS:
            is_modifier = any(mod in part for mod in ['ctrl', 'alt', 'shift', 'cmd'])
            if is_modifier:
                modifiers.append(part)
            else:
                if main_key is not None:
                    raise ValueError(f"Invalid key combination: Cannot have more than one non-modifier key. Found '{main_key}' and '{part}'.")
                main_key = part
        elif len(part) == 1:
            if main_key is not None:
                raise ValueError(f"Invalid key combination: Cannot have more than one non-modifier key. Found '{main_key}' and '{part}'.")
            main_key = part
        else:
            raise ValueError(f"Invalid key part: '{part}' in '{key_string}'")

    if main_key is None:
        if len(modifiers) == 1 and len(parts) == 1:
            main_key = modifiers.pop()
        else:
            raise ValueError(f"Invalid key combination: No main key found in '{key_string}'.")

    return modifiers, main_key


def press_key_combination(key_string):
    """
    Presses a combination of keys, like "ctrl+c" or "alt+f4".
    """
    try:
        from pynput.keyboard import Controller as KeyboardController

        KEY_MAP = _get_key_map()
        keyboard = KeyboardController()

        modifier_strs, main_key_str = _parse_key_string(key_string)

        modifier_keys = [KEY_MAP[mod] for mod in modifier_strs]
        main_key = KEY_MAP.get(main_key_str, main_key_str)

        for mod in modifier_keys:
            keyboard.press(mod)

        keyboard.press(main_key)
        keyboard.release(main_key)

        for mod in reversed(modifier_keys):
            keyboard.release(mod)

        logging.info(f"Pressed key combination: '{key_string}'")
        return True
    except (ValueError, ImportError) as e:
        logging.error(f"Error pressing key combination '{key_string}': {e}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred while pressing keys: {e}")
        return False


def click_at(x, y):
    """
    Moves the mouse to the given coordinates and performs a left click.
    """
    try:
        from pynput.mouse import Button, Controller as MouseController
        mouse = MouseController()
        mouse.position = (x, y)
        time.sleep(0.1)
        mouse.click(Button.left, 1)
        logging.info(f"Clicked at ({x}, {y})")
    except ImportError as e:
        logging.error(f"Mouse automation error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during click: {e}")

def right_click_at(x, y):
    """
    Moves the mouse to the given coordinates and performs a right click.
    """
    try:
        from pynput.mouse import Button, Controller as MouseController
        mouse = MouseController()
        mouse.position = (x, y)
        time.sleep(0.1)
        mouse.click(Button.right, 1)
        logging.info(f"Right-clicked at ({x}, {y})")
    except ImportError as e:
        logging.error(f"Mouse automation error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during right-click: {e}")

def type_text(text):
    """
    Types the given string using the keyboard.
    """
    try:
        from pynput.keyboard import Controller as KeyboardController
        keyboard = KeyboardController()
        time.sleep(0.1)
        keyboard.type(text)
        logging.info(f"Typed text: '{text}'")
    except ImportError as e:
        logging.error(f"Keyboard automation error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during type: {e}")


def click_and_drag(start_x, start_y, end_x, end_y, duration=0.5):
    """
    Simulates a click and drag from a start point to an end point.
    """
    try:
        from pynput.mouse import Button, Controller as MouseController
        mouse = MouseController()

        mouse.position = (start_x, start_y)
        time.sleep(0.1)
        mouse.press(Button.left)
        time.sleep(0.1)

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

        mouse.position = (end_x, end_y)
        time.sleep(0.1)
        mouse.release(Button.left)
        logging.info(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
    except ImportError as e:
        logging.error(f"Mouse automation error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during drag: {e}")


def scroll_wheel(direction, amount):
    """
    Simulates scrolling the mouse wheel up or down.
    """
    try:
        from pynput.mouse import Controller as MouseController
        mouse = MouseController()
        dy = amount if direction == 'down' else -amount
        mouse.scroll(0, dy)
        logging.info(f"Scrolled {direction} by {amount} steps.")
    except ImportError as e:
        logging.error(f"Mouse automation error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during scroll: {e}")


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
