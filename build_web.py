# LIU Liangyi (3231234) - CDT501 Lecture 9 - Night Survivors
"""build_web.py - one command that turns the game into the folder GitHub Pages serves.

Run me on your own computer:   python build_web.py

What it does, in the order of the lecture:

  1. pygbag --build .      the browser version, written to build/web/
  2. copy build/web/*      into docs/
  3. write docs/.nojekyll  an empty file: it tells GitHub Pages "do not run Jekyll,
                           just send these files as they are"
  4. change the <title>    so the browser tab says Night Survivors

Then commit docs/, push, and GitHub Pages serves docs/ on the main branch.

Why a separate docs/ folder and not build/web directly? Because build/ is
thrown away and made again on every build; docs/ is the copy that is saved in
the repository. GitHub Pages can only serve files that are in the repository.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build", "web")
DOCS = os.path.join(HERE, "docs")
HIDDEN = None                      # where docs/ waits while pygbag runs
TITLE = "Night Survivors - CDT501"


def run_pygbag():
    """Ask pygbag to build the web version. It reads main.py and packs the folder."""
    print("1. pygbag --build .   (this downloads the web runtime the first time)")
    result = subprocess.run([sys.executable, "-m", "pygbag", "--build", "."],
                            cwd=HERE, text=True, capture_output=True)
    if result.returncode != 0:
        print(result.stdout[-1500:])
        print(result.stderr[-1500:])
        raise SystemExit("pygbag failed - fix the error above and run me again")
    if not os.path.isfile(os.path.join(BUILD, "index.html")):
        raise SystemExit("pygbag did not write build/web/index.html")
    print("   build/web/index.html is ready")


def copy_to_docs():
    """build/web -> docs, starting from an empty docs/ so nothing old is left."""
    print("2. copy build/web -> docs/")
    if os.path.isdir(DOCS):
        shutil.rmtree(DOCS)
    shutil.copytree(BUILD, DOCS)
    for name in sorted(os.listdir(DOCS)):
        print("   docs/%-24s %8d bytes" % (name, os.path.getsize(os.path.join(DOCS, name))))


def nojekyll():
    """An empty .nojekyll: without it GitHub Pages hides files that start with _."""
    print("3. docs/.nojekyll  (empty file)")
    open(os.path.join(DOCS, ".nojekyll"), "w").close()


def retitle():
    """The tab should say the name of the game, not the name of the folder."""
    print("4. <title> -> %s" % TITLE)
    path = os.path.join(DOCS, "index.html")
    page = open(path, encoding="utf-8").read()
    page = page.replace("<title>night-survivors</title>", "<title>%s</title>" % TITLE)
    open(path, "w", encoding="utf-8").write(page)


def read_game_size():
    """Take the window size out of main.py, so the page and the game cannot disagree."""
    text = open(os.path.join(HERE, "main.py"), encoding="utf-8").read()
    width = re.search(r"^WIDTH\s*=\s*(\d+)", text, re.M)
    height = re.search(r"^HEIGHT\s*=\s*(\d+)", text, re.M)
    if not (width and height):
        print("   WARNING: no WIDTH/HEIGHT in main.py - assuming 390 x 700")
        return 390, 700
    return int(width.group(1)), int(height.group(1))


# pygbag's template gets the phone wrong in two ways, so we fix both here:
#
#  1. It writes TWO <meta name="viewport"> lines. The second one
#     ("height=device-height, initial-scale=1.0") wins and has no width=device-width,
#     so a phone lays the page out at the default 980 px and then shrinks it.
#     The game ends up a small, squashed rectangle in the middle of the screen.
#     A desktop browser ignores the meta, which is why it looked fine there.
#  2. <canvas> is styled width:100% + height:100%, which stretches the picture to the
#     shape of the screen instead of keeping the shape of the game.
#
# So: one correct viewport meta, and a canvas that always keeps the game's own
# width:height, as big as the visible screen allows, in the middle, with the space
# around it painted the same dark colour instead of grey.
PHONE_HTML = """
    <!-- Added by build_web.py: make the page fit a phone. -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        html, body {
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden;
            background: #0e1120 !important;   /* the night colour: the empty space looks on purpose.
                                                 !important because the template paints the
                                                 body grey from python at run time */
            overscroll-behavior: none;
            touch-action: none;
            -webkit-user-select: none;
            user-select: none;
        }

        /* keep the game's shape: never stretch it to the shape of the screen */
        canvas#canvas.emscripten {
            position: fixed !important;
            top: 50% !important;
            left: 50% !important;
            right: auto !important;
            bottom: auto !important;
            margin: 0 !important;
            transform: translate(-50%, -50%);
            width: min(100vw, calc(100vh * @W@ / @H@)) !important;
            height: min(100vh, calc(100vw * @H@ / @W@)) !important;
            width: min(100vw, calc(100dvh * @W@ / @H@)) !important;
            height: min(100dvh, calc(100vw * @H@ / @W@)) !important;
            max-width: 100vw !important;
            max-height: 100dvh !important;
            border: 0 !important;
            padding: 0 !important;
            z-index: 5;
        }

        /* "Loading, please wait ..." and "Ready to start !" in the middle, in our colours */
        #infobox {
            position: fixed !important;
            top: 50% !important;
            left: 50% !important;
            transform: translate(-50%, -50%);
            margin: 0;
            padding: 14px 22px;
            background: #1a1f30 !important;
            color: #eef0fa !important;
            border: 1px solid #4e5678 !important;
            border-radius: 14px;
            font: 15px/1.35 system-ui, -apple-system, "Segoe UI", Arial, sans-serif;
            text-align: center;
            white-space: normal;
            max-width: 84vw;
        }
    </style>
