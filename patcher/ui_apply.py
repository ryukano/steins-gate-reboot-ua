# -*- coding: utf-8 -*-
"""
Накладання готової графіки перекладу на моушен-архів гри.

Написи на кнопках, плашки імен і сторінки форуму намальовано заздалегідь і складено в
аркуші (`ui_pack_N.webp`) з маніфестом (`ui_pack.json`), де сказано, що куди класти. Тут лише
накладання: жодних шрифтів, вимірювань і верстки — усе це вже зроблено й перевірено.

Єдине, що доводиться робити на місці, — сітка іконки (`rect_mesh` в `ui_tex`): вершини й
матриця лежать двійковими шматками всередині самого PSB, тож зареєструвати їх можна тільки
в конкретному файлі гравця.
"""
from __future__ import annotations

from PIL import Image

from psb import PsbFloat
from ui_tex import rect_mesh


def apply(m, name: str, sheet: Image.Image, man: dict) -> bool:
    """Накласти на моушен m усе, що маніфест приписує для name. False — нічого не було."""
    entry = man["motions"].get(name)
    if not entry:
        return False

    grow = {s: tuple(wh) for s, wh in entry.get("atlas", {}).items()}
    touched = set(grow)
    for key in ("copy", "clear", "paste"):
        for src, *_ in entry.get(key, []):
            touched.add(src)

    atlases = {}
    for src in touched:
        at = m.atlas(src)
        if src in grow and at.size != grow[src]:
            big = Image.new("RGBA", grow[src], (0, 0, 0, 0))
            big.paste(at, (0, 0))
            at = big
        atlases[src] = at

    # Порядок обовʼязковий. copy читає оригінал, поки clear його не стер; paste кладе
    # зверху лише наші шматки. Так у пакунку немає жодного пікселя з гри — те, що ми
    # не міняли (шапки дописів, плашки, тло), лишається з копії гравця.
    for src, ol, ot, l, t, w, h in entry.get("copy", []):
        atlases[src].paste(atlases[src].crop((ol, ot, ol + w, ot + h)), (l, t))
    for src, l, t, w, h in entry.get("clear", []):
        atlases[src].paste(Image.new("RGBA", (w, h), (0, 0, 0, 0)), (l, t))
    for src, sx, sy, x, y, w, h in entry.get("paste", []):
        atlases[src].paste(sheet.crop((sx, sy, sx + w, sy + h)), (x, y))

    for src, iid, l, t, w, h in entry.get("geom", []):
        ic = m.icons(src)[iid]
        ic["left"], ic["top"], ic["width"], ic["height"] = float(l), float(t), w, h

    for src, iid, ox, oy in entry.get("mesh", []):
        ic = m.icons(src)[iid]
        w, h = int(ic["width"]), int(ic["height"])
        rect_mesh(m, ic, w, h, None if ox is None else (ox, oy))

    fy = entry.get("frame_y")
    if fy:
        # кадри-вибірки плашок імен: в оригіналі coord.y свій під висоту кожного англійського
        # спрайта, а наші однакової геометрії — тож один y на всі
        def walk(o):
            if isinstance(o, dict):
                c = o.get("content")
                if isinstance(c, dict) and c.get("src") in fy and isinstance(c.get("coord"), list):
                    c["coord"][1] = PsbFloat(float(fy[c["src"]]))
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(m.root["object"])

    for src, at in atlases.items():
        m.set_atlas(src, at, "RGBA8")
    return True
