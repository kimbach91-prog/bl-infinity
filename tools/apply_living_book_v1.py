#!/usr/bin/env python3
"""Materialize the verified public source for the living book release."""
from __future__ import annotations

import base64
import hashlib
import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = 7
PAYLOAD_SHA256 = "53a2ff2b1d6210ff6867792c286e0d2caccad993aae4000441f0bd98c587430b"
FILES = {
    "index.html": "e78ee43a50f031129e99f6eebc8088b9e7624e089267dc8a3a1c3008b41ae797",
    "author.html": "61b5417d43b77557f6643ab5f2438e8212e45755f3f62081e5ec644c153a518f",
    "projects.html": "23d1a70da0207a527b3d75b0f25e850bb22dab04934c0f15216b9258a6a070f7",
    "sitemap.xml": "0dc323300116ac23ff3437a7e7a78576b895030f214876603e1299e6adf88034",
    "books/index.html": "3cc2a27c178d135d62e78343141f42ce00a9169790ef291377a7f4179be8c12e",
    "books/bieu-tuong-va-ban-chat/index.html": "f6e36862aa7f3b5533f6bcb68e507d6cd12d20799cffc55fa573457c31f84e1b",
    "books/bieu-tuong-va-ban-chat/book.json": "d4f8dd6dfad7092fea8740a77092f7c9f6a7a626d08e8f0aaaf1ae257a07a445",
    "books/bieu-tuong-va-ban-chat/chapters/00-loi-mo.md": "fb8cc0f4ae4e1bbc14f8f26a8f861252656c3bbb32f2279b8f052df07689e08f",
    "books/bieu-tuong-va-ban-chat/chapters/01-bieu-tuong-khong-phai-ban-chat.md": "ab22242fe805da754460fd8304dc37a1831b6b189870eefb03ab304e343cd813",
    "books/bieu-tuong-va-ban-chat/chapters/02-khi-bieu-tuong-tao-ra-hanh-dong.md": "cdc4747f42e6830ab2f5aedcd30b9297346eb476957ce37c6951a869f41cabcc",
    "books/bieu-tuong-va-ban-chat/chapters/03-co-the-ky-uc-nghi-thuc.md": "a6224f46918f132ffc0fddee1eb3023ec4892913950dcea9d5667bf42e0c13d8",
    "books/bieu-tuong-va-ban-chat/chapters/04-quyen-luc-cua-nguoi-dat-ten.md": "35f0193be3a46d79285ac54c05af37e38df9b5b09a5e5b246a455e7c3b4eb60a",
    "books/bieu-tuong-va-ban-chat/chapters/05-ai-va-bieu-tuong-khong-co-trai-nghiem.md": "b2ef6dc4bad40255d22201d336b67225be31502b28dd71ae4d372d9495d580bd",
    "books/bieu-tuong-va-ban-chat/chapters/06-hop-tac-giua-cac-dang-tri-tue.md": "f41fc0d948edd5338b16f80019ecb3782b8cdf9e9301eb391cede3efe5e149af",
    "books/bieu-tuong-va-ban-chat/chapters/07-hoc-cach-nhin-xuyen-bieu-tuong.md": "4e4b95c8b6f28647b34a8aefaf2cb717222d67a8c913755c4b419608e5690842",
}


def main() -> None:
    source = ROOT / "tools" / "payload"
    encoded = "".join(
        (source / f"living-book-v1.part{i:02d}").read_text(encoding="ascii").strip()
        for i in range(1, PARTS + 1)
    )
    raw = base64.b64decode(encoded, validate=True)
    if hashlib.sha256(raw).hexdigest() != PAYLOAD_SHA256:
        raise SystemExit("LIVING_BOOK_PAYLOAD_HASH_MISMATCH")

    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if set(archive.namelist()) != set(FILES):
            raise SystemExit("LIVING_BOOK_FILESET_MISMATCH")
        for rel, expected in FILES.items():
            data = archive.read(rel)
            if hashlib.sha256(data).hexdigest() != expected:
                raise SystemExit(f"LIVING_BOOK_FILE_HASH_MISMATCH: {rel}")
            target = ROOT / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    print(f"Applied living book release: {len(FILES)} verified source files")


if __name__ == "__main__":
    main()
