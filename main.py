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


# GUI
class SpotDifferenceGUI:
    def __init__(self):
        # Create the application window
        self.root = tk.Tk()
        self.root.title("Spot The Difference")

        self.ImageModifier = ImageModifier()

        self.game = Game()

        self.original_image = None
        self.modified_image = None
        self.original_tk = None
        self.modified_tk = None

        self.setup_ui()

    def setup_ui(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(pady=10)

        # Create the Load Image and Reveal buttons
        load_btn = tk.Button(top_frame, text="Load Image", command=self.load_image)
        load_btn.grid(row=0, column=0, padx=10)
        reveal_btn = tk.Button(top_frame, text="Reveal", command=self.reveal_all)
        reveal_btn.grid(row=0, column=1, padx=10)

        # Label displaying the number of differences still unfound for the current image
        self.remaining_label = tk.Label(top_frame, text="Remaining: 5", font=("Arial", 12))
        self.remaining_label.grid(row=0, column=2, padx=10)

        # Label displaying the number of mistakes
        self.mistakes_label = tk.Label(top_frame,text="Mistakes: 0", font=("Arial", 12))
        self.mistakes_label.grid(row=0, column=3, padx=10)

        image_frame = tk.Frame(self.root)
        image_frame.pack()

        #  Canvas for displaying the images and drawing the circles
        self.left_canvas = tk.Canvas(image_frame, width=500, height=500, bg="lightgray")
        self.left_canvas.grid(row=0, column=0, padx=10)
        self.right_canvas = tk.Canvas(image_frame, width=500, height=500, bg="lightgray")
        self.right_canvas.grid(row=0, column=1, padx=10)

        # The modified image on the right is the only image that responds to player clicks
        self.right_canvas.bind("<Button-1>", self.on_click)


    def load_image(self):
        # Allows the user to browse for image.
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.png *.bmp *.jpeg")])
        if not file_path:
            return

        image = cv2.imread(file_path)
        if image is None:
            messagebox.showerror("Error","Could not load image.")
            return

        image = self.resize_image(image)
        self.original_image = image
        self.modified_image = self.ImageModifier.create_modified_image(image)
        self.display_images()

        self.game.reset()

        self.update_labels()

    def resize_image(self, image):
        height, width = image.shape[:2]
        max_size = 500
        scale = min(max_size / width, max_size / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        return cv2.resize(image, (new_width, new_height))

    def convert_to_tk(self, image):
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        return ImageTk.PhotoImage(pil_image)

    # Display the images on canvas
    def display_images(self):
        self.original_tk = self.convert_to_tk(self.original_image)
        self.modified_tk = self.convert_to_tk(self.modified_image)
        
        self.left_canvas.delete("all")
        self.right_canvas.delete("all")
        self.left_canvas.create_image(0, 0, anchor=tk.NW, image=self.original_tk)
        self.right_canvas.create_image(0, 0, anchor=tk.NW, image=self.modified_tk)

    # Handle player guesses. Checks if the guess is correct or not.
    def on_click(self, event):
        if not self.game.active:
            return

        x = event.x
        y = event.y
        result = self.game.check_click(x, y, self.ImageModifier.differences)
        if result:
            self.draw_circle(result, "red") # draw the red circles for found
            
            if self.game.remaining == 0: # All differences found
                messagebox.showinfo(
                    "Congratulations!",
                    "You found all 5 differences!"
                )

                self.game.active = False

        else:
            if self.game.mistakes >= Game.Max_mistakes:
                messagebox.showerror(
                    "Game Over",
                    f"You have made too many incorrect guesses.\n"
                    f"You found {5 - self.game.remaining} differences."
                )

        self.update_labels()

    # Draw the circles
    def draw_circle(self, diff, colour):
        r = diff._radius
        for canvas in [self.left_canvas, self.right_canvas]:

            canvas.create_oval(
                diff._x - r,
                diff._y - r,
                diff._x + r,
                diff._y + r,
                outline=colour,
                width=3
            )
    # Only reveal the unfound differences by drawing blue circles
    def reveal_all(self):
        for diff in self.ImageModifier.differences:
            if not diff.is_found():
                self.draw_circle(diff, "blue")

        self.game.remaining = 0
        self.update_labels()
        self.game.active = False

    # Updates GUI text dynamically ie the remaining differences and the number of mistakes
    def update_labels(self):
        self.remaining_label.config(text=f"Remaining: {self.game.remaining}")
        self.mistakes_label.config(text=f"Mistakes: {self.game.mistakes}")

    def run(self):
        self.root.mainloop()

# Main section
if __name__ == "__main__":
    app = SpotDifferenceGUI()
    app.run()

# Create the Load Image and Reveal buttons
        load_btn = tk.Button(top_frame, text="Load Image", command=self.load_image)
        load_btn.grid(row=0, column=0, padx=10)
        reveal_btn = tk.Button(top_frame, text="Reveal", command=self.reveal_all)
        reveal_btn.grid(row=0, column=1, padx=10)

        # Label displaying the number of differences still unfound for the current image
        self.remaining_label = tk.Label(top_frame, text="Remaining: 5", font=("Arial", 12))
        self.remaining_label.grid(row=0, column=2, padx=10)

        # Label displaying the number of mistakes
        self.mistakes_label = tk.Label(top_frame,text="Mistakes: 0", font=("Arial", 12))
        self.mistakes_label.grid(row=0, column=3, padx=10)

        image_frame = tk.Frame(self.root)
        image_frame.pack()

        #  Canvas for displaying the images and drawing the circles
        self.left_canvas = tk.Canvas(image_frame, width=500, height=500, bg="lightgray")
        self.left_canvas.grid(row=0, column=0, padx=10)
        self.right_canvas = tk.Canvas(image_frame, width=500, height=500, bg="lightgray")
        self.right_canvas.grid(row=0, column=1, padx=10)

        # The modified image on the right is the only image that responds to player clicks
        self.right_canvas.bind("<Button-1>", self.on_click)


    def load_image(self):
        # Allows the user to browse for image.
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.png *.bmp *.jpeg")])
        if not file_path:
            return

        image = cv2.imread(file_path)
        if image is None:
            messagebox.showerror("Error","Could not load image.")
            return

        image = self.resize_image(image)
        self.original_image = image
        self.modified_image = self.ImageModifier.create_modified_image(image)
        self.display_images()

        self.game.reset()

        self.update_labels()

    def resize_image(self, image):
        height, width = image.shape[:2]
        max_size = 500
        scale = min(max_size / width, max_size / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        return cv2.resize(image, (new_width, new_height))

    def convert_to_tk(self, image):
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        return ImageTk.PhotoImage(pil_image)

    # Display the images on canvas
    def display_images(self):
        self.original_tk = self.convert_to_tk(self.original_image)
        self.modified_tk = self.convert_to_tk(self.modified_image)
        
        self.left_canvas.delete("all")
        self.right_canvas.delete("all")
        self.left_canvas.create_image(0, 0, anchor=tk.NW, image=self.original_tk)
        self.right_canvas.create_image(0, 0, anchor=tk.NW, image=self.modified_tk)

# Main section
if __name__ == "__main__":
    app = SpotDifferenceGUI()
    app.run()

# Create the Load Image and Reveal buttons
        load_btn = tk.Button(top_frame, text="Load Image", command=self.load_image)
        load_btn.grid(row=0, column=0, padx=10)
        reveal_btn = tk.Button(top_frame, text="Reveal", command=self.reveal_all)
        reveal_btn.grid(row=0, column=1, padx=10)

        # Label displaying the number of differences still unfound for the current image
        self.remaining_label = tk.Label(top_frame, text="Remaining: 5", font=("Arial", 12))
        self.remaining_label.grid(row=0, column=2, padx=10)

        # Label displaying the number of mistakes
        self.mistakes_label = tk.Label(top_frame,text="Mistakes: 0", font=("Arial", 12))
        self.mistakes_label.grid(row=0, column=3, padx=10)

        image_frame = tk.Frame(self.root)
        image_frame.pack()

        #  Canvas for displaying the images and drawing the circles
        self.left_canvas = tk.Canvas(image_frame, width=500, height=500, bg="lightgray")
        self.left_canvas.grid(row=0, column=0, padx=10)
        self.right_canvas = tk.Canvas(image_frame, width=500, height=500, bg="lightgray")
        self.right_canvas.grid(row=0, column=1, padx=10)

        # The modified image on the right is the only image that responds to player clicks
        self.right_canvas.bind("<Button-1>", self.on_click)


    def load_image(self):
        # Allows the user to browse for image.
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.png *.bmp *.jpeg")])
        if not file_path:
            return

        image = cv2.imread(file_path)
        if image is None:
            messagebox.showerror("Error","Could not load image.")
            return

        image = self.resize_image(image)
        self.original_image = image
        self.modified_image = self.ImageModifier.create_modified_image(image)
        self.display_images()

        self.game.reset()

        self.update_labels()

    def resize_image(self, image):
        height, width = image.shape[:2]
        max_size = 500
        scale = min(max_size / width, max_size / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        return cv2.resize(image, (new_width, new_height))

    def convert_to_tk(self, image):
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        return ImageTk.PhotoImage(pil_image)

    # Display the images on canvas
    def display_images(self):
        self.original_tk = self.convert_to_tk(self.original_image)
        self.modified_tk = self.convert_to_tk(self.modified_image)
        
        self.left_canvas.delete("all")
        self.right_canvas.delete("all")
        self.left_canvas.create_image(0, 0, anchor=tk.NW, image=self.original_tk)
        self.right_canvas.create_image(0, 0, anchor=tk.NW, image=self.modified_tk)
