# -*- coding: utf-8 -*-
"""
Збирає SGRE-UA-Setup.exe — інсталятор одним файлом, щоб не вимагати від людей Python.

    pip install pyinstaller pillow fonttools zstandard
    python build_exe.py

Усередину кладемо: код інсталятора, українські тексти, таблицю написів і шрифти під OFL.
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
    for tool in ("PyInstaller", "PIL", "fontTools", "zstandard"):
        try:
            __import__(tool)
        except ImportError:
            raise SystemExit(f"Немає модуля {tool}. Спершу: pip install pyinstaller pillow fonttools zstandard")

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
        "--hidden-import", "ui_sprites_table",
        "--collect-submodules", "fontTools",
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
