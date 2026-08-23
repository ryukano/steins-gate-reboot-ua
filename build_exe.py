# -*- coding: utf-8 -*-
"""
Збирає SGRE-UA-Setup.exe — інсталятор одним файлом, щоб не вимагати від людей Python.

    pip install pyinstaller pillow fonttools zstandard texture2ddecoder
    python build_exe.py

Усередину кладемо: код інсталятора, українські тексти, аркуш готової графіки й шрифт під OFL.
Файлів гри в збірці немає — вона працює з архівами користувача.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEP = ";" if sys.platform == "win32" else ":"


def main() -> int:
    for tool in ("PyInstaller", "PIL", "fontTools", "zstandard", "texture2ddecoder"):
        try:
            __import__(tool)
        except ImportError:
            raise SystemExit(f"Немає модуля {tool}. Спершу: pip install pyinstaller pillow "
                             f"fonttools zstandard texture2ddecoder")

    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "SGRE-UA-Setup",
        "--console",
        "--noconfirm",
        "--clean",
        "--add-data", f"{ROOT / 'data'}{SEP}data",
        "--add-data", f"{ROOT / 'fonts'}{SEP}fonts",
        "--paths", str(ROOT / "patcher"),
        "--collect-submodules", "fontTools",
        # fontTools тягне за собою numpy (10 МБ), хоча інсталятору він не потрібен:
        # уся робота з пікселями тут — це paste і crop у Pillow
        "--exclude-module", "numpy",
        "--exclude-module", "scipy",
        "--exclude-module", "matplotlib",
        str(ROOT / "patcher" / "entry.py"),
    ]
    print(" ".join(args))
    subprocess.run(args, check=True, cwd=ROOT)

    out = ROOT / "dist" / ("SGRE-UA-Setup.exe" if sys.platform == "win32" else "SGRE-UA-Setup")
    if out.exists():
        print(f"\nГотово: {out}  ({out.stat().st_size // 1024 // 1024} МБ)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
