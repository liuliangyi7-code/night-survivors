# LIU Liangyi (3231234) - CDT501 Lecture 9 - Night Survivors
"""make_assets.py - turns raw_art/ into assets/ with Pillow.

Run me on your own computer:   python make_assets.py
raw_art/ is never changed: I only read it and write new files into assets/.

Two jobs:
1. Every raw picture is 16 x 16 pixels. I make a 3x copy (48 x 48) with NEAREST,
   so the pixels stay sharp: no blurring.
2. gem.png is grey. I read the brightness of every pixel, turn it into a shade
   between 0 and 1, and mix two colours with that shade. Dark stays dark,
   light stays light: only the colour changes. Blue crystal = 1 XP, pink = 2 XP.
"""

import os
import shutil

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw_art")
OUT = os.path.join(HERE, "assets")

GROW = 3                      # 16 x 16  ->  48 x 48

# Pictures I copy as they are (only bigger).
PLAIN = ["hero", "bat", "slime", "ghost", "demon", "sword", "floor"]

# The two crystals: (name, colour at shade 0, colour at shade 1)
CRYSTALS = [
    ("gem_blue", (40, 90, 190), (165, 245, 255)),     # 1 XP
    ("gem_pink", (170, 45, 120), (255, 205, 240)),    # 2 XP
]


def brightness(pixel):
    """One number for how light a pixel is. Green counts most: our eyes see it best."""
    red, green, blue = pixel[0], pixel[1], pixel[2]
    return 0.299 * red + 0.587 * green + 0.114 * blue


def mix(colour_a, colour_b, shade):
    """0 -> colour_a, 1 -> colour_b, 0.5 -> half way."""
    return tuple(
        int(round(colour_a[i] + (colour_b[i] - colour_a[i]) * shade))
        for i in range(3)
    )


def grow(image):
    """3x bigger, nearest neighbour: the pixels stay square, nothing is blurred."""
    width, height = image.size
    return image.resize((width * GROW, height * GROW), Image.NEAREST)


def make_crystal(raw_path, dark, light):
    """Grey gem.png -> one coloured crystal."""
    gem = Image.open(raw_path).convert("RGBA")
    pixels = gem.load()

    values = [brightness(pixels[x, y][:3])
              for y in range(gem.size[1]) for x in range(gem.size[0])
              if pixels[x, y][3] > 0]
    darkest, lightest = min(values), max(values)
    spread = max(1.0, lightest - darkest)

    for y in range(gem.size[1]):
        for x in range(gem.size[0]):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue
            shade = (brightness((red, green, blue)) - darkest) / spread
            colour = mix(dark, light, shade)
            pixels[x, y] = (colour[0], colour[1], colour[2], alpha)

    return gem


def main():
    if not os.path.isdir(RAW):
        raise SystemExit("raw_art/ is missing: run me inside the night-survivors folder.")

    os.makedirs(OUT, exist_ok=True)

    for name in PLAIN:
        source = os.path.join(RAW, name + ".png")
        target = os.path.join(OUT, name + ".png")
        image = Image.open(source).convert("RGBA")
        grown = grow(image)
        grown.save(target)
        print("assets/%-9s %s -> %s" % (name + ".png", image.size, grown.size))

    gem_path = os.path.join(RAW, "gem.png")
    for name, dark, light in CRYSTALS:
        crystal = grow(make_crystal(gem_path, dark, light))
        crystal.save(os.path.join(OUT, name + ".png"))
        print("assets/%-9s made from gem.png (grey -> colour)" % (name + ".png"))

    licence = os.path.join(RAW, "LICENSE-Kenney-CC0.txt")
    if os.path.isfile(licence):
        shutil.copyfile(licence, os.path.join(OUT, "LICENSE-Kenney-CC0.txt"))
        print("assets/LICENSE-Kenney-CC0.txt  copied (the pictures are Kenney's, CC0)")

    print("\nDone. %d pictures in assets/. raw_art/ was not changed." % (len(PLAIN) + len(CRYSTALS)))


if __name__ == "__main__":
    main()
