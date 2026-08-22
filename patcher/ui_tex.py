"""
Текстури UI-моушенів (E-mote PSB): декодування атласів, заміна і запис назад.

    from ui_tex import Motion
    m = Motion("title")                       # бере work/reboot_motion/title.psb (або з архіву)
    img = m.atlas("tex#000")                  # PIL RGBA
    m.set_atlas("tex#000", img, fmt="RGBA8")  # замінити (fmt: RGBA8 | BC7 через texconv)
    m.save_psb(path) / m.install()            # записати у motion-архів гри

    python ui_tex.py dump title               # → work/ui/title/tex000.png + sheet.png + icons.json
    python ui_tex.py test-rgba8 title         # тест: червона плашка на NEW GAME, RGBA8, у гру
"""
from __future__ import annotations
import argparse, json, sys, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
# сусідні модулі лежать поруч: у робочому репозиторії це tools/, у публічному — patcher/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from psb import Psb, PsbRes, UArr  # noqa: E402
from m2archive import Archive  # noqa: E402

GAME = Path(r"D:\GAMES\Steam\steamapps\common\SGRE")
DATA = GAME / "wind3d11data"
CACHE = ROOT / "work" / "reboot_motion"
TEXCONV = ROOT / "sources" / "tools" / "texconv.exe"


def bc7_decode(data: bytes, w: int, h: int) -> Image.Image:
    import texture2ddecoder as t2d
    return Image.frombytes("RGBA", (w, h), t2d.decode_bc7(data, w, h), "raw", "BGRA")


def bc7_encode(img: Image.Image) -> bytes:
    """BC7 через DirectXTex texconv (sources/tools/texconv.exe). Повертає сирі блоки без DDS-заголовка."""
    if not TEXCONV.exists():
        raise FileNotFoundError("нема sources/tools/texconv.exe — завантаж DirectXTex texconv або використовуй fmt=RGBA8")
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "in.png"; img.save(src)
        subprocess.run([str(TEXCONV), "-f", "BC7_UNORM", "-m", "1", "-y", "-o", td, str(src)], check=True, capture_output=True)
        dds = (Path(td) / "in.dds").read_bytes()
    # DDS: 4 magic + 124 header (+ 20 DX10 header для BC7)
    off = 4 + 124
    if dds[84:88] == b"DX10":
        off += 20
    return dds[off:]


class Motion:
    def __init__(self, name: str, key: str | None = None):
        self.name = name
        p = CACHE / f"{name}.psb"
        if p.exists():
            raw = p.read_bytes()
        else:
            arc = Archive(DATA, "motion")
            raw = arc.get(name); CACHE.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
        self.psb = Psb(raw)
        self.root = self.psb.root
        self.new_chunks: dict[int, bytes] = {}

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
            tex["truncated_height"] = img.size[1] - 2
        img = img.convert("RGBA")
        if fmt == "RGBA8":
            data = img.tobytes("raw", "BGRA")
        elif fmt == "BC7":
            data = bc7_encode(img)
        else:
            raise ValueError(fmt)
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
