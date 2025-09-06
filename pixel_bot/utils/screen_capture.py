import mss
import numpy as np
import cv2
import time

def _translate_region_keys(region):
    """Translates a region dictionary from using 'x', 'y' to 'left', 'top'."""
    if region and 'x' in region and 'left' not in region:
        region['left'] = region.pop('x')
    if region and 'y' in region and 'top' not in region:
        region['top'] = region.pop('y')
    return region

class ScreenCapturer:
    def __init__(self):
        self.sct = mss.mss()
        self.last_capture_time = 0
        self.last_region = None
        self.last_screenshot = None

    def capture(self, region=None):
        """
        Captures a region of the screen, with caching to avoid redundant captures.
        """
        current_time = time.time()

        # Check cache conditions
        if (self.last_screenshot is not None and
            region == self.last_region and
            current_time - self.last_capture_time < 0.1): # 100ms cache
            return self.last_screenshot

        # --- Perform new capture ---
        monitor = region
        if region is None:
            monitor = self.sct.monitors[1]
        else:
            monitor = _translate_region_keys(monitor)

        sct_img = self.sct.grab(monitor)
        img = np.array(sct_img)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # Update cache
        self.last_screenshot = img
        self.last_region = region
        self.last_capture_time = current_time

        return img

# Create a single, global instance of the capturer
_screen_capturer_instance = ScreenCapturer()

def capture_screen(region=None):
    """
    Public function to capture the screen. Uses the singleton ScreenCapturer instance.
    """
    return _screen_capturer_instance.capture(region)


if __name__ == '__main__':
    print("Running screen capture tests...")

    # --- Test 1: Key Translation ---
    print("\n--- Testing _translate_region_keys ---")
    test_region_xy = {'x': 10, 'y': 20, 'width': 100, 'height': 100}
    print(f"Original region: {test_region_xy}")

    translated_region = _translate_region_keys(test_region_xy.copy())
    print(f"Translated region: {translated_region}")

    expected_region = {'left': 10, 'top': 20, 'width': 100, 'height': 100}

    if translated_region == expected_region:
        print("SUCCESS: Region keys translated correctly.")
    else:
        print(f"FAILURE: Region keys not translated correctly. Expected {expected_region}")

    # --- Test 2: No translation needed ---
    print("\n--- Testing with already correct keys ---")
    test_region_lt = {'left': 50, 'top': 60, 'width': 100, 'height': 100}
    print(f"Original region: {test_region_lt}")
    translated_region_lt = _translate_region_keys(test_region_lt.copy())
    print(f"Translated region: {translated_region_lt}")
    if translated_region_lt == test_region_lt:
        print("SUCCESS: Region with correct keys was not modified.")
    else:
        print("FAILURE: Region with correct keys was modified.")
