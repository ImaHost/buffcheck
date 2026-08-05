"""캡처본 회귀 테스트 — production crop/OCR 사용."""
import os
import sys

import cv2

sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

from db import get_all_buffs
from icon_matcher import find_all_icons
from image_io import imread_unicode
from time_ocr import crop_time_for_match, read_time_debug

DEBUG = os.path.join(ROOT, "debug", "ocr")
os.makedirs(DEBUG, exist_ok=True)

SHOTS = [
    (
        "s0",
        r"C:\Users\user\.cursor\projects\d-buff-timer-app\assets\c__Users_user_AppData_Roaming_Cursor_User_workspaceStorage_0f4fb4004846893fbb33615a6a2054c2_images_image-d6adbf65-10d2-4aeb-9806-44896479a324.png",
        {"성역의 주인": 17},
    ),
    (
        "s1",
        r"C:\Users\user\.cursor\projects\d-buff-timer-app\assets\c__Users_user_AppData_Roaming_Cursor_User_workspaceStorage_0f4fb4004846893fbb33615a6a2054c2_images_image-71a7dcef-9235-422c-8f63-068a6f066170.png",
        {"성역의 주인": 2},
    ),
]


def extract_buff_panel(img):
    matches = find_all_icons(img, get_all_buffs(), "buff_icons")
    if not matches:
        return img[:, img.shape[1] // 2 :]
    min_x = max(0, min(m["x"] for m in matches) - 8)
    return img[:, min_x:]


def main():
    buffs = get_all_buffs()
    ok = 0
    total = 0

    for tag, path, expected in SHOTS:
        full = imread_unicode(path)
        panel = extract_buff_panel(full)
        cv2.imwrite(os.path.join(DEBUG, f"{tag}_prod_panel.png"), panel)
        print(f"\n=== {tag} {panel.shape} ===")
        matches = find_all_icons(panel, buffs, "buff_icons")
        results = {}
        for mi, m in enumerate(matches):
            crop, mode = crop_time_for_match(panel, m)
            if crop is not None:
                cv2.imwrite(os.path.join(DEBUG, f"{tag}_prod_m{mi}.png"), crop)
            dbg = read_time_debug(crop)
            print(f" {m['name']}: mode={mode} -> {dbg}")
            results[m["name"]] = dbg.get("remaining")

        for name, exp in expected.items():
            total += 1
            got = results.get(name)
            good = got is not None and abs(got - exp) <= 3
            print(f" CHECK {name}: expected~{exp} got={got} => {'OK' if good else 'FAIL'}")
            if good:
                ok += 1

    print(f"\nRESULT {ok}/{total}")
    return 0 if ok == total and total else 1


if __name__ == "__main__":
    raise SystemExit(main())
