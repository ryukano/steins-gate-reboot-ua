# -*- coding: utf-8 -*-
"""Точка входу для зібраного інсталятора (.exe).

Усередині exe файли лежать у тимчасовій теці (sys._MEIPASS), тому спершу підправляємо шляхи
до даних і шрифтів, а вже потім віддаємо роботу звичайному patch.py. Наприкінці — пауза,
щоб вікно не зникло, поки людина читає підсумок.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Консоль Windows за замовчуванням не в UTF-8 — без цього український текст валить програму
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:  # noqa: BLE001
        pass
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

BUNDLE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(BUNDLE / "patcher"))
sys.path.insert(0, str(BUNDLE / "data"))

import patch  # noqa: E402

patch.ROOT = BUNDLE
patch.DATA = BUNDLE / "data"
patch.FONTS = BUNDLE / "fonts"


def main() -> int:
    print("Українізатор STEINS;GATE RE:BOOT\n" + "─" * 32)
    try:
        code = patch.main()
    except SystemExit as e:
        print(f"\n{e}")
        code = 1
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        print("\nЩось пішло не так. Надішліть цей текст у issue — розберемося.")
        code = 1
    if sys.stdout.isatty():
        input("\nНатисніть Enter, щоб закрити…")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
