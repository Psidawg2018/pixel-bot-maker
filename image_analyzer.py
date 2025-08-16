import cv2
import numpy as np
import pytesseract

def find_color(image, target_bgr):
    """
    Checks if a specific color is present in the image.

    :param image: The image to search (OpenCV format, BGR).
    :param target_bgr: A list or tuple of [B, G, R] color values.
    :return: A list of coordinates (x, y) where the color is found.
    """
    target = np.uint8(target_bgr)
    mask = cv2.inRange(image, target, target)

    # Find contours of the color
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    locations = []
    for contour in contours:
        # Get the bounding box of the contour
        x, y, w, h = cv2.boundingRect(contour)
        # Add the center of the bounding box
        locations.append((x + w // 2, y + h // 2))

    return locations

def find_text(image):
    """
    Extracts text from an image using Tesseract OCR.

    :param image: The image to search (OpenCV format, BGR).
    :return: The extracted text as a string.
    """
    # Convert the image to grayscale, as it can improve OCR accuracy
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Use Tesseract to do OCR on the image
    text = pytesseract.image_to_string(gray_image)
    return text.strip()

if __name__ == '__main__':
    print("Running image analyzer tests...")

    # --- Test 1: find_color ---
    print("\n--- Testing find_color ---")
    color_test_image_path = "capture_test.png"
    try:
        color_test_image = cv2.imread(color_test_image_path)
        if color_test_image is None:
            raise FileNotFoundError(f"Could not read image file: {color_test_image_path}")

        # xeyes background is typically white.
        white_bgr = [255, 255, 255]
        print(f"Searching for color BGR: {white_bgr}")

        locations = find_color(color_test_image, white_bgr)

        if locations:
            print(f"SUCCESS: Found white color at {len(locations)} locations. First few: {locations[:5]}")
        else:
            print("FAILURE: Did not find white color in the image.")

    except FileNotFoundError as e:
        print(f"SKIPPED: {e}. Run screen_capture.py to generate the test image.")

    # --- Test 2: find_text ---
    print("\n--- Testing find_text ---")
    # Create a test image with text because capture_test.png has none
    width, height = 400, 100
    text_test_image = np.zeros((height, width, 3), np.uint8) # Black background

    test_text = "Hello, OCR!"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    font_color = (255, 255, 255) # White color
    thickness = 2
    text_size = cv2.getTextSize(test_text, font, font_scale, thickness)[0]
    text_x = (width - text_size[0]) // 2
    text_y = (height + text_size[1]) // 2

    cv2.putText(text_test_image, test_text, (text_x, text_y), font, font_scale, font_color, thickness)

    # Save the text test image for inspection
    cv2.imwrite("text_test_image.png", text_test_image)
    print("Created text_test_image.png for testing.")

    extracted_text = find_text(text_test_image)
    print(f"Extracted text: '{extracted_text}'")

    if extracted_text == test_text:
        print("SUCCESS: Extracted text matches the original text.")
    else:
        print("FAILURE: Extracted text does not match.")
