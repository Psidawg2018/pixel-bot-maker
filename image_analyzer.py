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

def find_image(haystack_img, needle_imgs, threshold=0.8):
    """
    Finds the best match for a list of smaller images (needles) within a larger image (haystack).

    :param haystack_img: The larger image to search within.
    :param needle_imgs: A list of smaller template images to find.
    :param threshold: The confidence threshold for a match (0.0 to 1.0).
    :return: A tuple (x, y) of the center of the best found match, or None.
    """
    haystack_gray = cv2.cvtColor(haystack_img, cv2.COLOR_BGR2GRAY)

    best_match = {
        'max_val': -1,
        'center_x': -1,
        'center_y': -1
    }

    for needle_img in needle_imgs:
        if needle_img is None:
            continue

        needle_gray = cv2.cvtColor(needle_img, cv2.COLOR_BGR2GRAY)
        needle_w, needle_h = needle_gray.shape[::-1]

        res = cv2.matchTemplate(haystack_gray, needle_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val > best_match['max_val']:
            best_match['max_val'] = max_val
            best_match['center_x'] = max_loc[0] + needle_w // 2
            best_match['center_y'] = max_loc[1] + needle_h // 2

    if best_match['max_val'] >= threshold:
        return (best_match['center_x'], best_match['center_y'])

    return None


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

    # --- Test 3: find_image ---
    print("\n--- Testing find_image ---")
    # Create a high-contrast haystack image
    haystack = np.ones((300, 300, 3), np.uint8) * 255 # White background
    # Create two smaller needle images
    needle1 = np.zeros((50, 50, 3), np.uint8) # Black square
    needle1[1,1] = 1 # Make it non-uniform to avoid matchTemplate issues
    needle2 = np.ones((25, 25, 3), np.uint8) * 128 # Grey square
    needle2[1,1] = 127 # Make it non-uniform

    # Place needle1 inside the haystack at a known location
    needle_x, needle_y = 100, 150
    haystack[needle_y:needle_y+50, needle_x:needle_x+50] = needle1

    print(f"Searching for a black square and a grey square inside a white image.")
    print("Only the black square is present.")
    location = find_image(haystack.copy(), [needle1.copy(), needle2.copy()], threshold=0.95)

    if location:
        print(f"SUCCESS: Found an image at {location}.")
        expected_x, expected_y = needle_x + 25, needle_y + 25
        if location == (expected_x, expected_y):
            print("SUCCESS: Location is correct (it found the black square).")
        else:
            print(f"FAILURE: Location is incorrect. Expected ({expected_x}, {expected_y}).")
    else:
        print("FAILURE: Did not find any of the images.")
