# -*- coding: utf-8 -*-
"""
Український патч для STEINS;GATE RE:BOOT — установлювач.

Нічого чужого не поширюємо: патч бере архіви ВАШОЇ копії гри, вставляє в них український текст
і перемальовані написи, складає назад. Оригінали зберігаються поруч у теці `_orig` — звідти ж
працює відкат.

    python -m patcher.patch                      — знайти гру самому й поставити все
    python -m patcher.patch --game "D:\\Steam\\steamapps\\common\\SGRE"
    python -m patcher.patch --restore            — повернути англійську
    python -m patcher.patch --only scenario ui   — лише частини (scenario, config, font, ui)
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import os
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from m2archive import Archive  # noqa: E402
from m2crypt import unshell, enshell, DEFAULT_KEY  # noqa: E402
from psb import Psb  # noqa: E402

DATA = ROOT / "data"
FONTS = ROOT / "fonts"
SLOT_EN = 1                      # у грі чотири мовні слоти: jp, en, tc, sc — займаємо англійський
FACE, FONT_FILE = "textuk", "sgre_uk.ttf"

APPID = "4012810"


def log(msg: str):
    print(msg, flush=True)


def steam_root() -> Path | None:
    """Куди встановлено сам Steam — питаємо реєстр, а не вгадуємо."""
    try:
        import winreg
    except ImportError:
        return None
    for hive, key, name in (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
    ):
        try:
            with winreg.OpenKey(hive, key) as k:
                p = Path(winreg.QueryValueEx(k, name)[0])
            if p.is_dir():
                return p
        except OSError:
            continue
    return None


def steam_libraries(root: Path) -> list[Path]:
    """Усі бібліотеки Steam: сама тека плюс перелічені в libraryfolders.vdf.

    Гру можна тримати на іншому диску й у теці з довільною назвою, тож перебирати здогади
    безглуздо — Steam сам веде список бібліотек.
    """
    libs = [root]
    vdf = root / "steamapps" / "libraryfolders.vdf"
    try:
        txt = vdf.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return libs
    for m in re.finditer(r'"path"\s+"([^"]+)"', txt):      # "path"  "D:\\SteamLibrary"
        p = Path(m.group(1).replace("\\\\", "\\"))
        if p.is_dir() and p not in libs:
            libs.append(p)
    return libs


def _as_game_dir(p: Path | None, max_depth: int = 6, max_dirs: int = 8000) -> Path | None:
    """Тека гри — та, де лежить wind3d11data.

    Людина, обираючи теку вручну, майже завжди тицяє вище, ніж треба: не в …\\common\\SGRE,
    а в D:\\GAMES або в корінь бібліотеки Steam. Тому спускаємося вглиб, але з двома запобіжниками
    (глибина й кількість тек), щоб вибір C:\\ не перетворився на сканування диска.
    """
    if p is None or not p.is_dir():
        return None
    if (p / "wind3d11data").is_dir():
        return p
    seen, level = 0, [p]
    for _ in range(max_depth):
        nxt = []
        for d in level:
            try:
                children = [c for c in d.iterdir() if c.is_dir()]
            except OSError:
                continue
            for c in children:
                if c.name.lower() == "wind3d11data":
                    return d
                seen += 1
                if seen > max_dirs:
                    return None
                nxt.append(c)
        if not nxt:
            return None
        level = nxt
    return None


def pick_folder(title: str) -> Path | None:
    """Рідний віндовий діалог вибору теки: самий shell32, нічого зайвого в збірку не тягне."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class BROWSEINFO(ctypes.Structure):
            _fields_ = [("hwndOwner", wintypes.HWND), ("pidlRoot", ctypes.c_void_p),
                        ("pszDisplayName", wintypes.LPWSTR), ("lpszTitle", wintypes.LPCWSTR),
                        ("ulFlags", wintypes.UINT), ("lpfn", ctypes.c_void_p),
                        ("lParam", wintypes.LPARAM), ("iImage", ctypes.c_int)]

        shell32, ole32 = ctypes.windll.shell32, ctypes.windll.ole32
        shell32.SHBrowseForFolderW.restype = ctypes.c_void_p      # на 64 біт інакше вріже вказівник
        shell32.SHGetPathFromIDListW.argtypes = [ctypes.c_void_p, wintypes.LPWSTR]
        ole32.OleInitialize(None)     # саме Ole, а не Co: інакше сучасний діалог мовчки не відкриється
        bi = BROWSEINFO()
        name_buf = ctypes.create_unicode_buffer(260)   # тримаємо посилання: Windows пише сюди назву
        bi.pszDisplayName = ctypes.cast(name_buf, wintypes.LPWSTR)
        bi.lpszTitle = title
        bi.ulFlags = 0x0001 | 0x0040      # лише теки файлової системи + сучасний вигляд діалогу
        pidl = shell32.SHBrowseForFolderW(ctypes.byref(bi))
        if not pidl:
            return None
        buf = ctypes.create_unicode_buffer(1024)
        ok = shell32.SHGetPathFromIDListW(pidl, buf)
        ole32.CoTaskMemFree(pidl)
        return Path(buf.value) if ok and buf.value else None
    except Exception:  # noqa: BLE001 — діалог не критичний, нижче є запасний шлях
        return None


