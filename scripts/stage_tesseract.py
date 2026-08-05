"""배포용 Tesseract 바이너리를 vendor/tesseract 로 복사."""
from __future__ import annotations

import glob
import os
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DST = os.path.join(ROOT, "vendor", "tesseract")

CANDIDATES = [
    os.environ.get("TESSERACT_HOME"),
    r"C:\Program Files\Tesseract-OCR",
    r"C:\Program Files (x86)\Tesseract-OCR",
]


def main() -> int:
    os.makedirs(DST, exist_ok=True)
    src = None
    for candidate in CANDIDATES:
        if not candidate:
            continue
        exe = os.path.join(candidate, "tesseract.exe")
        if os.path.isfile(exe):
            src = candidate
            break

    if not src:
        print(
            "Tesseract 설치 경로를 찾지 못했습니다. "
            "시스템 PATH의 tesseract를 쓰거나 TESSERACT_HOME을 설정하세요.",
            file=sys.stderr,
        )
        # electron-builder 가 빈 폴더도 허용하도록 keep
        keep = os.path.join(DST, ".gitkeep")
        if not os.path.isfile(keep):
            open(keep, "w", encoding="utf-8").close()
        return 0

    print(f"staging tesseract from {src}", flush=True)
    shutil.copy2(os.path.join(src, "tesseract.exe"), os.path.join(DST, "tesseract.exe"))
    for pattern in ("*.dll",):
        for path in glob.glob(os.path.join(src, pattern)):
            shutil.copy2(path, os.path.join(DST, os.path.basename(path)))
    print(f"staged -> {DST}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
