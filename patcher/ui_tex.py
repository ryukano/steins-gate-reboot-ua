"""
Текстури UI-моушенів (E-mote PSB): декодування атласів, заміна і запис назад.

    from ui_tex import Motion
    m = Motion("title")                       # бере work/reboot_motion/title.psb (або з архіву)
    img = m.atlas("tex#000")                  # PIL RGBA
    m.set_atlas("tex#000", img, fmt="RGBA8")  # замінити
    m.save_psb(path) / m.install()            # записати у motion-архів гри

    python ui_tex.py dump title               # → work/ui/title/tex000.png + sheet.png + icons.json
    python ui_tex.py test-rgba8 title         # тест: червона плашка на NEW GAME, RGBA8, у гру
"""
from __future__ import annotations
import argparse, json, struct, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
# сусідні модулі лежать поруч: у робочому репозиторії це tools/, у публічному — patcher/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from psb import Psb, PsbFloat  # noqa: E402
from m2archive import Archive  # noqa: E402

GAME = Path(r"D:\GAMES\Steam\steamapps\common\SGRE")
DATA = GAME / "wind3d11data"
CACHE = ROOT / "work" / "reboot_motion"


def bc7_decode(data: bytes, w: int, h: int) -> Image.Image:
    import texture2ddecoder as t2d
    return Image.frombytes("RGBA", (w, h), t2d.decode_bc7(data, w, h), "raw", "BGRA")


