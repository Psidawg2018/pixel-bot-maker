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

from PIL import Image

def extract_text_from_image(image):
    """
    Uses pytesseract to extract text from a given image.
    The image is expected to be a NumPy array (from OpenCV).
    This function includes preprocessing steps to improve OCR accuracy.
    Returns the extracted text as a string, or an error code.
    """
    try:
        # 1. Convert to Grayscale
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 2. Apply a slight blur to remove noise
        # A 3x3 kernel is usually a good starting point.
        blurred_image = cv2.GaussianBlur(gray_image, (3, 3), 0)

        # 3. Apply adaptive thresholding to binarize the image
        # This helps with varying lighting conditions.
        binary_image = cv2.adaptiveThreshold(
            blurred_image,
            255, # Max value to assign
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, # Block size (needs to be an odd number)
            2   # Constant subtracted from the mean
        )

        # Pytesseract works best with PIL Images.
        pil_image = Image.fromarray(binary_image)

        # 4. Perform OCR
        text = pytesseract.image_to_string(pil_image)
        return text.strip()
    except pytesseract.TesseractNotFoundError:
        print("OCR Error: Tesseract is not installed or not in your PATH.")
        print("Please install Tesseract OCR from: https://github.com/tesseract-ocr/tesseract")
        # Return a specific error message that the main app can check for
        return "TESSERACT_NOT_FOUND"
    except Exception as e:
        print(f"An unexpected OCR error occurred: {e}")
        return "" # Return empty string for other errors

