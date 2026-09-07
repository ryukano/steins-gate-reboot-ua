"""
Додає українські літери ІіЇїЄєҐґ у растрові шрифти textfont12/textfont24 (екран Observer тощо).

Нових ресурсів не треба — все складається з наявних пікселів атласа:
    і І ї  — той самий прямокутник, що в латинських i I ï (запис-псевдонім);
    Ї      — крапки з ï + стовбур I, у вільній зоні атласа;
    є Є    — дзеркало э Э;
    ґ Ґ    — г Г з домальованим угору ріжком тієї ж товщини, що верхня перекладина.

    python textfont_ua.py            — зібрати в work/build/textfont_ua/ (не чіпає гру)
    python textfont_ua.py --install  — у гру (з бекапом _orig/)
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from m2archive import Archive  # noqa: E402
from psb import Psb  # noqa: E402

GAME = Path(r"D:\GAMES\Steam\steamapps\common\SGRE")
NAMES = ("textfont12", "textfont24")
UA = "іІїЇєЄґҐ"


class _Atlas:
    def __init__(self, psb: Psb):
        src = psb.root["source"][0]
        self.w, self.h = src["width"], src["height"]
        self.chunk_index = src["pixel"].index
        self.px = bytearray(psb.chunk(self.chunk_index))
        self.code = psb.root["code"]

    def rect(self, ch: str) -> list[bytearray]:
        g = self.code[ch]
        x, y, w, h = int(g["x"]), int(g["y"]), int(g["w"]), int(g["h"])
        return [bytearray(self.px[(y + r) * self.w + x:(y + r) * self.w + x + w]) for r in range(h)]

    def blit(self, rows: list[bytearray], x: int, y: int):
        for r, row in enumerate(rows):
            self.px[(y + r) * self.w + x:(y + r) * self.w + x + len(row)] = row


def _mirror(rows: list[bytearray]) -> list[bytearray]:
    return [bytearray(reversed(r)) for r in rows]


def _dots_of(rows: list[bytearray]) -> list[bytearray]:
    """Верхні рядки ï до першого порожнього — це крапки."""
    out = []
    for r in rows:
        if not any(r):
            break
        out.append(bytearray(r))
    return out


def _horn(rows: list[bytearray], up: int) -> list[bytearray]:
    """г/Г → ґ/Ґ: над правим краєм верхньої перекладини домальовує ріжок висотою up."""
    top = next(r for r in rows if any(v >= 128 for v in r))
    strong = [i for i, v in enumerate(top) if v >= 128]
    thick = max(1, round(len(rows[0]) / 12))          # 1 px на 12-му кеглі, 2-3 на 24-му
    cols = strong[-thick:]
    horn = bytearray(len(rows[0]))
    for c in cols:
        horn[c] = top[c]
    return [bytearray(horn) for _ in range(up)] + rows


def extend(psb: Psb) -> bytes:
    """Повертає перебудований PSB із доданими українськими літерами."""
    at = _Atlas(psb)
    code = at.code
    if all(ch in code for ch in UA):
        return psb.build(chunks={at.chunk_index: bytes(at.px)})
    em = code["I"]["height"]                          # 12 або 24
    up = 2 if em == 12 else 4                         # висота ріжка ґ/Ґ

    # псевдоніми: той самий прямокутник атласа, лише новий запис у code
    for ua, lat in (("і", "i"), ("І", "I"), ("ї", "ï")):
        code.setdefault(ua, dict(code[lat]))

    # вільна зона під наявними гліфами
    pen_x, pen_y = 4, max(int(g["y"]) + int(g["h"]) for g in code.values() if isinstance(g, dict)) + 3

    def add(ch: str, donor: str, rows: list[bytearray], raised: int = 0):
        nonlocal pen_x
        if ch in code:
            return
        g = dict(code[donor])
        g["x"], g["y"] = float(pen_x), pen_y
        g["w"] = g["width"] = float(len(rows[0]))
        g["h"], g["b"] = len(rows), g["b"] + raised
        at.blit(rows, pen_x, pen_y)
        code[ch] = g
        pen_x += len(rows[0]) + 2

    # Ї: крапки з ï, порожній рядок, стовбур I
    dots = _dots_of(at.rect("ï"))
    stem = at.rect("I")
    width = max(len(dots[0]), len(stem[0]))
    pad = lambda rows: [bytearray(r) + bytearray(width - len(r)) for r in rows]
    add("Ї", "I", pad(dots) + [bytearray(width)] + pad(stem), raised=len(dots) + 1)

    add("є", "э", _mirror(at.rect("э")))
    add("Є", "Э", _mirror(at.rect("Э")))
    add("ґ", "г", _horn(at.rect("г"), up), raised=up)
    add("Ґ", "Г", _horn(at.rect("Г"), up), raised=up)

    assert pen_y + em + up + 2 <= at.h, "нема місця в атласі"
    return psb.build(chunks={at.chunk_index: bytes(at.px)})


def apply(font_arc: Archive) -> None:
    """Додає українські літери в обидва textfont-и відкритого font-архіву."""
    for name in NAMES:
        font_arc.put(name, extend(Psb(font_arc.get(name))))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", default=str(GAME))
    ap.add_argument("--install", action="store_true")
    a = ap.parse_args()
    font = Archive(Path(a.game) / "wind3d11data", "font")
    apply(font)
    if a.install:
        font.install()
        print("встановлено: textfont12/24 з українськими літерами")
    else:
        out = ROOT / "work" / "build" / "textfont_ua"
        font.write(out)
        print("→", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
