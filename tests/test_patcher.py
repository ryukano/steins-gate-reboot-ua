# -*- coding: utf-8 -*-
"""
Перевірки інсталятора, які не потребують файлів гри.

Запуск: python tests/test_patcher.py

Навмисно без pytest і без даних гри: тест має бігати і в CI на голому Linux, і на машині
розробника під Windows. Усе, що вимагає справжніх архівів, лишається ручною перевіркою.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

# консоль Windows типово не в UTF-8 (на раннерах CI це cp1252) — без цього перший же
# український рядок валить тест замість того, щоб щось перевірити
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "patcher"))
sys.path.insert(0, str(ROOT / "data"))

import patch  # noqa: E402
from m2crypt import keystream, xor_body  # noqa: E402

FAILED: list[str] = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {'OK  ' if ok else 'ПАДІННЯ'} {name}{'  — ' + detail if detail and not ok else ''}")
    if not ok:
        FAILED.append(name)


# ---------------------------------------------------------------- шифрування

def xor_reference(data: bytes, full_key: str, key_len: int = 131, keep_header: int = 8) -> bytes:
    """Повільна, але очевидно правильна реалізація — еталон для швидкої."""
    ks = keystream(full_key, key_len)
    head, body = data[:keep_header], data[keep_header:]
    out = bytearray(body)
    for i in range(len(out)):
        out[i] ^= ks[i % len(ks)]
    return head + bytes(out)


def test_xor():
    print("XOR тіла архіву")
    import os
    for size in (0, 1, 130, 131, 132, 1000, 3 * 131, 1 << 20):
        data = b"HDR12345" + os.urandom(size)
        check(f"збігається з еталоном, тіло {size} Б",
              xor_body(data, "ключ") == xor_reference(data, "ключ"))
    data = b"HDR12345" + os.urandom(5000)
    check("XOR оборотний", xor_body(xor_body(data, "к"), "к") == data)
    check("заголовок не чіпається", xor_body(data, "к")[:8] == data[:8])


# ---------------------------------------------------------------- пошук гри

def test_find_game(tmp: Path):
    print("розпізнавання теки гри")
    game = tmp / "steamapps" / "common" / "SGRE"
    (game / "wind3d11data").mkdir(parents=True)
    check("сама тека гри", patch._as_game_dir(game) == game)
    check("тека рівнем вище", patch._as_game_dir(game.parent) == game)
    check("корінь бібліотеки", patch._as_game_dir(tmp) == game)
    check("стороння тека", patch._as_game_dir(tmp.parent / "нема") is None)
    check("не тека", patch._as_game_dir(None) is None)

    deep = tmp / "a" / "b" / "c" / "d" / "e" / "f" / "g" / "SGRE"
    (deep / "wind3d11data").mkdir(parents=True)
    check("глибше за ліміт — не шукаємо вічно", patch._as_game_dir(tmp / "a") is None)


def test_steam_root(tmp: Path, monkey_home: Path):
    print("пошук кореня Steam")
    if sys.platform == "win32":
        print("  (пропущено: на Windows шлях іде через реєстр)")
        return
    (monkey_home / ".local" / "share" / "Steam" / "steamapps").mkdir(parents=True)
    check("знаходить типовий шлях Linux і Steam Deck",
          patch.steam_root() == monkey_home / ".local" / "share" / "Steam")


def test_no_gui_on_linux():
    print("віконні виклики поза Windows")
    if sys.platform == "win32":
        print("  (пропущено: перевірка саме для не-Windows)")
        return
    check("вибір теки повертає None, а не падає", patch.pick_folder("тест") is None)
    check("діалог кнопок повертає None, а не падає",
          patch.task_dialog("т", "т", [(1, "а"), (2, "б")]) is None)


# ---------------------------------------------------------------- резервні копії

def _sandbox(tmp: Path, buildid: str = "1000"):
    """Підроблена установка: оригінали в _orig, пропатчені файли в грі."""
    lib = tmp / "steamapps"
    game = lib / "common" / "SGRE"
    data = game / "wind3d11data"
    orig = data / "_orig"
    orig.mkdir(parents=True)
    for stem in patch.STEMS:
        for d, tag in ((orig, b"ORIGINAL-"), (data, b"PATCHED-")):
            (d / f"{stem}_body.bin").write_bytes(tag + stem.encode())
            (d / f"{stem}_info.psb.m").write_bytes(b"i" + tag[:4])
    (lib / f"appmanifest_{patch.APPID}.acf").write_text(
        '"AppState"{"buildid" "%s" "installdir" "SGRE"}' % buildid, encoding="utf-8")
    (orig / patch.STATE_FILE).write_text(json.dumps({
        "buildid": buildid,
        "orig": {s: patch.signature(orig / f"{s}_body.bin") for s in patch.STEMS},
        "installed": {s: patch.signature(data / f"{s}_body.bin") for s in patch.STEMS},
    }), encoding="utf-8")
    return game, data, orig, lib


def _state(orig: Path) -> dict:
    return json.loads((orig / patch.STATE_FILE).read_text(encoding="utf-8"))


def test_backups_survive_interrupted_install(tmp: Path):
    print("перерване встановлення не з'їдає оригінали")
    game, data, orig, _ = _sandbox(tmp)
    # ніби процес убили посеред запису: файл не збігається ні зі станом, ні з резервом
    (data / "motion_body.bin").write_bytes(b"HALF-WRITTEN")
    check("це не вважається оновленням гри",
          patch.game_was_updated(data, game, _state(orig)) is False)
    check("резерв не чіпається", patch.refresh_backups(data, game) == [])
    check("оригінал на місці",
          (orig / "motion_body.bin").read_bytes() == b"ORIGINAL-motion")


def test_backups_refresh_on_real_update(tmp: Path):
    print("справжнє оновлення гри оновлює резерв")
    game, data, orig, lib = _sandbox(tmp)
    (lib / f"appmanifest_{patch.APPID}.acf").write_text(
        '"AppState"{"buildid" "2000" "installdir" "SGRE"}', encoding="utf-8")
    for stem in patch.STEMS:
        (data / f"{stem}_body.bin").write_bytes(b"NEWVERSION-" + stem.encode())
    check("оновлення розпізнано",
          patch.game_was_updated(data, game, _state(orig)) is True)
    check("оновлено всі частини", sorted(patch.refresh_backups(data, game)) == sorted(patch.STEMS))
    check("резерв тепер із нової версії",
          (orig / "motion_body.bin").read_bytes() == b"NEWVERSION-motion")
    check("стару копію збережено, а не затерто",
          any(p.read_bytes() == b"ORIGINAL-motion" for p in orig.glob("motion_body.bin.before*")))


def test_backups_untouched_without_proof(tmp: Path):
    print("немає доказу оновлення — нічого не чіпаємо")
    game, data, orig, lib = _sandbox(tmp)
    (lib / f"appmanifest_{patch.APPID}.acf").unlink()          # копія не зі Steam
    for stem in patch.STEMS:
        (data / f"{stem}_body.bin").write_bytes(b"UNKNOWN-" + stem.encode())
    check("відповідь «не знаю»",
          patch.game_was_updated(data, game, _state(orig)) is None)
    check("резерв не чіпається", patch.refresh_backups(data, game) == [])
    check("оригінал на місці",
          (orig / "motion_body.bin").read_bytes() == b"ORIGINAL-motion")


def test_buildid_parsing(tmp: Path):
    print("читання buildid із маніфесту Steam")
    game, _, _, lib = _sandbox(tmp, buildid="24796682")
    check("зчитано", patch.steam_buildid(game) == "24796682")
    (lib / f"appmanifest_{patch.APPID}.acf").unlink()
    check("немає маніфесту — None, а не виняток", patch.steam_buildid(game) is None)


# ---------------------------------------------------------------- запуск

def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="sgre_test_"))
    home = base / "home"
    home.mkdir()
    old_home = None
    if sys.platform != "win32":
        import os
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(home)
    try:
        test_xor()
        test_find_game(base / "find"); (base / "find").mkdir(exist_ok=True)
        test_steam_root(base, home)
        test_no_gui_on_linux()
        test_backups_survive_interrupted_install(base / "s1")
        test_backups_refresh_on_real_update(base / "s2")
        test_backups_untouched_without_proof(base / "s3")
        test_buildid_parsing(base / "s4")
    finally:
        if old_home is not None:
            import os
            os.environ["HOME"] = old_home
        shutil.rmtree(base, ignore_errors=True)

    print()
    if FAILED:
        print(f"ПАДІНЬ: {len(FAILED)}")
        for n in FAILED:
            print(f"  - {n}")
        return 1
    print("усе пройдено")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
