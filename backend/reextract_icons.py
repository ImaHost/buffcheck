"""최신 스크린샷에서 버프 리스트 아이콘만 깨끗하게 추출."""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

from image_io import imread_unicode

SRC = r"C:\Users\user\.cursor\projects\d-buff-timer-app\assets\c__Users_user_AppData_Roaming_Cursor_User_workspaceStorage_0f4fb4004846893fbb33615a6a2054c2_images_image-f380cd0f-8186-44b7-9514-6282192193ca.png"
OUT = os.path.join(ROOT, "buff_icons")
DEBUG = os.path.join(ROOT, "debug", "ocr")
os.makedirs(DEBUG, exist_ok=True)

NAMES = [
    "투안의 노래",
    "성역의 주인",
    "공격력 증가",
    "전장의 서곡",
    "행진곡",
    "고결한 서약",
    "예리",
    "햄 아드레날린",
]


def save_png(path, img):
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError(path)
    buf.tofile(path)


def main():
    full = imread_unicode(SRC)
    # 오른쪽 버프 리스트만 (오버레이 제외)
    img = full[:, int(full.shape[1] * 0.42) :]
    save_png(os.path.join(DEBUG, "reextract_panel.png"), img)
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 왼쪽 아이콘 열에서 어두운 테두리 정사각 탐색
    candidates = []
    for side in (14, 15, 16):
        for x in range(0, min(28, w - side)):
            for y in range(0, h - side):
                g = gray[y : y + side, x : x + side].astype(np.float32)
                border = np.concatenate([g[0, :], g[-1, :], g[1:-1, 0], g[1:-1, -1]])
                inner = g[2:-2, 2:-2]
                if inner.size == 0:
                    continue
                if border.mean() > inner.mean() + 8:
                    continue  # 테두리가 더 밝으면 아이콘 아님
                patch = img[y : y + side, x : x + side]
                hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV).astype(np.float32)
                score = (255 - border.mean()) * 0.4 + inner.std() * 0.35 + hsv[:, :, 1].mean() * 0.25
                candidates.append((score, x, y, side))

    candidates.sort(reverse=True)
    picked = []
    for sc, x, y, side in candidates:
        if any(abs(y - py) < 12 and abs(x - px) < 8 for _, px, py, _ in picked):
            continue
        picked.append((sc, x, y, side))
        if len(picked) >= 8:
            break
    picked.sort(key=lambda t: t[2])
    print("picked", [(round(s, 1), x, y, side) for s, x, y, side in picked])

    if len(picked) < 8:
        # fallback: 등간격
        print("fallback equal")
        side = 15
        x = 4
        gap = max(18, (h - 8) // 8)
        y0 = 4
        picked = [(0, x, y0 + i * gap, side) for i in range(8)]

    # x/side 통일
    side = int(np.median([p[3] for p in picked]))
    x = int(np.median([p[1] for p in picked]))
    ys = [p[2] for p in picked]
    # y를 등간격으로 보정
    if len(ys) >= 2:
        gap = int(round(np.median(np.diff(ys))))
        y0 = ys[0]
        ys = [y0 + i * gap for i in range(8)]

    vis = img.copy()
    sheet = []
    for i, name in enumerate(NAMES):
        y = ys[i]
        # 주변에서 최적 미세조정
        best = None
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                xx, yy = x + dx, y + dy
                if xx < 0 or yy < 0 or xx + side > w or yy + side > h:
                    continue
                patch = img[yy : yy + side, xx : xx + side]
                g = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY).astype(np.float32)
                border = np.concatenate([g[0, :], g[-1, :], g[:, 0], g[:, -1]])
                inner = g[2:-2, 2:-2]
                hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV).astype(np.float32)
                sc = (255 - border.mean()) * 0.45 + inner.std() * 0.35 + hsv[:, :, 1].mean() * 0.2
                if best is None or sc > best[0]:
                    best = (sc, xx, yy, patch.copy())
        _, xx, yy, crop = best
        save_png(os.path.join(OUT, f"{name}.png"), crop)
        cv2.rectangle(vis, (xx, yy), (xx + side, yy + side), (0, 255, 0), 1)
        sheet.append(cv2.resize(crop, (96, 96), interpolation=cv2.INTER_NEAREST))
        print(f"saved {name} @({xx},{yy}) {side}")

    save_png(os.path.join(DEBUG, "reextract_vis.png"), vis)
    save_png(os.path.join(DEBUG, "reextract_sheet.png"), np.hstack(sheet))


if __name__ == "__main__":
    main()
