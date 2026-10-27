# LIU Liangyi (3231234) - CDT501 Lecture 9 - Night Survivors
"""make_web_sounds.py - turns sounds/*.wav into sounds/*.ogg for the web page.

Run me on your own computer, before pygbag:   python make_web_sounds.py

Why this file exists
--------------------
A browser cannot play every kind of sound file. The mixer that runs inside the
browser (SDL_mixer, compiled to WebAssembly) only has an Ogg Vorbis decoder.
That is why pygbag stops with

    Audio file 'sounds/hit.wav' ... Use OGG format instead

OGG is the same idea as WAV - numbers, 22,050 of them every second - but the
numbers are stored in a clever, smaller way. Python's standard library can
write WAV but not OGG, so this one script needs a helper: "soundfile", which
brings a small library called libsndfile that can write Ogg Vorbis.

    python -m pip install soundfile        # once

main.py must not import this file. main.py only loads the finished files, and
it asks for ".ogg" first and ".wav" second, so the same game works on the
desktop and in the browser.
"""

import os
import wave

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
SOUNDS = os.path.join(HERE, "sounds")

NAMES = ("hit", "gem", "hurt", "levelup", "end")


def read_wav(path):
    """Read a 16-bit mono .wav and give back numbers between -1.0 and +1.0."""
    with wave.open(path, "rb") as handle:
        frames = handle.readframes(handle.getnframes())
        rate = handle.getframerate()
    # array("h") would be the standard-library way; numpy does the same job
    # for the whole file in one go and soundfile wants numpy anyway.
    numbers = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    return numbers, rate


def main():
    print("Turning the .wav sounds into .ogg, so a browser can play them.\n")
    made = 0
    for name in NAMES:
        source = os.path.join(SOUNDS, name + ".wav")
        if not os.path.isfile(source):
            print("  %-9s missing - run make_sounds.py first" % (name + ".wav"))
            continue
        numbers, rate = read_wav(source)
        target = os.path.join(SOUNDS, name + ".ogg")
        sf.write(target, numbers, rate, format="OGG", subtype="VORBIS")
        print("  sounds/%-9s %5.2f s  %6d -> %5d bytes"
              % (name + ".ogg", len(numbers) / rate,
                 os.path.getsize(source), os.path.getsize(target)))
        made += 1
    print("\nDone. %d files in sounds/. main.py loads .ogg first, then .wav." % made)


if __name__ == "__main__":
    main()