def ask_game_dir() -> Path | None:
    """Гру не знайдено: показуємо діалог, а якщо він недоступний — просимо ввести шлях."""
    print("Не знайшов гру автоматично. Зараз відкриється вікно — вкажіть теку гри.")
    got = _as_game_dir(pick_folder("Оберіть теку гри STEINS;GATE RE:BOOT"))
    if got:
        print(f"Гра: {got}")
        return got
    try:
        typed = input("Шлях до теки гри (Enter — вийти): ").strip().strip('"')
    except (EOFError, KeyboardInterrupt):
        return None
    return _as_game_dir(Path(typed)) if typed else None


def find_game(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if (p / "wind3d11data").is_dir():
            return p
        raise SystemExit(f"У теці {p} немає wind3d11data — це не тека гри.")

    root = steam_root()
    if root:
        for lib in steam_libraries(root):
            apps = lib / "steamapps"
            # найнадійніше — маніфест гри: у ньому записана тека встановлення
            manifest = apps / f"appmanifest_{APPID}.acf"
            if manifest.exists():
                try:
                    m = re.search(r'"installdir"\s+"([^"]+)"',
                                  manifest.read_text(encoding="utf-8", errors="ignore"))
                except OSError:
                    m = None
                if m and (apps / "common" / m.group(1) / "wind3d11data").is_dir():
                    return apps / "common" / m.group(1)
            if (apps / "common" / "SGRE" / "wind3d11data").is_dir():
                return apps / "common" / "SGRE"

    got = ask_game_dir()
    if got:
        return got
    raise SystemExit(
        "Теку гри не вказано.\n"
        "Можна й одразу ключем — шлях до теки, де лежить wind3d11data, наприклад:\n"
        '  SGRE-UA-Setup.exe --game "D:\\SteamLibrary\\steamapps\\common\\SGRE"')


def load_py(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------- версія гри й свіжість резервних копій

BUILT_FOR = "1050"          # ревізія гри, під яку зібрано переклад
STATE_FILE = "patch_state.json"
STEMS = ("scenario", "config", "font", "motion")


def game_revision(data_dir: Path) -> str | None:
    """Ревізія гри з config-архіву. Читаємо з _orig, якщо він є: там незаймана копія."""
    try:
        return str(Psb(Archive(data_dir, "config").get("revision")).root.get("revision") or "") or None
    except Exception:  # noqa: BLE001
        return None


def signature(path: Path) -> str:
    """Відбиток файлу: розмір плюс хеш початку й кінця.

    Повністю хешувати не можна — motion_body.bin важить під гігабайт, і гравець чекав би
    щоразу. Для того, щоб помітити оновлення гри, розміру й країв цілком досить.
    """
    import hashlib
    st = path.stat()
    h = hashlib.sha1()
    with path.open("rb") as fh:
        h.update(fh.read(1 << 20))
        if st.st_size > (2 << 20):
            fh.seek(-(1 << 20), os.SEEK_END)
            h.update(fh.read(1 << 20))
    return f"{st.st_size}:{h.hexdigest()[:16]}"


def _state_path(data_dir: Path) -> Path:
    return data_dir / "_orig" / STATE_FILE


def load_state(data_dir: Path) -> dict:
    import json
    try:
        return json.loads(_state_path(data_dir).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def save_state(data_dir: Path):
    """Запам'ятати, що ми поклали в гру й що лежить у резерві."""
    import json
    orig = data_dir / "_orig"
    if not orig.is_dir():
        return
    state = {"built_for": BUILT_FOR, "orig": {}, "installed": {}}
    for stem in STEMS:
        f = f"{stem}_body.bin"
        if (orig / f).exists():
            state["orig"][stem] = signature(orig / f)
        if (data_dir / f).exists():
            state["installed"][stem] = signature(data_dir / f)
    _state_path(data_dir).write_text(json.dumps(state, indent=1), encoding="utf-8")


def refresh_backups(data_dir: Path) -> list[str]:
    """Якщо Steam оновив гру, резервні копії застаріли — і патч поверне старий вміст.

    Тому перед роботою звіряємо: якщо теперішній файл гри не збігається ні з тим, що ми
    самі записали минулого разу, ні з резервною копією, — гру оновили. Тоді стару копію
    відкладаємо вбік і робимо нову з поточного файлу.
    """
    orig = data_dir / "_orig"
    state = load_state(data_dir)
    if not orig.is_dir() or not state:
        return []
    updated = []
    for stem in STEMS:
        f = f"{stem}_body.bin"
        cur = data_dir / f
        if not cur.exists() or not (orig / f).exists():
            continue
        sig = signature(cur)
        if sig == state.get("installed", {}).get(stem):
            continue                       # це наш власний файл — усе гаразд
        if sig == state.get("orig", {}).get(stem):
            continue                       # ще не патчений оригінал — теж гаразд
        stamp = time.strftime("%Y%m%d")
        for suffix in (f"{stem}_body.bin", f"{stem}_info.psb.m"):
            old = orig / suffix
            if old.exists():
                # os.replace, а не rename: інакше повторний запуск того самого дня
                # спіткнеться об уже наявне ім'я
                os.replace(old, orig / f"{suffix}.before{stamp}")
            shutil.copy2(data_dir / suffix, orig / suffix)
        # одразу оновлюємо стан, щоб наступний запуск не порахував гру оновленою вдруге
        state.setdefault("orig", {})[stem] = signature(orig / f"{stem}_body.bin")
        updated.append(stem)
    if updated:
        import json
        _state_path(data_dir).write_text(json.dumps(state, indent=1), encoding="utf-8")
    return updated


# ---------------------------------------------------------------- сценарій

def patch_scenario(data_dir: Path):
    """Сценарій лежить не звичайним архівом, а як body + маніфест зі зсувами,
    тому перезбираємо його вручну — так само, як це робить гра при читанні."""
    ua: dict[str, dict[tuple[str, int], str]] = {}
    with (DATA / "scenario_ua.tsv").open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            ua.setdefault(r["file"], {})[(r["scene"], int(r["idx"]))] = r["ua"].replace("\\n", "\n")

    orig = data_dir / "_orig"
    orig.mkdir(exist_ok=True)
    for f in ("scenario_info.psb.m", "scenario_body.bin"):
        if not (orig / f).exists():
            shutil.copy2(data_dir / f, orig / f)

    info = Psb(unshell((orig / "scenario_info.psb.m").read_bytes(), DEFAULT_KEY, "scenario_info.psb.m"))
    body = (orig / "scenario_body.bin").read_bytes()
    suffix = (info.root.get("expire_suffix_list") or [""])[0]
    fi = info.root["file_info"]

    new_body = bytearray()
    total = 0
    for name, (off, ln) in list(fi.items()):
        blob = body[off:off + ln]
        rows = ua.get(name)
        if rows:
            psb = Psb(unshell(blob, DEFAULT_KEY, name + suffix))
            n = 0
            for sc in psb.root.get("scenes", []):
                label = sc.get("label", "")
                for i, t in enumerate(sc.get("texts") or []):
                    new = rows.get((label, i))
                    if new is None:
                        continue
                    variants = t[1]
                    if not (isinstance(variants, list) and len(variants) > SLOT_EN
                            and isinstance(variants[SLOT_EN], list)):
                        continue
                    v = variants[SLOT_EN]
                    v[1] = new
                    if len(v) > 2 and isinstance(v[2], int):
                        v[2] = len(new)
                    n += 1
            if n:
                blob = enshell(psb.build(), b"mzs\0", DEFAULT_KEY, name + suffix)
                total += n
        while len(new_body) % 16:
            new_body.append(0)
        fi[name] = [len(new_body), len(blob)]
        new_body += blob

    (data_dir / "scenario_body.bin").write_bytes(bytes(new_body))
    (data_dir / "scenario_info.psb.m").write_bytes(
        enshell(info.build(), b"mzs\0", DEFAULT_KEY, "scenario_info.psb.m"))
    log(f"  сценарій: {total} рядків")


# ---------------------------------------------------------------- config: інтерфейс, TIPS, пошта

ALPHA = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"
ORDER = {c: i for i, c in enumerate(ALPHA)}


def sort_key(s: str):
    s = (s or "").lower().lstrip("«\"'([ ")
    return [ORDER.get(c, 100 + ord(c) % 100) for c in s]


def font_installed(data_dir: Path) -> bool:
    """Чи лежить наш шрифт у ВСТАНОВЛЕНОМУ архіві гри (не в резервній копії _orig)."""
    try:
        info = Psb(unshell((data_dir / "font_info.psb.m").read_bytes(), DEFAULT_KEY, "font_info.psb.m"))
        return (FONT_FILE + ".m") in info.root["file_info"]
    except Exception:  # noqa: BLE001
        return False


def patch_config(data_dir: Path, with_font: bool):
    cfg = Archive(data_dir, "config")
    ui = load_py(DATA / "config_ui.py")
    stats = {}

    t = Psb(cfg.get("text"))
    n = 0
    for k, v in ui.SYSTEM.items():
        if k in t.root and isinstance(t.root[k], list) and len(t.root[k]) > SLOT_EN:
            t.root[k][SLOT_EN] = v
            n += 1
    cfg.put("text", t.build())
    stats["системні"] = n

    f = Psb(cfg.get("flowdata"))
    n = 0
    for node in f.root.get("lang", []):
        val = ui.FLOW.get(node.get("id"))
        if val is not None and isinstance(node.get("labels"), list) and node["labels"]:
            node["labels"][0] = val
            n += 1
    cfg.put("flowdata", f.build())
    stats["блок-схема"] = n

    pm = Psb(cfg.get("phone_master"))
    n = 0
    for c in pm.root.get("contacts_name_list", []):
        val = ui.PHONE_NAMES.get(c.get("id"))
        if val is not None and isinstance(c.get("names"), list) and len(c["names"]) > SLOT_EN:
            c["names"][SLOT_EN] = val
            n += 1
    for w in pm.root.get("wallpapers", []):
        val = ui.WALLPAPERS.get(w.get("id"))
        if val is not None and isinstance(w.get("names"), list) and len(w["names"]) > SLOT_EN:
            w["names"][SLOT_EN] = val
            n += 1
    cfg.put("phone_master", pm.build())
    stats["телефон"] = n

    extras: dict[str, dict[str, dict[str, str]]] = {}
    with (DATA / "extras_ua.tsv").open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            extras.setdefault(r["src"], {}).setdefault(r["id"], {})[r["field"]] = r["ua"]

    # TIPS: після заміни назв перебудовуємо порядок показу під українську абетку
    tips_psb = Psb(cfg.get("tips"))
    L = tips_psb.root["language"][SLOT_EN]
    d2i, lst = L["conv_d2i"], L["tips_list"]
    by_iid = {int(d2i[i]): lst[i] for i in range(len(lst))}
    n = 0
    for iid, entry in by_iid.items():
        tr = extras.get("tips", {}).get(str(iid))
        if not tr:
            continue
        for field in ("name", "note", "ctgr"):
            if tr.get(field):
                entry[field] = tr[field]
                n += 1
        entry["ruby"] = tr.get("name", entry.get("name", ""))
    order = sorted(by_iid, key=lambda i: sort_key(by_iid[i].get("name", "")))
    L["tips_list"] = [by_iid[i] for i in order]
    L["conv_d2i"] = list(order)
    i2d = [0] * (max(by_iid) + 1)
    for di, iid in enumerate(order):
        i2d[iid] = di
    L["conv_i2d"] = i2d
    cfg.put("tips", tips_psb.build())
    stats["TIPS"] = n

    md = Psb(cfg.get("maildata"))
    n = 0
    for mid, m in md.root.items():
        tr = extras.get("mail", {}).get(mid)
        if not tr:
            continue
        for field in ("subject", "body"):
            v = m.get(field)
            if tr.get(field) and isinstance(v, list) and len(v) > SLOT_EN:
                v[SLOT_EN] = tr[field]
                n += 1
    cfg.put("maildata", md.build())
    stats["пошта"] = n

    doc = Psb(cfg.get("maildoc"))
    n = 0
    for i, d in enumerate(doc.root):
        tr = (extras.get("maildoc", {}).get(str(d.get("key") or i))
              or extras.get("maildoc", {}).get(str(i)))
        if tr and tr.get("text") and isinstance(d.get("text"), list) and len(d["text"]) > SLOT_EN:
            d["text"][SLOT_EN] = tr["text"]
            n += 1
    cfg.put("maildoc", doc.build())
    stats["документи"] = n

    # Реєстрацію шрифту треба ставити навіть тоді, коли цього разу шрифт не перезбирали:
    # config щоразу збирається з оригіналу, тож інакше часткове встановлення зняло б кирилицю.
    if not with_font:
        with_font = font_installed(data_dir)

    if with_font:
        init = Psb(cfg.get("init"))
        fl = init.root["fontList"]
        if not any(isinstance(x, dict) and x.get("face") == FACE for x in fl):
            fl.append({"face": FACE, "file": FONT_FILE})
        cfg.put("init", init.build())
        lang = Psb(cfg.get("language"))
        for entry in lang.root:
            if entry.get("prefix") == "en":
                entry["facemap"] = {"text": FACE}
        cfg.put("language", lang.build())

    cfg.install()
    log("  інтерфейс: " + ", ".join(f"{k} {v}" for k, v in stats.items()))


# ---------------------------------------------------------------- шрифт

def patch_font(data_dir: Path, tmp: Path):
    """Гарнітура гри не має кирилиці. Беремо японську гарнітуру з ВАШОГО архіву
    й додаємо до неї латиницю з кирилицею з Source Sans 3 (ліцензія OFL)."""
    font_arc = Archive(data_dir, "font")
    base = tmp / "base.otf"
    base.write_bytes(font_arc.get("hiragino_pro_w6.otf.m"))

    import build_font
    out = tmp / FONT_FILE
    saved = sys.argv
    sys.argv = ["build_font", "--base", str(base),
                "--donor", str(FONTS / "SourceSans3-Semibold.ttf"), "--out", str(out)]
    try:
        build_font.main()
    finally:
        sys.argv = saved

    font_arc.put(FONT_FILE + ".m", out.read_bytes())
    font_arc.install()
    log(f"  шрифт: зібрано ({out.stat().st_size // 1024} КБ) і встановлено")


# ---------------------------------------------------------------- написи на текстурах

def patch_ui(data_dir: Path):
    import ui_tex
    ui_tex.DATA = data_dir
    ui_tex.CACHE = Path(os.environ.get("TEMP", ".")) / "sgre_ua_motion"
    ui_tex.CACHE.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(DATA))          # таблиця написів лежить у data/ — має бути видима до імпорту
    import ui_sprites
    ui_sprites.FONTS = {
        "oswald": FONTS / "Oswald-Bold.ttf",
        "oswald-semi": FONTS / "Oswald-SemiBold.ttf",
        "oswald-med": FONTS / "Oswald-Medium.ttf",
        "sans": FONTS / "SourceSans3-Semibold.ttf",
        "sans-bold": FONTS / "SourceSans3-Bold.ttf",
        "sans-reg": FONTS / "SourceSans3-Regular.ttf",
        "sans-black": FONTS / "SourceSans3-Black.ttf",
        "garamond": FONTS / "EBGaramond-Medium.ttf",
        "garamond-semi": FONTS / "EBGaramond-SemiBold.ttf",
    }
    import ui_sprites_table as T
    ui_sprites.T = T

    arc = Archive(data_dir, "motion")
    for name in T.SPRITES:
        m = ui_sprites.build_motion(name)
        arc.put(name, m.build())
        log(f"    {name}")
    arc.install()
    log("  написи на кнопках і плашках — готово")


# ---------------------------------------------------------------- головне

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", help="тека гри (та, де лежить wind3d11data)")
    ap.add_argument("--restore", action="store_true", help="повернути англійську")
    ap.add_argument("--only", nargs="*", choices=["scenario", "config", "font", "ui"],
                    help="ставити лише вибрані частини")
    a = ap.parse_args()

    game = find_game(a.game)
    data_dir = game / "wind3d11data"
    log(f"Гра: {game}")

    if a.restore:
        orig = data_dir / "_orig"
        if not orig.is_dir():
            raise SystemExit("Немає теки _orig — відкочувати нема з чого.")
        # у _orig лежить не лише резерв: там-таки файл стану й копії, відкладені при
        # оновленні гри (*.beforeYYYYMMDD) — їх у теку гри повертати не можна
        for f in sorted(orig.iterdir()):
            if f.name == STATE_FILE or ".before" in f.name or not f.is_file():
                continue
            shutil.copy2(f, data_dir / f.name)
            log(f"  повернуто {f.name}")
        log("Готово — у грі знову англійська.")
        return 0

    rev = game_revision(data_dir)
    if rev and rev != BUILT_FOR:
        log(f"  ! Ревізія гри {rev}, а переклад зібрано під {BUILT_FOR}.")
        log("    Патч усе одно спробує стати, але частина рядків може не збігтися.")
        log("    Якщо щось піде не так — --restore і напишіть issue з цим номером.")
    elif rev:
        log(f"  ревізія {rev} — та сама, під яку зібрано переклад")

    for stem in refresh_backups(data_dir):
        log(f"  ! Гру оновлено: {stem} відрізняється від нашої резервної копії.")
        log(f"    Стару копію перейменовано, нову зроблено з поточного файлу.")

    parts = a.only or ["scenario", "config", "font", "ui"]
    t0 = time.time()
    tmp = Path(os.environ.get("TEMP", ".")) / "sgre_ua_build"
    tmp.mkdir(parents=True, exist_ok=True)

    if "font" in parts:
        log("Шрифт…")
        patch_font(data_dir, tmp)
    if "scenario" in parts:
        log("Сценарій…")
        patch_scenario(data_dir)
    if "config" in parts:
        log("Інтерфейс, TIPS і пошта…")
        patch_config(data_dir, with_font="font" in parts)
    if "ui" in parts:
        log("Написи на кнопках і плашках (найдовша частина, кілька хвилин)…")
        patch_ui(data_dir)

    save_state(data_dir)
    log(f"\nГотово за {time.time() - t0:.0f} с.")
    log("У грі оберіть мову English — текст буде український.")
    log("Відкат: запустіть інсталятор із ключем --restore")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