def rect_mesh(m, ic: dict, w: int, h: int, origin: tuple | None = None) -> None:
    """Замінити адаптивну сітку іконки прямокутником на 4 вершини.

    Оригінальна сітка обтягує англійський напис за контуром; якщо її лишити, довший
    український обріжеться по чужій формі. origin=(ox, oy) — зберегти точку привʼязки
    (спрайт росте праворуч/униз, лівий верхній кут на місці); інакше привʼязка в центрі.
    """
    psb = m.psb
    m.mesh_calls.append((id(ic), origin))
    # кеш на самому PSB, а не в словнику за id(): id — це адреса, і звільнений обʼєкт
    # може віддати її наступному разом із чужими індексами
    cached = getattr(psb, "_rect_cache", None)
    if cached is None:
        cached = (psb.add_extra(struct.pack("<8f", 0, 0, 1, 0, 0, 1, 1, 1)),
                  psb.add_extra(struct.pack("<4I", 0, 1, 2, 3)),
                  psb.add_extra(struct.pack("<4I", 0, 1, 3, 2)),
                  psb.add_extra(struct.pack("<4I", 0, 1, 2, 3)),
                  psb.add_extra(b""))
        psb._rect_cache = cached
    verts, strip, hull, hidx, empty = cached
    mesh = ic.get("mesh")
    if not isinstance(mesh, dict):
        return
    pw, ph = w + 2, h + 2
    ox, oy = origin if origin else (w // 2, h // 2)
    tx, ty = (-(ox + 1), -(oy + 1)) if origin else (-pw / 2, -ph / 2)
    mesh["vertices"] = verts
    mesh["tristrip"] = strip
    mesh["convexHulls"] = [hull]
    mesh["concaveHulls"] = [hull]
    mesh["convexIndices"] = hidx
    mesh["concaveIndices"] = hidx
    mesh["concaveConvexDiffIndices"] = empty
    mesh["meshMatrix"] = psb.add_extra(struct.pack("<6f", pw, 0, 0, ph, tx, ty))
    mar = mesh.get("minAreaRect")
    if isinstance(mar, dict):
        mar["cx"] = PsbFloat(pw / 2)
        mar["cy"] = PsbFloat(ph / 2)
        mar["width"] = PsbFloat(pw)
        mar["height"] = PsbFloat(ph)
        mar["angle"] = PsbFloat(0.0)
    ic["originX"] = int(ox)
    ic["originY"] = int(oy)


class Motion:
    def __init__(self, name: str, key: str | None = None, archive: "Archive | None" = None):
        """archive — уже відкритий архів motion. Без нього кожен моушен відкриває свій,
        а це щоразу читання цілого motion_body.bin (0.94 ГБ): на тридцять моушенів
        інсталятора виходило тридцять гігабайтів вводу-виводу.

        Кеш у CACHE ключується лише іменем, тож із ним архів не звіряється. Це доречно
        для тутешніх інструментів (гра одна й та сама), але не для інсталятора: там кеш
        пережив би оновлення гри й підсунув PSB старої ревізії. Тому коли архів передано —
        читаємо з нього і кешу не торкаємось узагалі.
        """
        self.name = name
        if archive is not None:
            raw = archive.get(name)
            self.psb = Psb(raw)
            self.root = self.psb.root
            self.new_chunks = {}
            self.mesh_calls = []
            return
        p = CACHE / f"{name}.psb"
        if p.exists():
            raw = p.read_bytes()
        else:
            arc = Archive(DATA, "motion")
            raw = arc.get(name); CACHE.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
        self.psb = Psb(raw)
        self.root = self.psb.root
        self.new_chunks: dict[int, bytes] = {}
        self.mesh_calls: list[tuple[int, tuple | None]] = []   # порядок правок сітки — див. rect_mesh

    def textures(self) -> dict:
        return {k: v["texture"] for k, v in self.root["source"].items() if isinstance(v, dict) and "texture" in v}

    def atlas(self, src: str) -> Image.Image:
        tex = self.root["source"][src]["texture"]
        w, h = tex["width"], tex["height"]
        data = self.psb.chunk(tex["pixel"].index)
        t = tex["type"]
        if t == "BC7":
            return bc7_decode(data, w, h)
        if t == "RGBA8":
            return Image.frombytes("RGBA", (w, h), data, "raw", "BGRA")
        if t == "A8":
            return Image.frombytes("L", (w, h), data).convert("RGBA")
        raise ValueError(f"формат {t}")

    def icons(self, src: str) -> dict:
        return self.root["source"][src]["icon"]

    def set_atlas(self, src: str, img: Image.Image, fmt: str = "RGBA8"):
        tex = self.root["source"][src]["texture"]
        w, h = tex["width"], tex["height"]
        if img.size != (w, h):
            # атлас збільшено (релокація спрайтів): оновлюємо розміри; truncated_* — фактично використана площа
            tex["width"], tex["height"] = img.size
            tex["truncated_width"] = max(int(tex.get("truncated_width", w)), min(w, img.size[0]))
            # -2 — це гутер, який лишає внизу смуга релокації в ui_sprites.build_motion;
            # якщо пакування смуги колись зміниться, це число має змінитися разом із ним
            tex["truncated_height"] = img.size[1] - 2
        img = img.convert("RGBA")
        # пишемо тільки RGBA8. Читати гра вміє і BC7 (див. bc7_decode), але кодувати
        # його нам нема чим і нема навіщо: місця в архіві вистачає
        if fmt != "RGBA8":
            raise ValueError(f"писати вміємо лише RGBA8, не {fmt}")
        data = img.tobytes("raw", "BGRA")
        tex["type"] = fmt
        self.new_chunks[tex["pixel"].index] = data

    def build(self) -> bytes:
        return self.psb.build(chunks=self.new_chunks or None)

    def save_psb(self, path: Path) -> Path:
        path.write_bytes(self.build()); return path

    def install(self):
        arc = Archive(DATA, "motion")
        arc.put(self.name, self.build())
        arc.install()


def sheet(m: Motion, src: str, out_dir: Path, max_h=200, max_w=700):
    atlas = m.atlas(src)
    icons = sorted(m.icons(src).items())
    small = [(i, ic) for i, ic in icons if ic["height"] <= max_h and ic["width"] <= max_w]
    font = ImageFont.truetype(str(ROOT / "work" / "build" / "sgre_uk.ttf"), 18)
    cols, cw, ch = 4, 760, 120
    img = Image.new("RGBA", (cols * cw, max(1, (len(small) + cols - 1) // cols) * ch), (60, 60, 60, 255))
    d = ImageDraw.Draw(img)
    for k, (iid, ic) in enumerate(small):
        l, t, w, h = int(ic["left"]), int(ic["top"]), int(ic["width"]), int(ic["height"])
        crop = atlas.crop((l, t, l + w, t + h))
        x, y = (k % cols) * cw, (k // cols) * ch
        img.paste(crop, (x + 90, y + 5), crop)
        d.text((x + 5, y + 5), f"{iid}\n{w}x{h}", font=font, fill=(255, 255, 0, 255))
    img.save(out_dir / f"{src.replace('#', '')}_sheet.png")


def cmd_dump(name: str):
    m = Motion(name)
    out = ROOT / "work" / "ui" / name; out.mkdir(parents=True, exist_ok=True)
    meta = {}
    for src, tex in m.textures().items():
        if tex["type"] in ("BC7", "RGBA8", "A8"):
            img = m.atlas(src); img.save(out / f"{src.replace('#', '')}.png")
            sheet(m, src, out)
        meta[src] = dict(type=tex["type"], w=tex["width"], h=tex["height"],
                         icons={k: {kk: v[kk] for kk in ("left", "top", "width", "height", "attr")} for k, v in m.icons(src).items()})
        print(f"  {src}: {tex['type']} {tex['width']}x{tex['height']}, {len(m.icons(src))} icons")
    (out / "icons.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", out)


def cmd_test_rgba8(name: str):
    m = Motion(name)
    src = "tex#000"
    img = m.atlas(src)
    ic = m.icons(src)["0035"]  # NEW GAME (white)
    l, t, w, h = int(ic["left"]), int(ic["top"]), int(ic["width"]), int(ic["height"])
    d = ImageDraw.Draw(img); d.rectangle((l, t, l + w - 1, t + h - 1), fill=(255, 0, 0, 255))
    m.set_atlas(src, img, "RGBA8")
    m.install(); print("встановлено тестовий title з RGBA8 (червона плашка замість NEW GAME)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("name")
    a = ap.parse_args()
    {"dump": cmd_dump, "test-rgba8": cmd_test_rgba8}[a.cmd](a.name)
