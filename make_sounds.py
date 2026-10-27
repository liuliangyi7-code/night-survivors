# LIU Liangyi (3231234) - CDT501 Lecture 9 - Night Survivors
"""make_sounds.py - makes the short sounds with the standard library only.

Run me on your own computer:   python make_sounds.py

A sound is a list of numbers: 22,050 of them every second, each one between
-32767 and +32767. That is all a .wav file is. So I can build the sounds with
math and write them with the "wave" module that comes with Python.

    value = math.sin(phase) * envelope * volume
             the wiggle      fades in/out   how loud

main.py must not import this file (wave does not work in a browser): it only
loads the finished .wav files from sounds/.
"""

import math
import os
import random
import wave
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "sounds")

RATE = 22050                 # numbers per second


# -- small helpers ---------------------------------------------------------

def samples(seconds):
    """How many numbers a sound of this length needs.

    0.07 s * 22,050 = 1,543 numbers, the same numbers as the hit in the slides.
    """
    return int(seconds * RATE)


def tone(freq, count, volume=0.5, decay=6.0, shape="sine", freq_end=None, start=0.0):
    """A list of `count` numbers: one musical note that fades out."""
    out = [0.0] * count
    phase = 0.0
    for i in range(count):
        t = i / max(1, count - 1)               # 0 at the start, 1 at the end
        freq_now = freq if freq_end is None else freq + (freq_end - freq) * t
        phase += math.tau * freq_now / RATE
        if shape == "square":
            wave_now = 1.0 if math.sin(phase) >= 0.0 else -1.0
        elif shape == "saw":
            wave_now = 2.0 * ((phase / math.tau) % 1.0) - 1.0
        else:
            wave_now = math.sin(phase)
        envelope = math.exp(-decay * t)         # fades out
        attack = min(1.0, i / (0.004 * RATE))   # fades in over 4 ms, so there is no click
        out[i] = wave_now * envelope * attack * volume
    return out


def noise(count, volume=0.4, decay=20.0, seed=7):
    """A list of `count` random numbers: a hit, a knock, a breath."""
    rng = random.Random(seed)
    out = [0.0] * count
    for i in range(count):
        t = i / max(1, count - 1)
        out[i] = (rng.random() * 2.0 - 1.0) * math.exp(-decay * t) * volume
    return out


def add(base, extra, at=0):
    """Put `extra` on top of `base`, starting at number `at`."""
    for i, value in enumerate(extra):
        index = at + i
        if 0 <= index < len(base):
            base[index] += value
    return base


def notes(sequence, count, volume=0.45, decay=5.0):
    """A short melody: [(frequency, where it starts 0..1, length 0..1), ...]."""
    out = [0.0] * count
    for freq, start, length in sequence:
        piece = tone(freq, int(count * length), volume=volume, decay=decay)
        add(out, piece, int(count * start))
    return out


def save(name, data):
    """Write a list of numbers as a 16-bit mono .wav file."""
    clipped = array("h", (max(-32767, min(32767, int(v * 32767))) for v in data))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".wav")
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(clipped.tobytes())
    print("sounds/%-9s %6d numbers  %.2f s" % (name + ".wav", len(data), len(data) / RATE))
    return path


# -- the five sounds ------------------------------------------------------

def make_hit():
    """A spark hits an enemy: a very short knock. 0.07 s."""
    count = samples(0.07)                       # 1,543 numbers
    out = noise(count, volume=0.55, decay=26.0)
    add(out, tone(760, count, volume=0.35, decay=22.0, shape="square", freq_end=420))
    return out


def make_gem():
    """A crystal is picked up: two quick bright pings. 0.19 s."""
    count = samples(0.19)                       # 4,189 numbers
    out = [0.0] * count
    add(out, tone(1046, int(count * 0.45), volume=0.40, decay=7.0))
    add(out, tone(1568, int(count * 0.60), volume=0.32, decay=6.0), int(count * 0.35))
    return out


def make_hurt():
    """The hero is hurt: a low, ugly buzz. 0.20 s."""
    count = samples(0.20)                       # 4,410 numbers
    out = tone(220, count, volume=0.42, decay=5.0, shape="saw", freq_end=90)
    add(out, noise(count, volume=0.22, decay=12.0, seed=3))
    return out


def make_levelup():
    """A level up: four notes going up. 0.54 s."""
    count = samples(0.54)                       # 11,907 numbers
    return notes([(523, 0.00, 0.34), (659, 0.22, 0.34), (784, 0.44, 0.34), (1046, 0.66, 0.34)],
                 count, volume=0.40, decay=4.0)


def make_end():
    """The end of the game: three notes going down. 0.80 s."""
    count = samples(0.80)
    out = notes([(392, 0.00, 0.40), (330, 0.30, 0.40), (262, 0.60, 0.45)],
                count, volume=0.40, decay=2.2)
    add(out, tone(131, count, volume=0.18, decay=2.0))
    return out


def main():
    print("Making sounds at %d numbers per second.\n" % RATE)
    save("hit", make_hit())
    save("gem", make_gem())
    save("hurt", make_hurt())
    save("levelup", make_levelup())
    save("end", make_end())
    print("\nDone. %d files in sounds/. They are plain numbers, so they are small." % 5)


if __name__ == "__main__":
    main()
