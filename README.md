# Night Survivors

A tiny "survivors" game in Python, made for **CDT501 Lecture 9**.
You only walk; your weapons attack by themselves. Survive until **2:00** to win.

**Play in a browser:** https://liuliangyi7-code.github.io/night-survivors/
(the first visit downloads about 20 MB of Python runtime, so give it a few seconds)

## Play on my computer

```bash
python -m pip install pygame-ce soundfile   # soundfile is only needed for make_web_sounds.py
python main.py
```

Mouse or finger: the hero walks toward the pointer. Click a card to choose it. `P` pauses.

## The files

| File | What it is |
|---|---|
| `GAME.md` | the design: every name and every number |
| `rules.py` | the rules only (fixed step 1/60 s). No pygame, so the tests can run alone |
| `main.py` | window, drawing, sound, input. `async def main()` so a browser can run it |
| `data/game.json` | all the numbers from `GAME.md`. Change a number, not the code |
| `make_assets.py` | Pillow: 3x bigger sprites from `raw_art/`, and the two crystals |
| `make_sounds.py` | standard library only: makes the five `.wav` sounds with maths |
| `make_web_sounds.py` | turns those `.wav` into `.ogg`, because a browser only reads OGG |
| `build_web.py` | pygbag -> `build/web` -> `docs/` + `.nojekyll`: the folder GitHub Pages serves |
| `tests/` | `python -m unittest` - the rules only |

## Rebuild the web page after changing the game

```bash
python make_assets.py        # only if you changed raw_art/
python make_sounds.py        # only if you changed the sounds
python make_web_sounds.py    # .wav -> .ogg
python build_web.py          # pygbag + copy to docs/
```

Then commit `docs/` and push.

## Credits (who made what)

- **Pictures:** [Kenney.nl](https://kenney.nl) - CC0, free to use (`raw_art/`)
- **Sounds:** made by `make_sounds.py` in this folder - sine waves and noise
- **Code:** written by me, LIU Liangyi (3231234), with an AI agent (WorkBuddy)
- **Idea:** the "survivors" genre (Vampire Survivors, by poncle). The names, numbers
  and pictures are our own.
