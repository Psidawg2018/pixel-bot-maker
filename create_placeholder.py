import cv2
import numpy as np
import os

# Define the image path
dir_path = "pixel_bot/templates"
if not os.path.exists(dir_path):
    os.makedirs(dir_path)

image_path = os.path.join(dir_path, "placeholder.png")

# Create a 10x10 black image
image = np.zeros((10, 10, 3), dtype=np.uint8)

# Save the image
cv2.imwrite(image_path, image)

print(f"Image saved to {image_path}")
