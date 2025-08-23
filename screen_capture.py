import mss
import numpy as np
import cv2
import time
import subprocess
import os

def _translate_region_keys(region):
    """Translates a region dictionary from using 'x', 'y' to 'left', 'top'."""
    if region and 'x' in region and 'left' not in region:
        region['left'] = region.pop('x')
    if region and 'y' in region and 'top' not in region:
        region['top'] = region.pop('y')
    return region

def capture_screen(region=None):
    """
    Captures a region of the screen.

    :param region: A dictionary {'top': Y, 'left': X, 'width': W, 'height': H}
    :return: An OpenCV-compatible image (NumPy array)
    """
    with mss.mss() as sct:
        monitor = region
        if region is None:
            # If no region, grab the entire primary screen
            monitor = sct.monitors[1]
        else:
            monitor = _translate_region_keys(monitor)

        # Grab the data
        sct_img = sct.grab(monitor)

        # Convert to a NumPy array
        img = np.array(sct_img)

        # Convert from BGRA to BGR
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        return img

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
