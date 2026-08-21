"""
Читач/записувач M2 PSB (v2/v3) — для маніфестів *_info.psb.m і сценарних PSB Re:Boot.

Читання → звичайні Python-структури: dict / list / UArr / int / PsbFloat / PsbDouble / str / PsbRes / None / bool.
Запис  → Psb.build(): імена (trie) копіюються з оригіналу (ключі не змінюємо), рядки — нова відсортована
таблиця, entries — серіалізуються заново. Round-trip на оригіналі дає побайтово той самий файл.

    python psb.py <file.psb> [--json out.json]      — дамп у JSON
    python psb.py <file.psb> --roundtrip            — перевірка: parse → build == original
"""
from __future__ import annotations
import json, struct, sys, zlib
from pathlib import Path


class PsbFloat(float):
    """32-бітний float (тип 0x1E / 0x1D)"""


class PsbDouble(float):
    """64-бітний double (0x1F)"""


class UArr(list):
    """uint-масив PSB (тип 0x0D–0x14) — на відміну від колекції 0x20."""


class PsbRes:
    __slots__ = ("index", "extra")

    def __init__(self, index: int, extra: bool = False):
        self.index, self.extra = index, extra

    def __repr__(self):
        return f"<{'xres' if self.extra else 'res'} {self.index}>"


def _uint(b: bytes) -> int:
    return int.from_bytes(b, "little") if b else 0


def _size_signed(v: int) -> int:
    """мінімальна к-ть байтів для знакового little-endian (як у файлах M2): 200→2, -1→1, 0→0"""
    if v == 0:
        return 0
    for n in range(1, 9):
        lo, hi = -(1 << (8 * n - 1)), (1 << (8 * n - 1)) - 1
        if lo <= v <= hi:
            return n
    raise ValueError(v)


def _size_unsigned(v: int) -> int:
    if v == 0:
        return 0
    return (v.bit_length() + 7) // 8


def _arr_bytes(vals: list[int]) -> bytes:
    n = len(vals)
    cn = max(1, _size_unsigned(n))
    el = max(1, max((_size_unsigned(v) for v in vals), default=1))   # GetSize(0)=1; порожній масив теж має el=1
    out = bytearray([0x0D + cn - 1]) + n.to_bytes(cn, "little") + bytes([0x0C + el])
    for v in vals:
        if el:
            out += v.to_bytes(el, "little")
    return bytes(out)


def build_names_trie(names: list[str]) -> tuple[list[int], list[int], list[int]]:
    """Double-array trie як у пакувальника M2 (перевірено побайтово на font/config/scenario/resg*):
    root base = 1; далі DFS у порядку байтів, для кожного вузла база = найменша b0>=1, за якої всі
    слоти b0+byte вільні. Термінал (байт 0): charset[term] = індекс імені. tree[id] = батько.
    Повертає (charset, tree, name_indexes)."""
    names = list(names)
    children: list[dict[int, int]] = [{}]
    parent: list[int] = [0]
    term_of: list[int] = []
    for nm in names:
        cur = 0
        for b in nm.encode("utf-8") + b"\0":
            nxt = children[cur].get(b)
            if nxt is None:
                nxt = len(children); children.append({}); parent.append(cur); children[cur][b] = nxt
            cur = nxt
        term_of.append(cur)
    ids = [-1] * len(children); ids[0] = 0
    base = [0] * len(children)
    used = {0}

    def place(n: int, b0: int):
        base[n] = b0
        for b, c in children[n].items():
            ids[c] = b0 + b; used.add(b0 + b)

    place(0, 1)
    stack = [children[0][b] for b in sorted(children[0], reverse=True)]
    while stack:
        n = stack.pop()
        ch = children[n]
        if ch:
            bs = sorted(ch)
            b0 = 1
            while any((b0 + b) in used for b in bs):
                b0 += 1
            place(n, b0)
            stack.extend(ch[b] for b in sorted(ch, reverse=True))
    size = max(used) + 1
    charset = [0] * size; tree = [0] * size
    for n in range(len(children)):
        tree[ids[n]] = ids[parent[n]]
        charset[ids[n]] = base[n]
    for i, t in enumerate(term_of):
        charset[ids[t]] = i
    tree[0] = 0
    return charset, tree, [ids[t] for t in term_of]


