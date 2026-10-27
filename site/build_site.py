"""Assemble the website into one folder (_site/) ready to publish or preview.

The pages live in site/, but the charts live in results/ (where the analysis
writes them). GitHub Pages serves one folder, so this copies both together:
- site/*                          -> _site/
- results/*.png + summary.md      -> _site/results/   (raw CSVs are left out: ~90 MB)
- the game engine's Python files  -> _site/src/       (the Watch/Play pages run them
                                                       in the browser with Pyodide)

Used by the deploy workflow (.github/workflows/pages.yml) and for local preview:
    python site/build_site.py
    python -m http.server --directory _site      # then open http://localhost:8000
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repository root
OUT = ROOT / "_site"
# Only the engine files the browser needs (no analysis/matplotlib, no terminal view).
ENGINE_FILES = ["__init__.py", "board.py", "player.py", "strategies.py", "game.py", "web.py"]


def build() -> Path:
    """Rebuild _site/ from scratch and return its path."""
    if OUT.exists():
        shutil.rmtree(OUT)  # start clean so deleted files don't linger
    shutil.copytree(ROOT / "site", OUT, ignore=shutil.ignore_patterns("build_site.py"))
    (OUT / "results").mkdir()
    for f in [*sorted((ROOT / "results").glob("*.png")), ROOT / "results" / "summary.md"]:
        shutil.copy2(f, OUT / "results" / f.name)
    (OUT / "src").mkdir()
    for name in ENGINE_FILES:
        shutil.copy2(ROOT / "src" / name, OUT / "src" / name)
    return OUT


if __name__ == "__main__":
    print(f"Built {build()}")
