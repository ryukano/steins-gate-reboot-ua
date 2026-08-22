"""
Перемальовування текстових спрайтів UI (E-mote атласи) українською.

    python ui_sprites.py render title            — зібрати title з UA-спрайтами у work/ui/title/preview/*.png (без гри)
    python ui_sprites.py install title [menu …]  — зібрати й покласти в motion-архів гри
    python ui_sprites.py install --all
    python ui_sprites.py restore                 — повернути motion-архів з _orig/

Таблиця спрайтів — ui_sprites_table.py: SPRITES[motion][src][icon_id] = текст або dict(text=…, style=…, …).
Стиль «auto»: із оригінального спрайта беремо колір тла (піксель у кутку), колір тексту (найчастіший не-тло),
межі тексту (висота капітелей, лівий відступ, центрування) — і малюємо так само. Якщо напис довший за спрайт —
зменшуємо кегль (повні слова, як вирішено).
"""
from __future__ import annotations
import argparse, collections, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
# сусідні модулі лежать поруч: у робочому репозиторії це tools/, у публічному — patcher/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ui_tex import Motion, DATA  # noqa: E402
from psb import PsbFloat, PsbDouble, UArr  # noqa: E402
import struct
from m2archive import Archive  # noqa: E402
import ui_sprites_table as T  # noqa: E402

FONTS = {
    "oswald": ROOT / "sources" / "fonts" / "Oswald-Bold.ttf",
    "oswald-semi": ROOT / "sources" / "fonts" / "Oswald-SemiBold.ttf",
    "oswald-med": ROOT / "sources" / "fonts" / "Oswald-Medium.ttf",
    "sans": ROOT / "sources" / "fonts" / "TTF" / "SourceSans3-Semibold.ttf",
    "sans-bold": ROOT / "sources" / "fonts" / "TTF" / "SourceSans3-Bold.ttf",
    "sans-reg": ROOT / "sources" / "fonts" / "TTF" / "SourceSans3-Regular.ttf",
    "sans-black": ROOT / "sources" / "fonts" / "TTF" / "SourceSans3-Black.ttf",
    "game": ROOT / "work" / "build" / "sgre_uk.ttf",
    "garamond": ROOT / "sources" / "fonts" / "EBGaramond-Medium.ttf",
    "garamond-semi": ROOT / "sources" / "fonts" / "EBGaramond-SemiBold.ttf",
}


