"""Copy the packaged desktop assets to the static GitHub Pages preview."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    for name in ('index.html', 'desktop.css', 'desktop.js'):
        shutil.copyfile(ROOT / 'app/desktop_assets' / name, ROOT / 'docs' / name)
    shutil.copyfile(ROOT / 'app/desktop_assets/index.html', ROOT / 'docs/hud.html')


if __name__ == '__main__':
    main()
