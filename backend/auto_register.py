"""버프 패널 캡처에서 왼쪽 아이콘을 찾아 자동 등록."""
from __future__ import annotations

import os
import re
import time
from typing import List, Tuple

import cv2
import numpy as np
import pytesseract

from app_paths import project_root
from config import ICON_DIR, MATCH_THRESHOLD
from db import get_all_buffs, init_db, upsert_buff
from image_io import imread_unicode


def _save_png(path: str, img: np.ndarray) -> None:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError(f"encode failed: {path}")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    buf.tofile(path)


def _sanitize_name(raw: str, fallback: str) -> str:
    text = (raw or "").strip()
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"[\\/:*?\"<>|]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    # 시간 조각 제거
    text = re.sub(r"\d+\s*분", "", text)
    text = re.sub(r"\d+\s*초", "", text)
    text = re.sub(r"\d+", "", text).strip()
    if len(text) < 2:
        return fallback
    return text[:40]


def _ocr_row_name(panel: np.ndarray, y: int, icon_right: int, icon_h: int) -> str:
    ph, pw = panel.shape[:2]
    y1 = max(0, y - 2)
    y2 = min(ph, y + icon_h + 4)
    x1 = min(pw - 1, icon_right + 6)
    x2 = min(pw, max(x1 + 40, pw - 90))
    strip = panel[y1:y2, x1:x2]
    if strip.size == 0:
        return ""
    gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
    _, thr = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
    big = cv2.resize(thr, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    try:
        raw = pytesseract.image_to_string(big, lang="kor+eng", config="--oem 3 --psm 7")
    except Exception:
        try:
            raw = pytesseract.image_to_string(big, config="--oem 3 --psm 7")
        except Exception:
            return ""
    return (raw or "").strip()


def _find_icon_boxes(panel: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """왼쪽 열에서 아이콘 후보 박스 (x,y,w,h)."""
    h, w = panel.shape[:2]
    left_w = min(42, max(24, w // 8))
    left = panel[:, 0:left_w]
    hsv = cv2.cvtColor(left, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1].astype(np.float32)
    gray = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150).astype(np.float32)
    energy = sat.mean(axis=1) + edges.mean(axis=1) * 0.5
    thr = float(np.percentile(energy, 55))
    mask = energy > thr

    segs = []
    i = 0
    while i < h:
        if mask[i]:
            j = i
            while j < h and mask[j]:
                j += 1
            if 10 <= (j - i) <= 36:
                segs.append((i, j))
            i = j
        else:
            i += 1

    side = 16
    candidates = []
    for y1, y2 in segs:
        best = None
        for yy in range(y1, max(y1 + 1, y2 - side + 1)):
            for xx in range(0, max(1, left_w - side)):
                patch = gray[yy : yy + side, xx : xx + side]
                if patch.shape != (side, side):
                    continue
                st = float(patch.std())
                color_std = float(
                    left[yy : yy + side, xx : xx + side].reshape(-1, 3).std()
                )
                score = st + color_std * 0.3
                if best is None or score > best[0]:
                    best = (score, xx, yy)
        if best and best[0] > 18:
            candidates.append(best)

    candidates.sort(key=lambda t: t[2])
    picked = []
    for item in candidates:
        if picked and abs(item[2] - picked[-1][2]) < 12:
            if item[0] > picked[-1][0]:
                picked[-1] = item
            continue
        picked.append(item)

    if not picked:
        # 등간격 폴백
        gap = 24
        y0 = 2
        for i in range(min(12, max(1, (h - 8) // gap))):
            yy = y0 + i * gap
            if yy + side > h:
                break
            picked.append((30.0, 12, yy))

    # x 중앙값으로 정렬
    xs = [p[1] for p in picked]
    x_med = int(np.median(xs)) if xs else 12
    boxes = []
    for _, _, yy in picked:
        xx = x_med
        best = (0.0, xx, yy)
        for tx in range(max(0, x_med - 4), min(left_w - side, x_med + 5)):
            patch = gray[yy : yy + side, tx : tx + side]
            if patch.shape != (side, side):
                continue
            st = float(patch.std())
            if st > best[0]:
                best = (st, tx, yy)
        _, xx, yy = best
        if yy + side <= h and xx + side <= w:
            boxes.append((xx, yy, side, side))
    return boxes


def _best_existing_match(crop: np.ndarray, buff_db, icon_dir: str):
    best_name = None
    best_score = 0.0
    if crop is None or crop.size == 0:
        return None, 0.0
    crop_gray = (
        cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
    )
    for buff in buff_db:
        icon_path = os.path.join(icon_dir, buff["icon_path"])
        if not os.path.isfile(icon_path):
            continue
        tmpl = imread_unicode(icon_path, cv2.IMREAD_GRAYSCALE)
        if tmpl is None or tmpl.size == 0:
            continue
        th, tw = tmpl.shape[:2]
        try:
            resized = cv2.resize(crop_gray, (tw, th), interpolation=cv2.INTER_AREA)
            direct = cv2.matchTemplate(resized, tmpl, cv2.TM_CCOEFF_NORMED)
            score = float(direct.max())
        except Exception:
            continue
        if score > best_score:
            best_score = score
            best_name = buff["name"]
    return best_name, best_score


def auto_register_from_panel(panel_img: np.ndarray) -> dict:
    """
    패널 이미지에서 아이콘 자동 등록.
    이미 높은 점수로 매칭되면 건너뛰고, 신규만 저장.
    """
    root = project_root()
    icon_dir = os.path.join(root, ICON_DIR)
    os.makedirs(icon_dir, exist_ok=True)
    init_db()
    buff_db = get_all_buffs()

    boxes = _find_icon_boxes(panel_img)
    added = []
    skipped = []
    stamp = time.strftime("%H%M%S")

    for idx, (x, y, bw, bh) in enumerate(boxes):
        crop = panel_img[y : y + bh, x : x + bw].copy()
        if crop.size == 0:
            continue
        exist_name, score = _best_existing_match(crop, buff_db, icon_dir)
        if exist_name and score >= max(0.82, MATCH_THRESHOLD):
            skipped.append({"name": exist_name, "score": round(float(score), 3)})
            continue

        ocr_name = _ocr_row_name(panel_img, y, x + bw, bh)
        fallback = f"버프_{stamp}_{idx + 1}"
        name = _sanitize_name(ocr_name, fallback)
        # 이름 충돌 시 접미사
        base = name
        n = 2
        while any(b["name"] == name for b in buff_db) or any(a["name"] == name for a in added):
            name = f"{base}_{n}"
            n += 1

        fname = f"{name}.png"
        out_path = os.path.join(icon_dir, fname)
        _save_png(out_path, crop)
        upsert_buff(name, fname, bw, bh)
        added.append({"name": name, "file": fname, "ocr": ocr_name})
        buff_db.append({"name": name, "icon_path": fname})

    return {
        "added": added,
        "skipped": skipped,
        "boxCount": len(boxes),
        "iconCount": len(get_all_buffs()),
    }
