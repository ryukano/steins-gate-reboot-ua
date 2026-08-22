"""
Читання/запис M2-архівів Re:Boot (<stem>_info.psb.m + <stem>_body.bin) із шифруванням.

    from m2archive import Archive
    a = Archive(data_dir, "font")            # читає (бере з _orig/, якщо є)
    raw = a.get("hiragino_pro_w6.otf.m")      # розшифрований вміст
    a.put("sgre_uk.ttf.m", ttf_bytes)         # додати/замінити (буде зашифровано як mzs)
    a.write(out_dir)                          # записати info+body в теку
    a.install()                               # бекап у _orig/ (якщо ще нема) + запис у data_dir

Правило seed для MDF/MZS: ім'я запису + expire_suffix, якщо ім'я ще не закінчується на ".m"; інакше саме ім'я.
"""
from __future__ import annotations
import shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# сусідні модулі лежать поруч: у робочому репозиторії це tools/, у публічному — patcher/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from m2crypt import unshell, enshell, DEFAULT_KEY  # noqa: E402
from psb import Psb  # noqa: E402


class Archive:
    def __init__(self, data_dir: Path, stem: str, key: str = DEFAULT_KEY, prefer_orig: bool = True):
        """prefer_orig=False читає те, що зараз лежить у грі, а не резервну копію.

        Для патчення завжди беремо незайманий оригінал із _orig. Але щоб дізнатися, чи Steam
        оновив гру, треба подивитися саме на поточний файл — інакше побачимо стару копію
        й ніколи не помітимо оновлення.
        """
        self.data_dir = Path(data_dir); self.stem = stem; self.key = key
        orig = self.data_dir / "_orig"
        src = orig if prefer_orig and (orig / f"{stem}_body.bin").exists() else self.data_dir
        self.info_name = f"{stem}_info.psb.m"
        self.info = Psb(unshell((src / self.info_name).read_bytes(), key, self.info_name))
        self.body = (src / f"{stem}_body.bin").read_bytes()
        self.suffix = (self.info.root.get("expire_suffix_list") or [""])[0]
        self.entries: dict[str, bytes] = {}      # name → сирий (розшифрований) вміст, лише змінені/додані
        self.shell: dict[str, bytes | None] = {}  # name → магія оболонки для нових записів

    def seed(self, name: str) -> str:
        return name if name.endswith(".m") else name + self.suffix

    def names(self) -> list[str]:
        return list(self.info.root["file_info"])

    def raw_blob(self, name: str) -> bytes:
        off, ln = self.info.root["file_info"][name]
        return self.body[off:off + ln]

    def get(self, name: str) -> bytes:
        if name in self.entries:
            return self.entries[name]
        blob = self.raw_blob(name)
        if blob[:4] in (b"mzs\0", b"mdf\0"):
            return unshell(blob, self.key, self.seed(name))
        return blob

    def put(self, name: str, data: bytes, shell: bytes | None = b"mzs\0"):
        self.entries[name] = data
        if name in self.info.root["file_info"]:
            self.shell[name] = self.raw_blob(name)[:4] if self.raw_blob(name)[:4] in (b"mzs\0", b"mdf\0") else None
        else:
            self.shell[name] = shell

    def build(self) -> tuple[bytes, bytes]:
        fi = self.info.root["file_info"]
        body = bytearray(); new_fi = {}
        for name in list(fi) + [n for n in self.entries if n not in fi]:
            if name in self.entries:
                sh = self.shell.get(name)
                blob = enshell(self.entries[name], sh, self.key, self.seed(name)) if sh else self.entries[name]
            else:
                blob = self.raw_blob(name)
            while len(body) % 16:
                body.append(0)
            new_fi[name] = [len(body), len(blob)]
            body += blob
        # оновити маніфест: імена записів — це ключі file_info, тож вони йдуть у trie імен,
        # але Psb.build() перебудовує trie сам, коли бачить нові ключі
        fi.clear(); fi.update(new_fi)
        info_raw = self.info.build()
        # body віддаємо як є: bytes() робив ще одну повну копію — для motion це зайвий гігабайт
        return enshell(info_raw, b"mzs\0", self.key, self.info_name), body

    def write(self, out_dir: Path):
        out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
        info, body = self.build()
        (out_dir / self.info_name).write_bytes(info)
        (out_dir / f"{self.stem}_body.bin").write_bytes(body)
        return out_dir

    def install(self):
        orig = self.data_dir / "_orig"; orig.mkdir(exist_ok=True)
        for f in (self.info_name, f"{self.stem}_body.bin"):
            if not (orig / f).exists():
                shutil.copy2(self.data_dir / f, orig / f)
        info, body = self.build()
        (self.data_dir / self.info_name).write_bytes(info)
        (self.data_dir / f"{self.stem}_body.bin").write_bytes(body)

    def restore(self):
        orig = self.data_dir / "_orig"
        for f in (self.info_name, f"{self.stem}_body.bin"):
            if (orig / f).exists():
                shutil.copy2(orig / f, self.data_dir / f)