class Psb:
    def __init__(self, data: bytes):
        self.d = data
        if data[:4] != b"PSB\0":
            raise ValueError("not a PSB")
        self.version, self.flags = struct.unpack_from("<HH", data, 4)
        (self.hdr_len, self.off_names, self.off_strings, self.off_strings_data, self.off_chunk_offsets,
         self.off_chunk_lengths, self.off_chunk_data, self.off_entries) = struct.unpack_from("<8I", data, 8)
        self.checksum = struct.unpack_from("<I", data, 40)[0] if self.version >= 3 else None
        if self.version >= 4:
            (self.off_extra_offsets, self.off_extra_lengths, self.off_extra_data) = struct.unpack_from("<3I", data, 44)
        self._names_end = self._load_names()
        self.string_offsets, _ = self._array(self.off_strings)
        self.chunk_offsets, _ = self._array(self.off_chunk_offsets)
        self.chunk_lengths, _ = self._array(self.off_chunk_lengths)
        if self.version >= 4:
            self.extra_offsets, _ = self._array(self.off_extra_offsets)
            self.extra_lengths, _ = self._array(self.off_extra_lengths)
        else:
            self.extra_offsets, self.extra_lengths = UArr(), UArr()
        self.root, _ = self._value(self.off_entries)

    # --- primitives
    def _array(self, p: int) -> tuple[UArr, int]:
        t = self.d[p]; p += 1
        if not 0x0D <= t <= 0x14:
            raise ValueError(f"array type 0x{t:02x} @ {p-1}")
        n = t - 0x0D + 1
        count = _uint(self.d[p:p+n]); p += n
        el = self.d[p] - 0x0C; p += 1
        vals = UArr(_uint(self.d[p + i*el: p + (i+1)*el]) for i in range(count))
        return vals, p + count * el

    def _load_names(self) -> int:
        p = self.off_names
        charset, p = self._array(p)
        names_data, p = self._array(p)
        name_idx, p = self._array(p)
        self.names = []
        for idx in name_idx:
            out = []
            chr_ = names_data[idx]
            while chr_ != 0:
                code = names_data[chr_]
                d = charset[code]
                out.append(chr_ - d)
                chr_ = code
            self.names.append(bytes(reversed(out)).decode("utf-8", "replace"))
        self.name_index = {n: i for i, n in enumerate(self.names)}
        return p

    def set_names(self, names: list[str]):
        """Перебудувати таблицю імен (trie) — після додавання нових ключів у словники."""
        names = sorted(set(names), key=lambda x: x.encode("utf-8"))
        charset, tree, idx = build_names_trie(names)
        self._names_bytes_override = _arr_bytes(charset) + _arr_bytes(tree) + _arr_bytes(idx)
        self.names = names
        self.name_index = {n: i for i, n in enumerate(names)}

    def collect_keys(self, v=..., acc: set | None = None) -> set[str]:
        """Усі ключі словників у дереві (щоб викликати set_names перед build, якщо є нові)."""
        acc = set() if acc is None else acc
        v = self.root if v is ... else v
        if isinstance(v, dict):
            for k, x in v.items():
                acc.add(k); self.collect_keys(x, acc)
        elif isinstance(v, list) and not isinstance(v, UArr):
            for x in v:
                self.collect_keys(x, acc)
        return acc

    def string(self, i: int) -> str:
        s = self.off_strings_data + self.string_offsets[i]
        e = self.d.index(b"\0", s)
        return self.d[s:e].decode("utf-8", "replace")

    def chunk(self, i: int) -> bytes:
        s = self.off_chunk_data + self.chunk_offsets[i]
        return self.d[s:s + self.chunk_lengths[i]]

    def extra(self, i: int) -> bytes:
        new = getattr(self, "_extra_new", {})
        if i in new:
            return new[i]
        s = self.off_extra_data + self.extra_offsets[i]
        return self.d[s:s + self.extra_lengths[i]]

    def add_extra(self, data: bytes) -> "PsbRes":
        """Додати новий extra-chunk (v4); повертає PsbRes(extra=True) для вставки в дерево."""
        if not hasattr(self, "_extra_new"):
            self._extra_new = {}
        idx = len(self.extra_offsets) + len(self._extra_new)
        self._extra_new[idx] = data
        return PsbRes(idx, True)

    def _value(self, p: int):
        t = self.d[p]; p += 1
        if t == 0x00: return None, p
        if t == 0x01: return None, p
        if t == 0x02: return False, p
        if t == 0x03: return True, p
        if t == 0x04: return 0, p
        if 0x05 <= t <= 0x0C:
            n = t - 0x04
            return int.from_bytes(self.d[p:p+n], "little", signed=True), p + n
        if 0x0D <= t <= 0x14:
            return self._array(p - 1)
        if 0x15 <= t <= 0x18:
            n = t - 0x14
            return self.string(_uint(self.d[p:p+n])), p + n
        if 0x19 <= t <= 0x1C:
            n = t - 0x18
            return PsbRes(_uint(self.d[p:p+n])), p + n
        if t == 0x1D: return PsbFloat(0.0), p
        if t == 0x1E: return PsbFloat(struct.unpack_from("<f", self.d, p)[0]), p + 4
        if t == 0x1F: return PsbDouble(struct.unpack_from("<d", self.d, p)[0]), p + 8
        if t == 0x20:
            offs, p2 = self._array(p)
            return [self._value(p2 + o)[0] for o in offs], p2
        if t == 0x21:
            names, p2 = self._array(p)
            offs, p3 = self._array(p2)
            return {self.names[ni]: self._value(p3 + o)[0] for ni, o in zip(names, offs)}, p3
        if 0x22 <= t <= 0x25:
            n = t - 0x21
            return PsbRes(_uint(self.d[p:p+n]), True), p + n
        raise ValueError(f"unknown type 0x{t:02x} @ {p-1}")

    # --- writer
    def build(self, root=None, chunks: "dict[int, bytes] | None" = None) -> bytes:
        """Серіалізує (root або self.root) у PSB тієї ж версії. Імена (trie) беруться з оригіналу або
        перебудовуються, якщо з'явилися нові ключі. chunks = {index: bytes} — підмінити chunk-дані (текстури)."""
        root = self.root if root is None else root
        strs: set[str] = set()

        def walk(v):
            if isinstance(v, str):
                strs.add(v)
            elif isinstance(v, dict):
                for x in v.values():
                    walk(x)
            elif isinstance(v, list) and not isinstance(v, UArr):
                for x in v:
                    walk(x)
        walk(root)
        table = sorted(strs, key=lambda s: s.encode("utf-8"))
        sidx = {s: i for i, s in enumerate(table)}
        sdata = bytearray(); soffs = []
        for s in table:
            soffs.append(len(sdata)); sdata += s.encode("utf-8") + b"\0"
        keys = self.collect_keys(root)
        if not keys <= set(self.name_index):
            self.set_names(list(keys))
        ent = self._pack(root, sidx)
        names_bytes = getattr(self, "_names_bytes_override", None) or self.d[self.off_names:self._names_end]
        hdr_len = 0x38 if self.version >= 4 else (0x2c if self.version >= 3 else 0x28)

        def pad_to(buf: bytearray, align: int):
            while len(buf) % align:
                buf.append(0)

        out = bytearray(b"\0" * hdr_len)
        off_names = len(out); out += names_bytes
        off_entries = len(out); out += ent
        off_strings = len(out); out += _arr_bytes(soffs)
        off_strings_data = len(out); out += sdata
        off_x_offs = off_x_lens = off_x_data = 0
        if self.version >= 4:
            # extra chunks: копіюємо дані як є (офсети перераховуємо)
            xs = [self.extra(i) for i in range(len(self.extra_offsets) + len(getattr(self, "_extra_new", {})))]
            xoffs, xdata, pos = [], bytearray(), 0
            for c in xs:                      # кожен extra-chunk вирівняний на 32
                while pos % 32:
                    xdata.append(0); pos += 1
                xoffs.append(pos); xdata += c; pos += len(c)
            off_x_offs = len(out); out += _arr_bytes(xoffs)
            off_x_lens = len(out); out += _arr_bytes([len(c) for c in xs])
            if xs:
                pad_to(out, 32)
            off_x_data = len(out); out += xdata
        # chunks
        if chunks:
            cs = [chunks.get(i, self.chunk(i)) for i in range(len(self.chunk_offsets))]
            coffs, cdata, pos = [], bytearray(), 0
            for c in cs:                      # кожен chunk вирівняний на 32
                while pos % 32:
                    cdata.append(0); pos += 1
                coffs.append(pos); cdata += c; pos += len(c)
            clens = [len(c) for c in cs]
        else:
            coffs, clens = list(self.chunk_offsets), list(self.chunk_lengths)
            cdata = self.d[self.off_chunk_data:] if self.chunk_offsets else b""
        off_chunk_offsets = len(out); out += _arr_bytes(coffs)
        off_chunk_lengths = len(out); out += _arr_bytes(clens)
        if coffs:
            pad_to(out, 32)
        off_chunk_data = len(out); out += cdata
        offs = struct.pack("<8I", hdr_len, off_names, off_strings, off_strings_data, off_chunk_offsets,
                           off_chunk_lengths, off_chunk_data, off_entries)
        hdr = bytearray(b"PSB\0") + struct.pack("<HH", self.version, self.flags) + offs
        if self.version >= 3:
            xo = struct.pack("<3I", off_x_offs, off_x_lens, off_x_data)
            hdr += struct.pack("<I", zlib.adler32(offs + (xo if self.version >= 4 else b"")) & 0xffffffff)
        if self.version >= 4:
            hdr += xo
        assert len(hdr) == hdr_len, (len(hdr), hdr_len)
        out[:hdr_len] = hdr
        return bytes(out)

    def _pack(self, v, sidx: dict) -> bytes:
        if v is None:
            return b"\x01"
        if v is True:
            return b"\x03"
        if v is False:
            return b"\x02"
        if isinstance(v, PsbDouble):
            return b"\x1f" + struct.pack("<d", v)
        if isinstance(v, float):  # PsbFloat або звичайний float
            return b"\x1d" if v == 0.0 else b"\x1e" + struct.pack("<f", v)
        if isinstance(v, int):
            n = _size_signed(v)
            return b"\x04" if n == 0 else bytes([0x04 + n]) + v.to_bytes(n, "little", signed=True)
        if isinstance(v, str):
            i = sidx[v]; n = max(1, _size_unsigned(i))
            return bytes([0x14 + n]) + i.to_bytes(n, "little")
        if isinstance(v, PsbRes):
            n = max(1, _size_unsigned(v.index))
            return bytes([(0x21 if v.extra else 0x18) + n]) + v.index.to_bytes(n, "little")
        if isinstance(v, UArr):
            return _arr_bytes(v)
        if isinstance(v, list):
            offs, blob = self._pack_members(v, sidx)
            return b"\x20" + _arr_bytes(offs) + blob
        if isinstance(v, dict):
            items = sorted(((self.name_index[k], x) for k, x in v.items()), key=lambda t: t[0])
            offs, blob = self._pack_members([x for _, x in items], sidx)
            return b"\x21" + _arr_bytes([i for i, _ in items]) + _arr_bytes(offs) + blob
        raise TypeError(type(v))

    def _pack_members(self, values, sidx: dict) -> tuple[list[int], bytes]:
        """Члени колекції; однакові за байтами значення діляться одним offset — як у пакувальника M2."""
        blobs, offs, pos, seen = [], [], 0, {}
        for x in values:
            b = self._pack(x, sidx)
            if b in seen:                      # однакові значення (і цілі під-об'єкти) діляться одним offset
                offs.append(seen[b])
                continue
            seen[b] = pos
            blobs.append(b); offs.append(pos); pos += len(b)
        return offs, b"".join(blobs)


