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
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build", "web")
DOCS = os.path.join(HERE, "docs")
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


def main():
    run_pygbag()
    copy_to_docs()
    nojekyll()
    retitle()
    size = sum(os.path.getsize(os.path.join(DOCS, name)) for name in os.listdir(DOCS))
    print("\nDone. docs/ is %d KB. Commit it, push, and GitHub Pages will serve it."
          % (size // 1024))


if __name__ == "__main__":
    main()
