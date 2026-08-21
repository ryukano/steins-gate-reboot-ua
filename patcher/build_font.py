"""
Збирає шрифт для українського слота Re:Boot: Hiragino Kaku Gothic W6 (усі JP/символи, як у грі)
+ Source Sans 3 Semibold (латиниця, кирилиця з і/ї/є/ґ, пунктуація), масштабований під висоту
великих літер Hiragino. Результат — TTF (квадратичні контури через cu2qu).

    python build_font.py [--out work/build/sgre_uk.ttf] [--scale 1.188] [--donor sources/fonts/TTF/SourceSans3-Semibold.ttf]

Донор перекриває: ASCII, Latin-1, Latin Ext-A, кирилицю U+0400–04FF, General Punctuation U+2010–203A, ʼ U+02BC.
Решта гліфів (кана, кандзі, ♪ ☆ → ℃, повноширинні) — з Hiragino, щоб в EN-слоті нічого не зникло.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import DecomposingRecordingPen

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "work" / "reboot_font" / "hiragino_pro_w6.otf"
DONOR = ROOT / "sources" / "fonts" / "TTF" / "SourceSans3-Semibold.ttf"

OVERRIDE_RANGES = [(0x20, 0x7E), (0xA0, 0xFF), (0x100, 0x17F), (0x400, 0x4FF), (0x2010, 0x203A), (0x2BC, 0x2BC), (0x2116, 0x2116)]


def in_override(cp: int) -> bool:
    return any(a <= cp <= b for a, b in OVERRIDE_RANGES)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=str(BASE))
    ap.add_argument("--donor", default=str(DONOR))
    ap.add_argument("--scale", type=float, default=None, help="масштаб донора; типово capHeight(base)/capHeight(donor)")
    ap.add_argument("--out", default=str(ROOT / "work" / "build" / "sgre_uk.ttf"))
    ap.add_argument("--family", default="SGRE UK Text")
    a = ap.parse_args()

    base = TTFont(a.base)
    donor = TTFont(a.donor)
    upem = base["head"].unitsPerEm
    scale = a.scale or (base["OS/2"].sCapHeight / donor["OS/2"].sCapHeight) * (upem / donor["head"].unitsPerEm)
    print(f"base upem {upem}, donor upem {donor['head'].unitsPerEm}, scale {scale:.4f}")

    base_cmap = base.getBestCmap()
    donor_cmap = donor.getBestCmap()
    base_gs = base.getGlyphSet()
    donor_gs = donor.getGlyphSet()
    base_hmtx = base["hmtx"]
    donor_hmtx = donor["hmtx"]

    glyphs: dict[str, object] = {}
    metrics: dict[str, tuple[int, int]] = {}
    cmap: dict[int, str] = {}
    order: list[str] = [".notdef"]

    # .notdef з базового
    def conv(gs, name, tr=None):
        pen = TTGlyphPen(None)
        qpen = Cu2QuPen(pen, max_err=1.0, reverse_direction=True)
        target = TransformPen(qpen, tr) if tr else qpen
        rec = DecomposingRecordingPen(gs)   # компоненти → контури (імена гліфів змінюються)
        gs[name].draw(rec)
        rec.replay(target)
        return pen.glyph()

    nd = base.getGlyphOrder()[0]
    glyphs[".notdef"] = conv(base_gs, nd)
    metrics[".notdef"] = base_hmtx.metrics.get(nd, (upem // 2, 0))

    # 1) базовий шрифт — усе, крім перекритих кодпоінтів
    used_base: set[str] = set()
    for cp, gname in base_cmap.items():
        if in_override(cp) and cp in donor_cmap:
            continue
        cmap[cp] = "b_" + gname
        used_base.add(gname)
    for gname in sorted(used_base):
        nn = "b_" + gname
        glyphs[nn] = conv(base_gs, gname)
        metrics[nn] = base_hmtx[gname]
        order.append(nn)
    # 2) донор — перекриті кодпоінти (масштабовано)
    tr = (scale, 0, 0, scale, 0, 0)
    used_donor: set[str] = set()
    for cp, gname in donor_cmap.items():
        if in_override(cp):
            cmap[cp] = "d_" + gname
            used_donor.add(gname)
    for gname in sorted(used_donor):
        nn = "d_" + gname
        glyphs[nn] = conv(donor_gs, gname, tr)
        adv, lsb = donor_hmtx[gname]
        metrics[nn] = (round(adv * scale), round(lsb * scale))
        order.append(nn)
    print(f"гліфів: base {len(used_base)}, donor {len(used_donor)}, cmap {len(cmap)}")

    fb = FontBuilder(upem, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    # lsb з контурів (TTGlyph xMin) — перерахувати після setupGlyf
    glyf = fb.font["glyf"]
    fixed = {}
    for n in order:
        adv = metrics[n][0]
        g = glyf[n]
        lsb = g.xMin if hasattr(g, "xMin") and g.numberOfContours != 0 else metrics[n][1]
        fixed[n] = (adv, lsb)
    fb.setupHorizontalMetrics(fixed)
    hhea = base["hhea"]; os2 = base["OS/2"]
    fb.setupHorizontalHeader(ascent=hhea.ascent, descent=hhea.descent, lineGap=hhea.lineGap)
    fb.setupNameTable({"familyName": a.family, "styleName": "Semibold", "fullName": a.family + " Semibold",
                       "psName": a.family.replace(" ", "") + "-Semibold", "uniqueFontIdentifier": a.family + " 1.0",
                       "version": "Version 1.0", "copyright": "Hiragino Kaku Gothic Pro W6 (SCREEN) + Source Sans 3 (Adobe, OFL); fan build"})
    fb.setupOS2(sTypoAscender=getattr(os2, "sTypoAscender", hhea.ascent), sTypoDescender=getattr(os2, "sTypoDescender", hhea.descent),
                sTypoLineGap=getattr(os2, "sTypoLineGap", 0), usWinAscent=getattr(os2, "usWinAscent", hhea.ascent),
                usWinDescent=getattr(os2, "usWinDescent", -hhea.descent), sCapHeight=os2.sCapHeight, sxHeight=os2.sxHeight,
                usWeightClass=600, usWidthClass=5, fsSelection=0x40, achVendID="SGUK")
    fb.setupPost(keepGlyphNames=False)
    fb.setupHead(unitsPerEm=upem, fontRevision=1.0)
    fb.setupMaxp()
    fb.setupDummyDSIG()
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    fb.save(str(out))
    print(f"→ {out}  ({out.stat().st_size} б)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