def to_json(v):
    if isinstance(v, PsbRes):
        return repr(v)
    if isinstance(v, dict):
        return {k: to_json(x) for k, x in v.items()}
    if isinstance(v, list):
        return [to_json(x) for x in v]
    return v


if __name__ == "__main__":
    p = Path(sys.argv[1])
    raw = p.read_bytes()
    psb = Psb(raw)
    print(f"PSB v{psb.version}: names={len(psb.names)} strings={len(psb.string_offsets)} chunks={len(psb.chunk_offsets)}")
    if "--roundtrip" in sys.argv:
        out = psb.build()
        same = out == raw
        print("round-trip:", "OK (побайтово)" if same else f"РІЗНИЦЯ: {len(out)} vs {len(raw)}")
        if not same:
            for i, (a, b) in enumerate(zip(out, raw)):
                if a != b:
                    print(f"  перша відмінність @ 0x{i:x}: new {out[i:i+16].hex()} / orig {raw[i:i+16].hex()}")
                    break
        sys.exit(0 if same else 1)
    j = to_json(psb.root)
    if len(sys.argv) > 3 and sys.argv[2] == "--json":
        Path(sys.argv[3]).write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
        print("→", sys.argv[3])
    else:
        print(json.dumps(j, ensure_ascii=False, indent=1)[:3000])