def measure(sprite: Image.Image, bg: tuple | None = None, force_transparent: bool = False) -> dict:
    """Вимірює оригінальний спрайт: тло (найчастіший непрозорий колір, якщо непрозорих >50%), колір тексту, bbox тексту.
    force_transparent=True — спрайт без плашки (напис щільний, з контуром): текст = усе непрозоре, тло нема."""
    w, h = sprite.size
    px = sprite.load()
    if force_transparent:
        xs = [x for y in range(h) for x in range(w) if px[x, y][3] >= 100]
        ys = [y for y in range(h) for x in range(w) if px[x, y][3] >= 100]
        if not xs:
            return dict(bg=None, fg=(255, 255, 255), bbox=(0, 0, w, h), transparent=True, box=(0, 0, w, h))
        cols = collections.Counter((px[x, y][0] // 8 * 8, px[x, y][1] // 8 * 8, px[x, y][2] // 8 * 8)
                                   for y in range(h) for x in range(w) if px[x, y][3] >= 200)
        fg = tuple(min(255, c + 4) for c in cols.most_common(1)[0][0]) if cols else (255, 255, 255)
        box = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
        return dict(bg=None, fg=fg, bbox=box, transparent=True, box=box)
    # тло — найчастіший колір на периметрі НЕПРОЗОРОЇ частини спрайта (плашка може бути вужча за спрайт)
    oxs = [x for y in range(h) for x in range(w) if px[x, y][3] >= 200]
    oys = [y for y in range(h) for x in range(w) if px[x, y][3] >= 200]
    if not oxs:
        return dict(bg=None, fg=(255, 255, 255), bbox=(0, 0, w, h), transparent=True, box=(0, 0, w, h))
    ox0, oy0, ox1, oy1 = min(oxs), min(oys), max(oxs) + 1, max(oys) + 1
    border = collections.Counter()
    for x in range(ox0, ox1):
        for y in (oy0, oy0 + 1, oy1 - 2, oy1 - 1):
            p = px[x, max(0, min(h - 1, y))]
            if p[3] >= 200:
                border[(p[0] // 8 * 8, p[1] // 8 * 8, p[2] // 8 * 8)] += 1
    for y in range(oy0, oy1):
        for x in (ox0, ox0 + 1, ox1 - 2, ox1 - 1):
            p = px[max(0, min(w - 1, x)), y]
            if p[3] >= 200:
                border[(p[0] // 8 * 8, p[1] // 8 * 8, p[2] // 8 * 8)] += 1
    transparent = len(oxs) < 0.5 * (ox1 - ox0) * (oy1 - oy0)   # мало непрозорого → це просто текст без плашки
    if bg is None and not transparent:
        # тло плашки = колір периметра P; але якщо звʼязна область кольору P, що торкається краю, — лише тонкий
        # контур (< 25 % площі; плашки меню з темною обвідкою), тло = найчастіший колір поза цим контуром
        P = border.most_common(1)[0][0]

        def near(p, c):
            return p[3] >= 200 and max(abs(p[0] - c[0]), abs(p[1] - c[1]), abs(p[2] - c[2])) <= 40
        pm = [[near(px[x, y], P) for x in range(w)] for y in range(h)]
        ring = set()
        for c in _components(pm, w, h):
            if c[0] <= ox0 or c[1] <= oy0 or c[2] >= ox1 or c[3] >= oy1:
                ring.update(c[4])
        bg = P
        if len(ring) < 0.25 * len(oxs):
            rest = collections.Counter((px[x, y][0] // 8 * 8, px[x, y][1] // 8 * 8, px[x, y][2] // 8 * 8)
                                       for y in range(oy0, oy1) for x in range(ox0, ox1)
                                       if px[x, y][3] >= 200 and (x, y) not in ring)
            if rest:
                I = rest.most_common(1)[0][0]
                if max(abs(I[0] - P[0]), abs(I[1] - P[1]), abs(I[2] - P[2])) > 60:
                    bg = I
    box = (ox0, oy0, ox1, oy1)

    def is_text(p):
        if p[3] < 100:
            return False
        if bg is None:
            return True
        return max(abs(p[0] - bg[0]), abs(p[1] - bg[1]), abs(p[2] - bg[2])) > 60
    mask = [[is_text(px[x, y]) for x in range(w)] for y in range(h)]
    comps = _components(mask, w, h)
    if not comps:
        return dict(bg=bg, fg=(255, 255, 255), bbox=box, transparent=transparent, box=box)
    if bg is not None:
        # літери: не торкаються краю непрозорої частини (контур плашки) і не дрібніші за половину найвищої
        inner = [c for c in comps if c[0] > ox0 and c[1] > oy0 and c[2] < ox1 and c[3] < oy1]
        if inner:
            hmax = max(c[3] - c[1] for c in inner)
            letters = [c for c in inner if c[3] - c[1] >= 0.45 * hmax and c[2] - c[0] >= 3]
            comps = letters or inner
    cols = collections.Counter()
    for c in comps:
        for (x, y) in c[4]:
            p = px[x, y]; cols[(p[0] // 8 * 8, p[1] // 8 * 8, p[2] // 8 * 8)] += 1
    fg = cols.most_common(1)[0][0]
    fg = tuple(min(255, c + 4) for c in fg)
    bbox = (min(c[0] for c in comps), min(c[1] for c in comps), max(c[2] for c in comps), max(c[3] for c in comps))
    return dict(bg=bg, fg=fg, bbox=bbox, transparent=transparent, box=box, comps=comps)


def _components(mask, w, h):
    """Звʼязні компоненти (8-сусідство) маски → список (x0, y0, x1, y1, pixels)."""
    seen = [[False] * w for _ in range(h)]
    out = []
    for y0 in range(h):
        for x0 in range(w):
            if not mask[y0][x0] or seen[y0][x0]:
                continue
            stack = [(x0, y0)]; seen[y0][x0] = True; pts = []
            while stack:
                x, y = stack.pop(); pts.append((x, y))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h and mask[ny][nx] and not seen[ny][nx]:
                            seen[ny][nx] = True; stack.append((nx, ny))
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            out.append((min(xs), min(ys), max(xs) + 1, max(ys) + 1, pts))
    return out


def fit_font(path: Path, text: str, cap_h: int, max_w: int) -> ImageFont.FreeTypeFont:
    """Кегль, за якого висота великих літер = cap_h (або менше, щоб влізти в max_w)."""
    size = max(8, int(cap_h * 1.45))
    for _ in range(60):
        f = ImageFont.truetype(str(path), size)
        bb = f.getbbox("НОВЕ")  # капітелі
        ch = bb[3] - bb[1]
        tw = f.getlength(text)
        if ch > cap_h * 1.02 or tw > max_w:
            size -= 1
            if size < 8:
                break
            continue
        if ch < cap_h * 0.96 and tw < max_w * 0.97:
            size += 1
            f2 = ImageFont.truetype(str(path), size)
            bb2 = f2.getbbox("НОВЕ")
            if bb2[3] - bb2[1] > cap_h * 1.02 or f2.getlength(text) > max_w:
                size -= 1
                return ImageFont.truetype(str(path), size)
            continue
        return f
    return ImageFont.truetype(str(path), max(8, size))


def render_sprite(orig: Image.Image, spec: dict) -> Image.Image:
    """Повертає новий спрайт того ж розміру."""
    w, h = orig.size
    if spec.get("inset"):
        return render_inset(orig, spec)
    if spec.get("transparent"):
        # напис без плашки, але щільний (білий текст із тонким контуром) — вимірювалка вважає його плашкою
        m = measure(orig, None, force_transparent=True)
    else:
        m = measure(orig, spec.get("bg"))
    text = spec["text"]
    font_key = spec.get("font", "oswald")
    pad = spec.get("pad")
    align = spec.get("align")  # left | center
    bx0, by0, bx1, by1 = m["bbox"]
    if pad is None:
        pad = bx0
    if align is None:
        # центроване, якщо лівий і правий відступи (у межах плашки) приблизно рівні
        ox0_, _, ox1_, _ = m["box"]
        align = "center" if abs((bx0 - ox0_) - (ox1_ - bx1)) <= 4 and bx0 - ox0_ > 2 else "left"
    cap_h = spec.get("cap_h") or (by1 - by0)
    if spec.get("upper", True):
        text = text.upper()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    ox0, oy0, ox1, oy1 = m["box"]
    if m["bg"] is not None and not m["transparent"]:
        # зберігаємо оригінальну плашку (з її краями), затираючи текст усередині неї
        out = orig.copy()
        d = ImageDraw.Draw(out)
        d.rectangle((max(ox0 + 1, bx0 - 2), max(oy0 + 1, by0 - 2), min(ox1 - 2, bx1 + 1), min(oy1 - 2, by1 + 1)), fill=m["bg"] + (255,))
    left_pad = bx0 - ox0
    max_w = (ox1 - ox0) - left_pad - (left_pad if align == "center" else max(2, left_pad // 2))
    pad = bx0 if spec.get("pad") is None else ox0 + spec["pad"]
    f = fit_font(FONTS[font_key], text, cap_h, max_w)
    # повний bbox тексту (з діакритикою Й/Ї/Ґ) має вміститися у плашку по висоті — інакше зменшуємо кегль
    box_h = (oy1 - oy0) - 2
    for _ in range(40):
        bb = f.getbbox(text)
        if bb[3] - bb[1] <= box_h and f.getlength(text) <= max_w:
            break
        f = ImageFont.truetype(str(FONTS[font_key]), max(8, f.size - 1))
    bb = f.getbbox(text)
    tw = bb[2] - bb[0]
    cap_bb = f.getbbox("Н")
    if spec.get("baseline") is not None:
        # базова лінія на фіксованій відстані від верху оригінального bbox (плашки імен: капітелі 23px)
        ty = by0 + spec["baseline"] - cap_bb[3]
    elif bb[1] < cap_bb[1] - 1:
        # є верхня діакритика: центруємо повний bbox у плашці
        ty = oy0 + ((oy1 - oy0) - (bb[3] - bb[1])) // 2 - bb[1]
    else:
        # як в оригіналі: капітелі на тій самій висоті
        ty = by0 - cap_bb[1] + (cap_h - (cap_bb[3] - cap_bb[1])) // 2
        ty = max(ty, oy0 + 1 - bb[1]); ty = min(ty, oy1 - 1 - bb[3])
    tx = (ox0 + ox1 - tw) // 2 - bb[0] if align == "center" else pad - bb[0]
    fg = spec.get("fg") or m["fg"]
    STATS.append(dict(text=text, cap=cap_h, got=cap_bb[3] - cap_bb[1], size=f.size, tw=tw, max_w=max_w))
    stroke = spec.get("stroke", 0)
    d.text((tx, ty), text, font=f, fill=tuple(fg) + (255,), stroke_width=stroke, stroke_fill=spec.get("stroke_fill", (0, 0, 0, 255)))
    return out


def render_inset(orig: Image.Image, spec: dict) -> Image.Image:
    """Спрайт із декором (пілюлі панелі): текст малюємо лише в заданому вікні inset=(l,t,r,b) поверх
    оригінального тла bg, колір fg явний; keep_red=True — повернути червоні пікселі оригіналу (перекреслення).
    bg="keep" — тло не зафарбовувати (вікно вже порожнє), shadows=[(dx,dy,(r,g,b[,a])),…] — кольорові тіні під
    текстом (глітч-обвідка кнопки DEFAULT)."""
    w, h = orig.size
    l, t, r, b = spec["inset"]
    if r is None:
        # права межа не задана — декор по краях симетричний (шеврони банера), тож дзеркалимо лівий відступ
        r = w - l
    bg = spec.get("bg") or (40, 40, 40)
    fg = tuple(spec.get("fg") or (192, 192, 188))
    text = spec["text"].upper() if spec.get("upper", True) else spec["text"]
    font_key = spec.get("font", "oswald")
    out = orig.copy(); d = ImageDraw.Draw(out)
    if bg == "clear":
        out.paste(Image.new("RGBA", (r - l, b - t), (0, 0, 0, 0)), (l, t))
    elif isinstance(bg, str) and bg.startswith("patch:"):
        # затерти вікно клаптем тієї ж плити нижче/вище (bg="patch:sy" — той самий діапазон x, рядки від sy)
        sy = int(bg.split(":")[1])
        out.paste(orig.crop((l, sy, r, sy + (b - t))), (l, t))
    elif isinstance(bg, str) and bg.startswith("tile:"):
        # затерти вікно клаптем текстури самого спрайта (bg="tile:sx0:sx1" — стовпчики-донори тієї ж смуги):
        # горизонтальні скан-лінії тайляться безшовно, на відміну від суцільної заливки
        sx0, sx1 = (int(v) for v in bg.split(":")[1:])
        for x in range(l, r, sx1 - sx0):
            out.paste(orig.crop((sx0, t, min(sx1, sx0 + r - x), b)), (x, t))
    elif bg != "keep":
        d.rectangle((l, t, r - 1, b - 1), fill=tuple(bg) + (255,))
    cap_h = spec.get("cap_h") or (b - t)
    f = fit_font(FONTS[font_key], text, cap_h, r - l)
    for _ in range(40):
        bb = f.getbbox(text)
        if bb[3] - bb[1] <= (b - t) and f.getlength(text) <= (r - l):
            break
        f = ImageFont.truetype(str(FONTS[font_key]), max(8, f.size - 1))
    bb = f.getbbox(text)
    cap_bb = f.getbbox("Н")
    STATS.append(dict(text=text, cap=cap_h, got=cap_bb[3] - cap_bb[1], size=f.size, tw=bb[2] - bb[0], max_w=r - l))
    tx = l - bb[0] if spec.get("align") == "left" else (l + r - (bb[2] - bb[0])) // 2 - bb[0]
    if bb[1] < cap_bb[1] - 1:
        ty = t + ((b - t) - (bb[3] - bb[1])) // 2 - bb[1]
    else:
        ty = t + ((b - t) - (cap_bb[3] - cap_bb[1])) // 2 - cap_bb[1]
    for dx, dy, col in spec.get("shadows", ()):
        d.text((tx + dx, ty + dy), text, font=f, fill=tuple(col) if len(col) == 4 else tuple(col) + (255,))
    d.text((tx, ty), text, font=f, fill=fg + (255,))
    if spec.get("keep_red"):
        px_o, px_n = orig.load(), out.load()
        for y in range(h):
            for x in range(w):
                p = px_o[x, y]
                if p[3] > 60 and p[0] > 150 and p[1] < 130 and p[2] < 140:
                    px_n[x, y] = p
    return out


def _bright_clusters(px, x0, x1, y0, y1, gap=5, thr=200):
    """Стовпчики зі світлими (білими) пікселями в смузі y0..y1 → список (cx0, cx1, cy0, cy1); сусідні
    стовпчики з проміжком ≤ gap зливаються."""
    cols = []
    for x in range(x0, x1):
        ys = [y for y in range(y0, y1) if px[x, y][3] >= 200 and min(px[x, y][:3]) >= thr]
        cols.append((min(ys), max(ys) + 1) if ys else None)
    out = []; cur = None
    for i, c in enumerate(cols):
        x = x0 + i
        if c:
            if cur and x - cur[1] <= gap:
                cur = [cur[0], x + 1, min(cur[2], c[0]), max(cur[3], c[1])]
            else:
                if cur:
                    out.append(tuple(cur))
                cur = [x, x + 1, c[0], c[1]]
    if cur:
        out.append(tuple(cur))
    return out


def render_guide(orig: Image.Image, spec: dict) -> Image.Image:
    """Смуга підказок керування (OPERATION GUIDE): [гліф(и)] Текст  [гліф] Текст …, вирівняно праворуч.
    spec["guide"] = [текст, …] — по одному на групу (зліва направо). Гліфи кнопок (білі квадратики ≥ 22×24)
    копіюємо з оригіналу, написи перемальовуємо (білий Source Sans, мішаний регістр) і розкладаємо від правого
    краю з оригінальними проміжками. Старий текст затираємо клаптем порожньої текстури смуги
    (band=(y0,y1) — смуга по вертикалі, blank=(x0,x1) — порожня ділянка-донор)."""
    w, h = orig.size
    px = orig.load()
    by0, by1 = spec.get("band", (5, 58))
    cl = [c for c in _bright_clusters(px, 3, w - 3, by0, by1, gap=3) if (c[1] - c[0]) >= 3 and (c[3] - c[2]) >= 8]

    def is_glyph(c):
        # гліф кнопки — світлий квадратик/кружечок ≥ 22×22 із заповненням ≥ 52 % (літери тексту — вужчі або рідші);
        # кружечок із літерою (○ × △ R) — квадратний (|w−h| ≤ 4) із заповненням ≥ 40 %
        # (glyph_fill у spec — нижчий поріг для розріджених гліфів, напр. 4-крапковий d-pad observer: fill 0.32)
        cw, ch = c[1] - c[0], c[3] - c[2]
        if cw < 22 or ch < 22:
            return False
        n = sum(1 for x in range(c[0], c[1]) for y in range(c[2], c[3]) if px[x, y][3] >= 200 and min(px[x, y][:3]) >= 200)
        fill = n / (cw * ch)
        return fill >= 0.52 or (abs(cw - ch) <= 4 and fill >= spec.get("glyph_fill", 0.4))
    # групи: [гліф(и)] текст; нова група починається з гліфа після тексту (або після проміжку ≥ group_gap)
    groups = [[]]
    for c in cl:
        if groups[-1] and (c[0] - groups[-1][-1][1] >= spec.get("group_gap", 18)
                           or (is_glyph(c) and not is_glyph(groups[-1][-1]))):
            groups.append([])
        groups[-1].append(c)
    groups = [g for g in groups if g]
    parsed = []   # (glyph clusters, text span (x0, x1, y0, y1))
    for g in groups:
        gl = [c for c in g if is_glyph(c)]; tx_ = [c for c in g if not is_glyph(c)]
        if not tx_:
            print(f"  !! guide: група без тексту {g}"); continue
        parsed.append((gl, (min(c[0] for c in tx_), max(c[1] for c in tx_), min(c[2] for c in tx_), max(c[3] for c in tx_))))
    texts = spec["guide"]
    if len(parsed) != len(texts):
        print(f"  !! guide: {len(parsed)} груп у спрайті, {len(texts)} текстів: {[p[1][:2] for p in parsed]}")
    right = parsed[-1][1][1]
    # базова лінія — мода низу текстових кластерів без виносних (низ літер без хвостів)
    bottoms = collections.Counter(c[3] for g in groups for c in g if not is_glyph(c))
    baseline = bottoms.most_common(1)[0][0]
    gaps_t = [t[0] - gl[-1][1] for gl, t in parsed if gl]
    gap_t = spec.get("gap_text", min(gaps_t) if gaps_t else 8)
    gaps_g = [parsed[i + 1][0][0][0] - parsed[i][1][1] for i in range(len(parsed) - 1) if parsed[i + 1][0]]
    gap_g = spec.get("gap_group", min(gaps_g) if gaps_g else 27)
    out = orig.copy()
    ex0 = (parsed[0][0][0][0] if parsed[0][0] else parsed[0][1][0]) - 6; ex1 = spec.get("right_edge", right + 8)
    # донор порожньої текстури: ліва частина смуги до першої групи (або хвіст праворуч від тексту)
    # донор: найширший суцільний проміжок «чистих» стовпчиків (непрозорі, темні по всій смузі) поза текстом
    def clean(x):
        return all(px[x, y][3] >= 250 and max(px[x, y][:3]) < 120 for y in range(by0, by1))
    best = (0, 0); cur = None
    for x in list(range(3, ex0 - 1)) + [None] + list(range(right + 4, w - 3)):
        if x is not None and clean(x):
            cur = x if cur is None else cur
            if x + 1 - cur > best[1] - best[0]:
                best = (cur, x + 1)
        else:
            cur = None
    bx0, bx1 = spec.get("blank") or best
    if bx1 - bx0 >= 8:
        for x in range(ex0, ex1):
            sx = bx0 + (x - bx0) % (bx1 - bx0)
            out.paste(orig.crop((sx, by0, sx + 1, by1)), (x, by0))
    else:
        # текст на всю ширину смуги — тиражуємо по вертикалі чисту смужку над текстом (рядки by0..top-2)
        top = min(min(c[2] for c in g) for g in groups)
        band = max(2, top - 2 - by0)
        for y in range(by0, by1):
            sy = by0 + (y - by0) % band
            out.paste(orig.crop((ex0, sy, ex1, sy + 1)), (ex0, y))
    d = ImageDraw.Draw(out)
    font_key = spec.get("font", "sans")
    cap_h = spec.get("cap_h", 22)
    f = fit_font(FONTS[font_key], "Н", cap_h, 4000)
    cap_bb = f.getbbox("Н")
    fg = tuple(spec.get("fg") or (252, 252, 252))
    stroke = spec.get("stroke", 0)
    # якщо не вміщається від лівого поля (left_min) — спершу стискаємо проміжки, потім кегль
    glyph_w = sum(sum((c[1] - c[0] + 2) for c in gl) + sum(gl[i + 1][0] - gl[i][1] - 2 for i in range(len(gl) - 1)) for gl, _ in parsed)
    left_min = spec.get("left_min", 24)
    for _ in range(200):
        need = sum(f.getbbox(t)[2] - f.getbbox(t)[0] for t in texts) + glyph_w + len(texts) * gap_t + (len(texts) - 1) * gap_g
        if right - need >= left_min:
            break
        if gap_g > 14:
            gap_g -= 1
        elif gap_t > 5:
            gap_t -= 1
        else:
            f = ImageFont.truetype(str(FONTS[font_key]), f.size - 1); cap_bb = f.getbbox("Н")
    cursor = right
    for (gl, _), text in zip(reversed(parsed), reversed(texts)):
        bb = f.getbbox(text); tw = bb[2] - bb[0]
        tx, ty = cursor - tw - bb[0], baseline - cap_bb[3]
        for dx, dy, col in spec.get("shadows", ()):
            d.text((tx + dx, ty + dy), text, font=f, fill=tuple(col) if len(col) == 4 else tuple(col) + (255,),
                   stroke_width=stroke, stroke_fill=tuple(col) if len(col) == 4 else tuple(col) + (255,))
        d.text((tx, ty), text, font=f, fill=fg + (255,), stroke_width=stroke,
               stroke_fill=spec.get("stroke_fill", (0, 0, 0, 255)))
        cursor -= tw + gap_t
        for i, c in enumerate(reversed(gl)):
            gx0, gx1 = c[0] - 1, c[1] + 1
            cursor -= (gx1 - gx0)
            out.paste(orig.crop((gx0, by0, gx1, by1)), (cursor, by0))
            if i < len(gl) - 1:
                cursor -= gl[len(gl) - 1 - i][0] - gl[len(gl) - 2 - i][1] - 2
        cursor -= gap_g
        STATS.append(dict(text=text, cap=cap_h, got=cap_bb[3] - cap_bb[1], size=f.size, tw=tw, max_w=w))
    if cursor < 0:
        print(f"  !! guide: не вмістилося ({-cursor} px за лівим краєм): {texts}")
    return out


def render_guide_light(orig: Image.Image, spec: dict) -> Image.Image:
    """Смуга підказок ретро-режиму (gamemode/command): світлий мармуровий бар, білий текст із чорним контуром,
    темні круглі кнопки-гліфи. spec["guide_light"] = [текст, …] (зліва направо). Ліва частина бару (водяний знак
    sousa setumei) не чіпається — скануємо від scan_from (типово w//2). Гліфи копіюємо смугами повної висоти band,
    слова перемальовуємо білим із чорним контуром, розкладаємо від правого краю (UA довший — росте ліворуч)."""
    w, h = orig.size
    px = orig.load()
    by0, by1 = spec.get("band", (14, 88))
    x0scan = spec.get("scan_from", w // 2)
    # білі кластери (заливка тексту; мармур ~200–235 не проходить поріг 245)
    txt = [c for c in _bright_clusters(px, x0scan, w - 6, by0, by1, gap=8, thr=spec.get("text_thr", 245))
           if c[1] - c[0] >= 3 and c[3] - c[2] >= 8]
    # темні кластери (гліфи-диски і контури ієрогліфів) — шукаємо «яскраве» в інвертованій копії
    from PIL import ImageChops
    rgb = ImageChops.invert(orig.convert("RGB"))
    inv = Image.merge("RGBA", (*rgb.split(), orig.split()[3]))
    ipx = inv.load()
    dark = [c for c in _bright_clusters(ipx, x0scan, w - 6, by0, by1, gap=4, thr=190) if c[1] - c[0] >= 20 and c[3] - c[2] >= 20]

    def white_ratio(c):
        n = sum(1 for x in range(c[0], c[1]) for y in range(c[2], c[3]) if px[x, y][3] >= 200 and min(px[x, y][:3]) >= 245)
        return n / ((c[1] - c[0]) * (c[3] - c[2]))
    # гліф — квадратний диск (|w−h| ≤ 12) майже без білої заливки; контури ієрогліфів — широкі (w ≈ 2h) і білі всередині
    glyphs = [c for c in dark if abs((c[1] - c[0]) - (c[3] - c[2])) <= 12 and white_ratio(c) < 0.15]
    # білі літери всередині дисків (A/B на кнопках Xbox) — не текст
    txt = [c for c in txt if not any(g[0] <= (c[0] + c[1]) // 2 < g[1] and g[2] <= (c[2] + c[3]) // 2 < g[3] for g in glyphs)]
    if not txt or not glyphs:
        print("  !! guide_light: не знайдено тексту/гліфів"); return orig
    # групи: гліф + наступні текстові кластери до наступного гліфа
    items = sorted([("g", c) for c in glyphs] + [("t", c) for c in txt], key=lambda it: it[1][0])
    groups = []
    for kind, c in items:
        if kind == "g":
            groups.append([c, []])
        elif groups:
            groups[-1][1].append(c)
    groups = [g for g in groups if g[1]]
    texts = spec["guide_light"]
    if len(groups) != len(texts):
        print(f"  !! guide_light: {len(groups)} груп, {len(texts)} текстів: {[g[0][:2] for g in groups]}")
    right = max(c[1] for g in groups for c in g[1])
    ex0 = groups[0][0][0] - 8
    ex1 = spec.get("right_edge", right + 10)
    # донор чистого мармуру: найширший блок стовпчиків без кластерів, світлий по всій смузі, ліворуч від гліфів
    def clean(x):
        return all(px[x, y][3] >= 250 and min(px[x, y][:3]) >= 150 for y in range(by0, by1))
    best = (0, 0); cur = None
    for x in range(x0scan, ex0 - 2):
        if clean(x):
            cur = x if cur is None else cur
            if x + 1 - cur > best[1] - best[0]:
                best = (cur, x + 1)
        else:
            cur = None
    out = orig.copy()
    bx0, bx1 = best
    bw = min(48, bx1 - bx0)
    if bw >= 8:
        block = orig.crop((bx1 - bw, by0, bx1, by1))
        for x in range(ex0, ex1, bw):
            out.paste(block.crop((0, 0, min(bw, ex1 - x), by1 - by0)), (x, by0))
    else:
        print("  !! guide_light: нема чистого донора мармуру")
    d = ImageDraw.Draw(out)
    font_key = spec.get("font", "sans-bold")
    cap_h = spec.get("cap_h", 30)
    f = fit_font(FONTS[font_key], "Н", cap_h, 4000)
    cap_bb = f.getbbox("Н")
    fg = tuple(spec.get("fg") or (255, 255, 255))
    stroke = spec.get("stroke", 3)
    gaps_t = [g[1][0][0] - g[0][1] for g in groups]
    gap_t = spec.get("gap_text", min(gaps_t))
    gaps_g = [groups[i + 1][0][0] - max(c[1] for c in groups[i][1]) for i in range(len(groups) - 1)]
    gap_g = spec.get("gap_group", min(gaps_g) if gaps_g else 60)
    # якщо не вміщається від left_min (правіше водяного знака) — стискаємо проміжки, потім кегль
    glyph_w = sum(g[0][1] - g[0][0] + 4 for g in groups)
    left_min = spec.get("left_min", 340)
    for _ in range(200):
        need = sum(f.getbbox(t_)[2] - f.getbbox(t_)[0] for t_ in texts) + glyph_w + len(texts) * gap_t + (len(texts) - 1) * gap_g
        if right - need >= left_min:
            break
        if gap_g > 24:
            gap_g -= 1
        elif gap_t > 10:
            gap_t -= 1
        else:
            f = ImageFont.truetype(str(FONTS[font_key]), f.size - 1); cap_bb = f.getbbox("Н")
    cy = sum((g[0][2] + g[0][3]) // 2 for g in groups) // len(groups)   # центр гліфів — вісь рядка
    cursor = right
    for (gl, _tc), text in zip(reversed(groups), reversed(texts)):
        bb = f.getbbox(text); tw = bb[2] - bb[0]
        tx = cursor - tw - bb[0]
        ty = cy - (cap_bb[1] + cap_bb[3]) // 2
        d.text((tx, ty), text, font=f, fill=fg + (255,), stroke_width=stroke,
               stroke_fill=spec.get("stroke_fill", (12, 12, 12, 255)))
        cursor -= tw + gap_t
        gx0, gx1 = gl[0] - 2, gl[1] + 2
        cursor -= (gx1 - gx0)
        out.paste(orig.crop((gx0, by0, gx1, by1)), (cursor, by0))
        cursor -= gap_g
        STATS.append(dict(text=text, cap=cap_h, got=cap_bb[3] - cap_bb[1], size=f.size, tw=tw, max_w=w))
    if cursor < left_min:
        print(f"  !! guide_light: заліз на водяний знак ({left_min - cursor} px): {texts}")
    return out


STATS: list = []   # статистика останнього render_sprite (кегль/висота капітелей) — для звіту про стиснення


def rect_mesh(m: Motion, ic: dict, w: int, h: int, origin: tuple | None = None):
    """Замінити адаптивний mesh іконки на прямокутник (4 вершини), щоб новий напис не обрізався контуром старого.
    origin=(ox, oy) — зберегти точку привʼязки старої іконки (anchor left/top: спрайт росте праворуч/униз,
    лівий/верхній край лишається на місці); інакше привʼязка в центрі."""
    psb = m.psb
    # кеш тримаємо на самому PSB, а не в словнику за id(): id — це адреса, і після звільнення
    # попереднього моушена новий об'єкт може дістати ту саму адресу разом із чужими індексами
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
    mesh["vertices"] = verts; mesh["tristrip"] = strip
    mesh["convexHulls"] = [hull]; mesh["concaveHulls"] = [hull]
    mesh["convexIndices"] = hidx; mesh["concaveIndices"] = hidx
    mesh["concaveConvexDiffIndices"] = empty
    mesh["meshMatrix"] = psb.add_extra(struct.pack("<6f", pw, 0, 0, ph, tx, ty))
    mar = mesh.get("minAreaRect")
    if isinstance(mar, dict):
        mar["cx"] = PsbFloat(pw / 2); mar["cy"] = PsbFloat(ph / 2); mar["width"] = PsbFloat(pw); mar["height"] = PsbFloat(ph); mar["angle"] = PsbFloat(0.0)
    ic["originX"] = int(ox); ic["originY"] = int(oy)


def _legacy_font(spec: dict) -> str:
    return spec.get("font", "garamond" if not (spec.get("anchor") or spec.get("stretch")) else "oswald")


def reloc_sprite(orig: Image.Image, spec: dict, ic: dict) -> tuple[Image.Image, tuple | None]:
    """Спрайт, що потребує більше місця (relocate / stretch). Повертає (новий спрайт, origin|None):
      • без anchor/stretch (плашки імен): порожнє полотно w×48, текст по центру, базова лінія h-9 (як раніше);
      • anchor="left" + прозорий напис: нове полотно, текст починається там, де в оригіналі (bx0), капітелі на тій
        самій висоті; ширина = за потребою тексту при кеглі scale×оригінал (обмеження max_w), висота — щоб уміс-
        тилися діакритика/виносні; origin старої іконки зберігається → лівий/верхній край на місці;
      • stretch=True (плашка): вставляємо N дубльованих стовпчиків тла ліворуч від тексту, щоб напис уміс-
        тився при кеглі scale×оригінал (max_w — стеля ширини спрайта), далі звичайний render_sprite."""
    import math
    w, h = orig.size
    text = spec["text"].upper() if spec.get("upper", True) else spec["text"]
    font = FONTS[_legacy_font(spec)]
    scale = spec.get("scale", 1.0)
    anchor = spec.get("anchor")
    origin = (int(ic["originX"]), int(ic["originY"])) if anchor in ("left", "right") else None
    if spec.get("stretch") and spec.get("inset"):
        # банер із декором по краях (заголовки категорій config): текст у вікні inset; якщо не вміщається при
        # кеглі scale×cap_h — вставляємо стовпчики тла після лівого краю вікна (спрайт росте, привʼязка в центрі)
        l, t, r, b = spec["inset"]
        if r is None:
            r = w - l            # симетричне вікно (шеврони однакові з обох боків)
        if b is None:
            b = h - t
        cap = int((spec.get("cap_h") or (b - t)) * scale)
        f = fit_font(font, text, cap, 4000)
        n = max(0, math.ceil(f.getlength(text) + 2 * spec.get("margin", 6) - (r - l)))
        if spec.get("max_w"):
            n = min(n, max(0, spec["max_w"] - w))
        if n == 0:
            return render_inset(orig, {**spec, "inset": (l, t, r, b), "cap_h": cap}), None
        split = l + 1
        wide = Image.new("RGBA", (w + n, h), (0, 0, 0, 0))
        wide.paste(orig.crop((0, 0, split, h)), (0, 0))
        col = orig.crop((split, 0, split + 1, h))
        for i in range(n):
            wide.paste(col, (split + i, 0))
        wide.paste(orig.crop((split, 0, w, h)), (split + n, 0))
        return render_inset(wide, {**spec, "inset": (l, t, r + n, b), "cap_h": cap}), None
    if spec.get("stretch"):
        mm = measure(orig, spec.get("bg"))
        bx0, by0, bx1, by1 = mm["bbox"]; ox0, oy0, ox1, oy1 = mm["box"]
        cap = spec.get("cap_h") or (by1 - by0)
        left_pad = bx0 - ox0
        align = spec.get("align") or ("center" if abs((bx0 - ox0) - (ox1 - bx1)) <= 4 and bx0 - ox0 > 2 else "left")
        max_w = (ox1 - ox0) - left_pad - (left_pad if align == "center" else max(2, left_pad // 2))
        f = fit_font(font, text, int(cap * scale), 4000)
        n = max(0, math.ceil(f.getlength(text) - max_w))
        if spec.get("max_w"):
            n = min(n, max(0, spec["max_w"] - w))
        if n == 0:
            return render_sprite(orig, spec), origin
        split = max(ox0 + 2, bx0 - 1)
        wide = Image.new("RGBA", (w + n, h), (0, 0, 0, 0))
        wide.paste(orig.crop((0, 0, split, h)), (0, 0))
        col = orig.crop((split, 0, split + 1, h))
        for i in range(n):
            wide.paste(col, (split + i, 0))
        wide.paste(orig.crop((split, 0, w, h)), (split + n, 0))
        return render_sprite(wide, spec), origin
    if anchor not in ("left", "right"):
        # плашки імен (legacy)
        f = fit_font(font, text, spec.get("cap_h", 24), spec.get("max_w") or 4000)
        w_new = max(w, int(f.getlength(text)) + 6)
        h_new = spec.get("h", 48)
        mm = measure(orig)
        blank = Image.new("RGBA", (w_new, h_new), (0, 0, 0, 0))
        return render_sprite(blank, {"align": "center", "baseline": h_new - 9, **spec, "fg": spec.get("fg") or mm["fg"]}), None
    mm = measure(orig, None, force_transparent=bool(spec.get("transparent")))
    bx0, by0, bx1, by1 = mm["bbox"]
    cap = spec.get("cap_h") or (by1 - by0)
    cap_t = max(8, int(cap * scale))
    f = fit_font(font, text, cap_t, (spec["max_w"] - bx0 - 4) if spec.get("max_w") else 4000)
    bb = f.getbbox(text); cap_bb = f.getbbox("Н")
    tw = bb[2] - bb[0]
    if anchor == "right":
        # правий край напису (і спрайта) на місці, ростемо ліворуч
        w_new = max(w, (w - bx1) + tw + 4)
        pad_l = w_new - (w - bx1) - tw
        origin = (origin[0] + (w_new - w), origin[1])
    else:
        w_new = max(w, bx0 + tw + 4); pad_l = bx0
    baseline = by0 + (cap_bb[3] - cap_bb[1])            # низ капітелей — як в оригіналі
    top = baseline - cap_bb[3] + bb[1]                   # верх повного bbox (діакритика)
    bottom = baseline - cap_bb[3] + bb[3]                # низ (виносні)
    pad_top = max(0, 2 - top)
    h_new = max(h, bottom + pad_top + 3, spec.get("h", 0))
    blank = Image.new("RGBA", (w_new, h_new), (0, 0, 0, 0))
    new = render_sprite(blank, {**spec, "align": "left", "pad": pad_l, "baseline": baseline + pad_top, "cap_h": cap_t,
                                "fg": spec.get("fg") or mm["fg"]})
    return new, (origin[0], origin[1] + pad_top)


VERBOSE = False


def _stat_line(name, src, iid, n0, geom):
    """Друкує (VERBOSE) і запамʼятовує стиснення напису: висота капітелей наша/оригінал."""
    for s in STATS[n0:]:
        s.update(motion=name, src=src, iid=iid, geom=geom)
        if VERBOSE:
            flag = "  <60%!" if s["got"] < 0.6 * s["cap"] else ""
            print(f"  {name} {src} {iid} {geom:>14s} cap {s['cap']:3d}→{s['got']:3d} ({s['got'] / s['cap']:4.0%}) {s['text']}{flag}")


def build_motion(name: str, preview_dir: Path | None = None) -> Motion:
    m = Motion(name)
    table = T.SPRITES.get(name, {})
    # id іконок унікальні в межах PSB, але розкидані по атласах — перегрупувати за фактичним атласом
    regrouped: dict[str, dict] = {}
    for src, icons in table.items():
        for iid, spec in icons.items():
            real = src if iid in m.icons(src) else next((s2 for s2 in m.textures() if iid in m.icons(s2)), None)
            if real is None:
                print(f"  !! {name}: нема іконки {iid}"); continue
            regrouped.setdefault(real, {})[iid] = spec
    for src, icons in regrouped.items():
        atlas = m.atlas(src)
        all_icons = m.icons(src)
        reloc = []  # (iid, spec, orig, new, origin)
        for iid, spec in icons.items():
            if isinstance(spec, str):
                spec = {"text": spec}
            ic = all_icons[iid]
            l, t, w, h = int(ic["left"]), int(ic["top"]), int(ic["width"]), int(ic["height"])
            orig = atlas.crop((l, t, l + w, t + h))
            n0 = len(STATS)
            if spec.get("relocate") or spec.get("stretch"):
                new, origin = reloc_sprite(orig, spec, ic)
                if new.size != (w, h) or spec.get("relocate"):
                    # переносимо у новий рядок внизу атласу (місце на кирилицю з виносними/діакритикою, ширший напис)
                    atlas.paste(Image.new("RGBA", (w, h), (0, 0, 0, 0)), (l, t))
                    reloc.append((iid, spec, orig, new, origin))
                    _stat_line(name, src, iid, n0, f"{w}x{h}→{new.size[0]}x{new.size[1]}")
                    continue
            elif spec.get("guide"):
                new = render_guide(orig, spec)
            elif spec.get("guide_light"):
                new = render_guide_light(orig, spec)
            elif spec.get("keep_left"):
                # ліву частину спрайта (напр., помаранчевий номер поста @channel) лишаємо, напис праворуч від неї
                # перемальовуємо; keep_left="orange" — межа = правий край помаранчевих пікселів + 2
                kl = spec["keep_left"]
                if kl == "orange":
                    pxo = orig.load()
                    ox = [x for y in range(h) for x in range(w) if pxo[x, y][3] > 150 and pxo[x, y][0] > 180 and pxo[x, y][1] < 170 and pxo[x, y][2] < 80]
                    kl = (max(ox) + 3) if ox else 0
                sub = render_sprite(orig.crop((kl, 0, w, h)), spec)
                new = orig.copy(); new.paste(sub, (kl, 0))
            elif spec.get("multi"):
                # кілька написів в одному спрайті (вікна inset) — застосовуємо послідовно
                new = orig
                for sub in spec["multi"]:
                    new = render_sprite(new, sub)
            else:
                new = render_sprite(orig, spec)
            atlas.paste(new, (l, t))
            # обережно з .get(ключ, типове): типове обчислюється завжди, навіть коли ключ є,
            # тож раніше повний попіксельний measure() робився ще раз на кожен спрайт
            if "rect_mesh" in spec:
                need_mesh = spec["rect_mesh"]
            else:
                need_mesh = spec.get("stretch") or measure(orig)["transparent"]
            if need_mesh:
                rect_mesh(m, ic, w, h)
            _stat_line(name, src, iid, n0, f"{w}x{h}")
            if preview_dir:
                pv = Image.new("RGBA", (w, h * 2 + 4), (90, 90, 90, 255))
                pv.paste(orig, (0, 0), orig); pv.paste(new, (0, h + 4), new)
                pv.save(preview_dir / f"{src.replace('#', '')}_{iid}.png")
        if reloc:
            AW, AH = atlas.size
            need_w = max(it[3].width + 2 for it in reloc)
            if need_w > AW:  # напис ширший за атлас (tex#003 128px) — розширюємо і вшир
                big = Image.new("RGBA", (need_w, AH), (0, 0, 0, 0)); big.paste(atlas, (0, 0)); atlas = big; AW = need_w
            rows, x = [[]], 0
            for item in reloc:
                if x + item[3].width + 2 > AW and rows[-1]:
                    rows.append([]); x = 0
                rows[-1].append((x + 1, item)); x += item[3].width + 2
            strip_h = sum(max(it[3].height for _, it in r) + 2 for r in rows) + 2
            big = Image.new("RGBA", (AW, AH + strip_h), (0, 0, 0, 0)); big.paste(atlas, (0, 0)); atlas = big
            y = AH + 1
            for r in rows:
                rh = max(it[3].height for _, it in r)
                for x, (iid, spec, orig, new, origin) in r:
                    w_new, h_new = new.size
                    atlas.paste(new, (x, y))
                    ic = all_icons[iid]
                    ic["left"], ic["top"], ic["width"], ic["height"] = float(x), float(y), w_new, h_new
                    rect_mesh(m, ic, w_new, h_new, origin)
                    if preview_dir:
                        pv = Image.new("RGBA", (max(orig.width, w_new), orig.height + h_new + 4), (90, 90, 90, 255))
                        pv.paste(orig, (0, 0), orig); pv.paste(new, (0, orig.height + 4), new)
                        pv.save(preview_dir / f"{src.replace('#', '')}_{iid}.png")
                y += rh + 2
            print(f"  {name}/{src}: релоковано {len(reloc)} спрайтів, атлас {AW}x{AH} → {atlas.size[0]}x{atlas.size[1]}")
        m.set_atlas(src, atlas, "RGBA8")
    # вирівняти кадри-вибірки спрайтів (плашки імен: в оригіналі coord.y різний під висоту кожного EN-спрайта;
    # наші релоковані спрайти однакової геометрії → один y для всіх)
    fy = getattr(T, "FRAME_Y", {}).get(name)
    if fy:
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
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["render", "install", "restore"])
    ap.add_argument("names", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true", help="друкувати стиснення кожного напису")
    a = ap.parse_args()
    global VERBOSE
    VERBOSE = a.verbose
    if a.cmd == "restore":
        Archive(DATA, "motion").restore(); print("motion повернуто з _orig/"); return 0
    names = list(T.SPRITES) if a.all else a.names
    if a.cmd == "render":
        for n in names:
            pv = ROOT / "work" / "ui" / n / "preview"; pv.mkdir(parents=True, exist_ok=True)
            build_motion(n, pv); print(f"{n}: превʼю → {pv}")
        return 0
    # Archive збирає з _orig/, тому ставимо ВСІ моушени з таблиці щоразу (інакше попередні злетять)
    arc = Archive(DATA, "motion")
    for n in T.SPRITES:
        m = build_motion(n)
        arc.put(n, m.build()); print(f"{n}: зібрано")
    arc.install(); print("встановлено в гру (motion)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
