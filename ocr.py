
from typing import List
import pyautogui
try:
    import pygetwindow
except NotImplementedError or ModuleNotFoundError:
    print('pygetwindow not suported') # import pygetwindow not suported under linux 
from PIL import Image
from pytesseract import image_to_string, pytesseract
import numpy as np
from decimal import Decimal
import re

# Regular expression pattern for matching loot instances
LOOT_RE = "([a-zA-Z\(\) ]+) [\(\{\[](\d+[\.\,]\d+) PED[\)\]\}]"

# Set the path to the Tesseract OCR executable
pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def screenshot_window():
    """
    Capture a screenshot of the game window.

    Returns:
        Image: Cropped image of the game window
        int: Width of the game window
        int: Height of the game window
    """
    window_name = None

    # Find the game window with a title starting with "Entropia Universe Client"
    for window_name in pygetwindow.getAllTitles():
        if window_name.startswith("Entropia Universe Client"):
            found_window = window_name
            break

    if not window_name:
        return None, 0, 0

    # Get the window object based on the found window name
    window = pygetwindow.getWindowsWithTitle(window_name)[0]
    
    try:
        # Activate the game window
        window.activate()
    except:
        pass  # ignore for now

    # Capture a screenshot of the entire screen
    im = pyautogui.screenshot()

    # Crop the captured image to the dimensions of the game window
    top_left = window.topleft
    width = window.width
    height = window.height
    im1 = im.crop((top_left.x, top_left.y, top_left.x + width, top_left.y + height))

    return im1, width, height

def change_contrast(img, level):
    """
    Adjust the contrast of an image.

    Args:
        img (Image): Input image
        level (int): Contrast level

    Returns:
        Image: Image with adjusted contrast
    """
    factor = (259 * (level + 255)) / (255 * (259 - level))

    def contrast(c):
        """
        Calculate the contrast of a given color value.

        Args:
            c (int): The color value.

        Returns:
            int: The contrast value calculated using the given color value.
        """
        return 128 + factor * (c - 128)

    # Apply the contrast function to each pixel of the image
    return img.point(contrast)

def get_loot_instances_from_screen():
    """
    Extract loot instances from the game window screenshot.

    Returns:
        List: List of loot instances (name, value)
    """
    loots = []

    # Capture the game window screenshot
    img = screenshot_window()

    # Convert the image to grayscale
    img = img.convert('LA')
    data = np.array(img)

    # Adjust the contrast of the image
    img = change_contrast(img, 150)

    # Greyscale and try to isolate text
    converted = np.where((data // 39) == 215 // 39, 0, 255)
    img = Image.fromarray(converted.astype('uint8'))

    # Perform OCR to extract text from the image
    text = image_to_string(img)
    lines = text.split("\n")
    
    for s in lines:
        # Match the loot pattern in each line of the extracted text
        match = re.match(LOOT_RE, s)
        print(s)
        if match:
            # Extract the loot name and value from the matched pattern
            name, value = match.groups()
            value = Decimal(value.replace(",", "."))
            # Add the loot instance to the list
            loots.append((name, value))

    return loots

def capture_target(contrast=0, banding=35, filter=225):
    """
    Capture the target information from the game window screenshot.

    Args:
        contrast (int): Contrast level
        banding (int): Banding value
        filter (int): Filter value

    Returns:
        None
    """
    # Capture the entire screen
    im = pyautogui.screenshot()

    # Get the dimensions of the captured image
    width, height = im.size

    # Define the region of interest for the target information
    sides = width / 3
    bottom = height / 3

    print((0, 0, sides, bottom))
    
    # Crop the captured image to the target region
    im1 = im.crop((sides, 0, width - sides, bottom))

    # Convert the image to grayscale
    im1 = im1.convert('LA')
    data = np.array(im1)

    # Adjust the contrast of the image
    im1 = change_contrast(im1, contrast)

    # Greyscale and try to isolate text
    converted = np.where((data // banding) == filter // banding, 0, 255)
    img = Image.fromarray(converted.astype('uint8'))

    # Perform OCR to extract text from the image
    text = image_to_string(img)
    lines = text.split("\n")
    
    for s in lines:
        if s:
            print(s)