"""

VIEWPORT_META = re.compile(r'<meta\s+name="viewport"[^>]*>\s*')


def patch_phone():
    """Fix the phone layout: one viewport meta, and a canvas that keeps the game's shape."""
    width, height = read_game_size()
    print("5. phone layout: canvas always %d:%d, one clean viewport meta" % (width, height))
    path = os.path.join(DOCS, "index.html")
    page = open(path, encoding="utf-8").read()

    if not VIEWPORT_META.search(page):
        raise SystemExit("no viewport meta in index.html - the pygbag template changed")
    page = VIEWPORT_META.sub("", page)          # drop both of pygbag's meta lines

    block = PHONE_HTML.replace("@W@", str(width)).replace("@H@", str(height))
    if "</head>" not in page:
        raise SystemExit("no </head> in index.html - the pygbag template changed")
    page = page.replace("</head>", block + "</head>", 1)

    open(path, "w", encoding="utf-8").write(page)
    print("   %d bytes of style added" % len(block))


def hide_docs():
    """Move the old docs/ out of the project while pygbag runs.

    pygbag packs every file in this folder. If docs/ is still there, it packs the
    old web page (and the old .apk) into the new .apk, and the .apk grows on every
    build. Renaming it is not enough - it has to leave the folder - so it goes to a
    temporary folder outside the project and comes back afterwards.
    """
    global HIDDEN
    if not os.path.isdir(DOCS):
        return False
    HIDDEN = tempfile.mkdtemp(prefix="night-survivors-docs-")
    shutil.move(DOCS, os.path.join(HIDDEN, "docs"))
    print("   docs/ moved out of the folder while pygbag runs")
    return True


def unhide_docs(restore):
    """After the build: delete the temporary copy, or put the old page back on failure."""
    global HIDDEN
    if not HIDDEN:
        return
    if restore:
        shutil.move(os.path.join(HIDDEN, "docs"), DOCS)
    shutil.rmtree(HIDDEN, ignore_errors=True)
    HIDDEN = None


def main():
    hidden = hide_docs()
    try:
        run_pygbag()
    except SystemExit:
        unhide_docs(restore=True)        # put the old page back if the build failed
        raise
    copy_to_docs()
    unhide_docs(restore=False)
    nojekyll()
    retitle()
    patch_phone()
    size = sum(os.path.getsize(os.path.join(DOCS, name)) for name in os.listdir(DOCS))
    print("\nDone. docs/ is %d KB. Commit it, push, and GitHub Pages will serve it."
          % (size // 1024))


if __name__ == "__main__":
    main()