def find_image(haystack_img, needle_imgs, threshold=0.8):
    """
    Finds the best match for a list of smaller images (needles) within a larger image (haystack).
    This version is color-sensitive and handles transparency in needle images.
    It uses normalized squared difference, where a lower value indicates a better match.

    :param haystack_img: The larger image to search within (BGR).
    :param needle_imgs: A list of smaller template images to find (BGRA or BGR).
    :param threshold: The confidence threshold for a match (0.0 to 1.0).
                      Note: For this method, a value closer to 0 is a better match.
                      The threshold is inverted internally to a 'match quality' score.
    :return: A tuple (x, y) of the center of the best found match, or None.
    """
    best_match = {
        'min_val': float('inf'), # Lower is better for TM_SQDIFF_NORMED
        'max_loc': None,
        'found_needle_w': 0,
        'found_needle_h': 0
    }

    for needle_img in needle_imgs:
        if needle_img is None:
            continue

        needle_h, needle_w = needle_img.shape[:2]

        # Ensure haystack is not smaller than needle
        if haystack_img.shape[0] < needle_h or haystack_img.shape[1] < needle_w:
            continue

        # Check if needle has an alpha channel
        if needle_img.shape[2] == 4:
            needle_bgr = needle_img[:, :, :3]
            mask = needle_img[:, :, 3]
            # The mask requires TM_SQDIFF or TM_CCORR_NORMED.
            # TM_SQDIFF_NORMED is excellent for color matching.
            res = cv2.matchTemplate(haystack_img, needle_bgr, cv2.TM_SQDIFF_NORMED, mask=mask)
        else:
            res = cv2.matchTemplate(haystack_img, needle_img, cv2.TM_SQDIFF_NORMED)

        min_val, _, min_loc, _ = cv2.minMaxLoc(res)

        if min_val < best_match['min_val']:
            best_match['min_val'] = min_val
            best_match['min_loc'] = min_loc
            best_match['found_needle_w'] = needle_w
            best_match['found_needle_h'] = needle_h

    # For TM_SQDIFF_NORMED, a value of 0 is a perfect match.
    # We invert the logic: a match is good if min_val is *below* (1 - threshold).
    match_quality = 1 - best_match['min_val']
    if match_quality >= threshold:
        center_x = best_match['min_loc'][0] + best_match['found_needle_w'] // 2
        center_y = best_match['min_loc'][1] + best_match['found_needle_h'] // 2
        return (center_x, center_y)

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

    # --- Test 2: extract_text_from_image ---
    print("\n--- Testing extract_text_from_image ---")
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

    extracted_text = extract_text_from_image(text_test_image)
    print(f"Extracted text: '{extracted_text}'")

    if extracted_text == test_text:
        print("SUCCESS: Extracted text matches the original text.")
    else:
        print("FAILURE: Extracted text does not match.")

    # --- Test 3: find_image (Basic) ---
    print("\n--- Testing find_image (Basic) ---")
    haystack_basic = np.ones((300, 300, 3), np.uint8) * 255
    needle_basic = np.zeros((50, 50, 3), np.uint8)
    needle_basic[1, 1] = 1
    needle_x, needle_y = 100, 150
    haystack_basic[needle_y:needle_y+50, needle_x:needle_x+50] = needle_basic
    print("Searching for a black square in a white image.")
    location = find_image(haystack_basic.copy(), [needle_basic.copy()], threshold=0.95)
    if location:
        expected_x, expected_y = needle_x + 25, needle_y + 25
        if location == (expected_x, expected_y):
            print("SUCCESS: Basic image found at the correct location.")
        else:
            print(f"FAILURE: Basic image found at incorrect location. Got {location}, expected ({expected_x}, {expected_y}).")
    else:
        print("FAILURE: Basic image not found.")

    # --- Test 4: find_image (Color-Sensitivity) ---
    print("\n--- Testing find_image (Color-Sensitivity) ---")
    haystack_color = np.ones((300, 300, 3), np.uint8) * 255 # White background
    # Create a blue square and a red square
    blue_square = np.array([[[255, 0, 0]] * 50] * 50, dtype=np.uint8)
    red_square = np.array([[[0, 0, 255]] * 50] * 50, dtype=np.uint8)
    # Place them in the haystack
    haystack_color[50:100, 50:100] = blue_square
    haystack_color[150:200, 150:200] = red_square
    # The needle is the red square
    needle_color = red_square.copy()
    print("Searching for a red square in an image containing a blue and a red square.")
    location_color = find_image(haystack_color, [needle_color], threshold=0.95)
    if location_color:
        expected_color_x, expected_color_y = 150 + 25, 150 + 25
        if location_color == (expected_color_x, expected_color_y):
            print("SUCCESS: Correctly found the red square, ignoring the blue one.")
        else:
            print(f"FAILURE: Found an object, but at the wrong location: {location_color}. Expected the red square at ({expected_color_x}, {expected_color_y}).")
    else:
        print("FAILURE: Did not find the red square.")

    # --- Test 5: find_image (Transparency) ---
    print("\n--- Testing find_image (Transparency) ---")
    haystack_trans = np.ones((300, 300, 3), np.uint8) * 255
    # Create a transparent needle (BGRA) with a green circle
    needle_trans = np.zeros((100, 100, 4), dtype=np.uint8)
    cv2.circle(needle_trans, (50, 50), 40, (0, 255, 0, 255), -1) # Green circle, fully opaque
    # Place a green circle on the haystack
    cv2.circle(haystack_trans, (150, 150), 40, (0, 255, 0), -1)
    print("Searching for a green circle using a template with transparency.")
    location_trans = find_image(haystack_trans, [needle_trans], threshold=0.95)
    if location_trans:
        # The center of the circle in the haystack is (150, 150)
        # The location returned is the center of the matched bounding box.
        # Since the needle is 100x100, the top-left is at (100, 100).
        # The center of the match should be 100 + 100/2 = 150.
        expected_trans_x, expected_trans_y = 150, 150
        if abs(location_trans[0] - expected_trans_x) < 2 and abs(location_trans[1] - expected_trans_y) < 2:
             print("SUCCESS: Correctly found the circle using a transparent needle.")
        else:
            print(f"FAILURE: Found circle at the wrong location: {location_trans}. Expected ({expected_trans_x}, {expected_trans_y}).")
    else:
        print("FAILURE: Did not find the circle using the transparent needle.")
