"""
M2 «wind» engine (Re:Boot): розшифровка/зашифровка MDF/MZS-оболонок з ключем.
Алгоритм = FreeMote PsbExtension.EncodeMdf: seed = MD5(key + filename) → MT19937 init_by_array(4×u32)
→ буфер keyLength (131) байт → XOR усіх байтів після 8-байтового заголовка.

    python m2crypt.py <file> [--key K] [--name NAME] [--len 131] [--out OUT]
"""
from __future__ import annotations
import argparse, hashlib, struct, sys
from pathlib import Path

DEFAULT_KEY = "Rk3nwA8ZYV0yV"   # знайдено в sgre_steam.exe поруч із script_info.psb.m


class MT19937:
    def __init__(self, seeds: list[int]):
        self.mt = [0] * 624
        self.idx = 625
        self._init_genrand(19650218)
        i, j = 1, 0
        n = len(seeds)
        for _ in range(max(624, n)):
            self.mt[i] = ((self.mt[i] ^ ((self.mt[i-1] ^ (self.mt[i-1] >> 30)) * 1664525)) + seeds[j] + j) & 0xffffffff
            i += 1; j += 1
            if i >= 624:
                self.mt[0] = self.mt[623]; i = 1
            if j >= n:
                j = 0
        for _ in range(623):
            self.mt[i] = ((self.mt[i] ^ ((self.mt[i-1] ^ (self.mt[i-1] >> 30)) * 1566083941)) - i) & 0xffffffff
            i += 1
            if i >= 624:
                self.mt[0] = self.mt[623]; i = 1
        self.mt[0] = 0x80000000
        self.idx = 624

    def _init_genrand(self, s):
        self.mt[0] = s & 0xffffffff
        for i in range(1, 624):
            self.mt[i] = (1812433253 * (self.mt[i-1] ^ (self.mt[i-1] >> 30)) + i) & 0xffffffff

    def u32(self) -> int:
        if self.idx >= 624:
            for k in range(624):
                y = (self.mt[k] & 0x80000000) | (self.mt[(k+1) % 624] & 0x7fffffff)
                self.mt[k] = self.mt[(k+397) % 624] ^ (y >> 1) ^ (0x9908b0df if y & 1 else 0)
            self.idx = 0
        y = self.mt[self.idx]; self.idx += 1
        y ^= y >> 11
        y ^= (y << 7) & 0x9d2c5680
        y ^= (y << 15) & 0xefc60000
        y ^= y >> 18
        return y & 0xffffffff


def keystream(full_key: str, key_len: int = 131) -> bytes:
    h = hashlib.md5(full_key.encode("utf-8")).digest()
    seeds = list(struct.unpack("<4I", h))
    g = MT19937(seeds)
    buf = b"".join(struct.pack("<I", g.u32()) for _ in range(key_len // 4 + 1))
    return buf[:key_len]


def xor_body(data: bytes, full_key: str, key_len: int = 131, keep_header: int = 8) -> bytes:
    ks = keystream(full_key, key_len)
    head, body = data[:keep_header], data[keep_header:]
    n = len(ks)
    out = bytearray(body)
    for i in range(len(out)):
        out[i] ^= ks[i % n]
    return head + bytes(out)


def unshell(data: bytes, key: str | None, name: str, key_len: int = 131) -> bytes:
    """mzs/mdf → сирий PSB (або інший вміст)."""
    magic = data[:4]
    if key:
        data = xor_body(data, key + name, key_len)
    size = struct.unpack("<I", data[4:8])[0]
    payload = data[8:]
    if magic == b"mzs\0":
        import zstandard as zstd
        return zstd.ZstdDecompressor().decompress(payload, max_output_size=size)
    if magic == b"mdf\0":
        import zlib
        return zlib.decompress(payload)
    raise ValueError(f"невідома оболонка {magic!r}")


def enshell(raw: bytes, magic: bytes, key: str | None, name: str, key_len: int = 131, level: int = 19) -> bytes:
    if magic == b"mzs\0":
        import zstandard as zstd
        payload = zstd.ZstdCompressor(level=level).compress(raw)
    elif magic == b"mdf\0":
        import zlib
        payload = zlib.compress(raw, 9)
    else:
        raise ValueError(magic)
    data = magic + struct.pack("<I", len(raw)) + payload
    if key:
        data = xor_body(data, key + name, key_len)
    return data


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--key", default=DEFAULT_KEY)
    ap.add_argument("--name", help="ім'я файлу для seed (типово — basename)")
    ap.add_argument("--len", type=int, default=131)
    ap.add_argument("--out")
    a = ap.parse_args()
    p = Path(a.file)
    raw = unshell(p.read_bytes(), a.key, a.name or p.name, a.len)
    print(f"{p.name}: {len(raw)} байт, початок: {raw[:16]!r}")
    if a.out:
        Path(a.out).write_bytes(raw)
