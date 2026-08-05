"""PyInstaller로 백엔드 단일 실행 파일 생성."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "backend-dist")
SPEC_WORK = os.path.join(ROOT, "build", "pyinstaller")
MAIN = os.path.join(ROOT, "backend", "main.py")
NAME = "buffcheck-backend"


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(SPEC_WORK, exist_ok=True)

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller 설치 중...", flush=True)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller"],
            cwd=ROOT,
        )

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        NAME,
        "--distpath",
        OUT_DIR,
        "--workpath",
        SPEC_WORK,
        "--specpath",
        SPEC_WORK,
        "--paths",
        os.path.join(ROOT, "backend"),
        "--hidden-import",
        "cv2",
        "--hidden-import",
        "numpy",
        "--hidden-import",
        "mss",
        "--hidden-import",
        "pytesseract",
        "--hidden-import",
        "app_paths",
        "--hidden-import",
        "buff_state",
        "--hidden-import",
        "color_mask",
        "--hidden-import",
        "config",
        "--hidden-import",
        "db",
        "--hidden-import",
        "icon_matcher",
        "--hidden-import",
        "image_io",
        "--hidden-import",
        "time_ocr",
        "--collect-all",
        "mss",
        MAIN,
    ]
    print(" ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=ROOT)

    exe = os.path.join(OUT_DIR, f"{NAME}.exe" if os.name == "nt" else NAME)
    if not os.path.isfile(exe):
        print(f"빌드 결과 없음: {exe}", file=sys.stderr)
        return 1
    print(f"backend ready: {exe}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
