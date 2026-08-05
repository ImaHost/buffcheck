"""buff_icons/ 스캔 → icons.db 생성/갱신."""
import os
import sys

import cv2

# backend 디렉터리를 path에 추가
sys.path.insert(0, os.path.dirname(__file__))

from db import init_db, upsert_buff
from image_io import imread_unicode

ICON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "buff_icons"))


def main():
    init_db()
    if not os.path.isdir(ICON_DIR):
        os.makedirs(ICON_DIR, exist_ok=True)
        print(f"아이콘 폴더가 없어 생성했습니다: {ICON_DIR}")
        print("PNG 아이콘을 넣은 뒤 다시 실행하세요.")
        return

    count = 0
    for fname in os.listdir(ICON_DIR):
        if not fname.lower().endswith(".png"):
            continue
        name = os.path.splitext(fname)[0]
        path = os.path.join(ICON_DIR, fname)
        img = imread_unicode(path, cv2.IMREAD_COLOR)
        if img is None:
            print(f"읽기 실패: {fname}")
            continue
        h, w = img.shape[:2]
        upsert_buff(name, fname, w, h)
        count += 1
        print(f"  + {name} ({w}x{h})")

    print(f"{count}개 아이콘 등록 완료 → icons.db")


if __name__ == "__main__":
    main()
