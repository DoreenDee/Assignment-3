import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import random

# Alteration parent class. All alteration types inherit from this class 
class Alteration:
    def apply(self, image, x, y, w, h):
        pass


# Colour shift alteration
class ColourShiftAlteration(Alteration):
    def apply(self, image, x, y, w, h):
        region = image[y:y+h, x:x+w].astype(np.int16)
        region[:, :, 0] = np.clip(region[:, :, 0] + 10, 0, 255)  # Blue
        region[:, :, 1] = np.clip(region[:, :, 1] + 15, 0, 255)  # Green
        region[:, :, 2] = np.clip(region[:, :, 2] - 10, 0, 255)  # Red
        image[y:y+h, x:x+w] = region.astype(np.uint8)

# Blur alteration: Applies blur to only a small section of the image
class BlurAlteration(Alteration):
    def apply(self, image, x, y, w, h):
        region = image[y:y+h, x:x+w]
        blurred = cv2.GaussianBlur(region, (15, 15), 0)
        image[y:y+h, x:x+w] = blurred

# Brightness alteration: changes the brightness
class BrightnessAlteration(Alteration):
    def apply(self, image, x, y, w, h):
        region = image[y:y+h, x:x+w]
        brighter = cv2.convertScaleAbs(region, alpha=1.25, beta=25)
        image[y:y+h, x:x+w] = brighter

# Difference class: represents a hidden difference
class ImageDifference:
    def __init__(self, x, y, radius, diff_type):
        self._x = x
        self._y = y
        self._radius = radius
        self._diff_type = diff_type
        self._found = False

    # Checks whether the player clicked close enough to the hidden difference.
    def contains_point(self, px, py):
        distance = ((px - self._x) ** 2 + (py - self._y) ** 2) ** 0.5
        return distance <= self._radius

    def mark_found(self):
        self._found = True

    def is_found(self):
        return self._found

# Generates the differences, and creates the modified image 
class ImageModifier:
    def __init__(self):
        self.differences = []

    def create_modified_image(self, image):
        clone = image.copy()
        self.differences.clear()
        height, width = image.shape[:2]
        alterations = [ColourShiftAlteration(), BlurAlteration(), BrightnessAlteration()]

        attempts = 0

        # Introduces exactly 5 differences into the clone at random locations.
        while len(self.differences) < 5 and attempts < 100:
            attempts += 1
            w = 60
            h = 60

            x = random.randint(0, width - w)
            y = random.randint(0, height - h)

            # Randomly chooses an alteration type; Ensures the differences do not overlap
            if not self.overlaps(x, y):         
                alteration = random.choice(alterations) 
                alteration.apply(clone, x, y, w, h)
                diff = ImageDifference(x + w // 2, y + h // 2, 30, alteration.__class__.__name__)
                self.differences.append(diff)

        return clone

    def overlaps(self, x, y):
        for diff in self.differences:
            if abs(diff._x - x) < 80 and abs(diff._y - y) < 80:
                return True

        return False

# Game class: handles the state of the game
class Game:
    Max_mistakes = 3

    def __init__(self):
        self.score = 0
        self.mistakes = 0
        self.remaining = 5
        self.active = True

    # Runs when loading a new image to reset the mistakes, remaining differences and game state
    def reset(self):
        self.mistakes = 0
        self.remaining = 5
        self.active = True

    def check_click(self, x, y, differences):
        if not self.active:
            return None

        for diff in differences:
            if not diff.is_found() and diff.contains_point(x, y):
                diff.mark_found()
                self.score += 1
                self.remaining -= 1
                return diff

        self.mistakes += 1 # mistake tracking

        # disable further clicks after 3 mistakes
        if self.mistakes >= self.Max_mistakes:
            self.active = False

        return None


# 
