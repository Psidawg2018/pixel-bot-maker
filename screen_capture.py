import mss
import numpy as np
import cv2
import time
import subprocess
import os

def capture_screen(region=None):
    """
    Captures a region of the screen.

    :param region: A dictionary {'top': Y, 'left': X, 'width': W, 'height': H}
    :return: An OpenCV-compatible image (NumPy array)
    """
    with mss.mss() as sct:
        # If no region is specified, grab the entire screen
        monitor = sct.monitors[1] if region is None else region

        # Grab the data
        sct_img = sct.grab(monitor)

        # Convert to a NumPy array
        img = np.array(sct_img)

        # Convert from BGRA to BGR
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        return img

if __name__ == '__main__':
    print("Running screen capture test...")

    # Start a simple X11 app to have something to capture
    print("Starting xeyes...")
    xeyes_proc = subprocess.Popen(["xeyes"])

    # Give it a moment to appear
    time.sleep(1)

    # Define a region to capture (top, left, width, height)
    # We'll just capture a 400x400 box from the top-left corner.
    capture_area = {'top': 0, 'left': 0, 'width': 400, 'height': 400}

    print(f"Capturing screen region: {capture_area}")
    screenshot = capture_screen(capture_area)

    # Save the captured image
    output_filename = "capture_test.png"
    cv2.imwrite(output_filename, screenshot)

    print(f"Screenshot saved to {output_filename}")

    # Clean up the xeyes process
    xeyes_proc.terminate()
    xeyes_proc.wait()
    print("xeyes process terminated.")

    # Verify the file was created
    if os.path.exists(output_filename):
        print("Test successful: capture_test.png created.")
    else:
        print("Test failed: capture_test.png was not created.")
