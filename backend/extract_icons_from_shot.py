"""왼쪽 아이콘 열을 수동 보정 크롭으로 저장."""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

from image_io import imread_unicode

SRC = r"C:\Users\user\.cursor\projects\d-buff-timer-app\assets\c__Users_user_AppData_Roaming_Cursor_User_workspaceStorage_0f4fb4004846893fbb33615a6a2054c2_images_image-ec731efe-be1f-4f2c-91d6-5ff86d14f542.png"
OUT = os.path.join(ROOT, "buff_icons")
DEBUG = os.path.join(ROOT, "debug", "ocr")

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
    img = imread_unicode(SRC)
    h, w = img.shape[:2]
    print("shape", h, w)

    # 왼쪽 열에서 행 에너지(채도)로 아이콘 y 구간 검출
    left = img[:, 0:34]
    hsv = cv2.cvtColor(left, cv2.COLOR_BGR2HSV)
    # 아이콘은 채도/구조가 큼. 글자(흰)는 채도 낮음 → 채도+엣지
    sat = hsv[:, :, 1].astype(np.float32)
    gray = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150).astype(np.float32)
    energy = sat.mean(axis=1) + edges.mean(axis=1) * 0.5

    # 로컬 맥스: 아이콘 중심
    # 먼저 이진화
    thr = np.percentile(energy, 55)
    mask = energy > thr

    # 연속 True 구간
    segs = []
    i = 0
    while i < h:
        if mask[i]:
            j = i
            while j < h and mask[j]:
                j += 1
            if j - i >= 8:
                segs.append((i, j))
            i = j
        else:
            i += 1
    print("segs", segs)

    # 글자 줄과 아이콘이 섞일 수 있음 → 왼쪽 12~30px 폭에서 std가 큰 구간만
    refined = []
    for y1, y2 in segs:
        best = None
        for yy in range(y1, max(y1 + 1, y2 - 14)):
            for xx in range(0, 20):
                patch = gray[yy : yy + 16, xx : xx + 16]
                if patch.shape != (16, 16):
                    continue
                # 아이콘: 중간 이상 std, 너무 균일하지 않음
                st = float(patch.std())
                # 오른쪽(글자)보다 왼쪽 패치가 색이 다양
                color_std = float(left[yy : yy + 16, xx : xx + 16].reshape(-1, 3).std())
                score = st + color_std * 0.3
                if best is None or score > best[0]:
                    best = (score, xx, yy)
        if best and best[0] > 25:
            refined.append(best)
    # y NMS
    refined.sort(key=lambda t: t[2])
    picked = []
    for item in refined:
        if picked and abs(item[2] - picked[-1][2]) < 12:
            if item[0] > picked[-1][0]:
                picked[-1] = item
            continue
        picked.append(item)
    print("picked", picked)

    # 8개 안 되면 등간격으로 강제 (실측: 리스트 행 간격 ~24)
    if len(picked) < 8:
        # 첫/마지막 아이콘 y 추정
        if picked:
            y0 = picked[0][2]
            x0 = picked[0][1]
        else:
            y0, x0 = 2, 14
        gap = 24
        # 이미지 높이에 맞게 gap 조정
        gap = max(18, min(26, (h - y0 - 16) // 7))
        picked = []
        for i in range(8):
            yy = y0 + i * gap
            if yy + 16 > h:
                yy = h - 16
            # x는 고정 탐색
            best = None
            for xx in range(10, 22):
                patch = gray[yy : yy + 16, xx : xx + 16]
                if patch.shape != (16, 16):
                    continue
                st = float(patch.std())
                if best is None or st > best[0]:
                    best = (st, xx, yy)
            picked.append(best)
        print("forced", picked, "gap", gap)

    # 정확히 8개
    if len(picked) > 8:
        # 점수 상위? 아니면 등간격 샘플
        picked = picked[:8]

    # 최종: x를 통일 (중앙값)
    xs = [p[1] for p in picked]
    x_med = int(np.median(xs))
    print("x_med", x_med)

    side = 16
    vis = img.copy()
    sheet = []
    for i, name in enumerate(NAMES):
        _, x, y = picked[i]
        x = x_med  # 정렬
        # 미세 조정: 해당 y에서 최적 x
        best = (0, x, y)
        for xx in range(max(0, x_med - 4), min(22, x_med + 5)):
            patch = gray[y : y + side, xx : xx + side]
            if patch.shape != (side, side):
                continue
            st = float(patch.std())
            if st > best[0]:
                best = (st, xx, y)
        _, x, y = best
        crop = img[y : y + side, x : x + side].copy()
        save_png(os.path.join(OUT, f"{name}.png"), crop)
        cv2.rectangle(vis, (x, y), (x + side, y + side), (0, 255, 0), 1)
        sheet.append(cv2.resize(crop, (64, 64), interpolation=cv2.INTER_NEAREST))
        print(f"saved {name} @({x},{y})")

    save_png(os.path.join(DEBUG, "extract_final_vis.png"), vis)
    save_png(os.path.join(DEBUG, "icons_sheet.png"), np.hstack(sheet))
    print("done")


if __name__ == "__main__":
    main()
