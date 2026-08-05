import os

import cv2
import numpy as np

from config import MATCH_THRESHOLD
from image_io import imread_unicode

# 해상도/UI 스케일 차이를 흡수하기 위한 스케일
_SCALES = (0.7, 0.85, 1.0, 1.15, 1.35, 1.6, 1.85)


def find_all_icons(panel_img: np.ndarray, buff_db: list, icon_dir: str):
    """
    panel_img: F8로 지정한 버프 패널 전체 캡처 이미지
    buff_db: db.get_all_buffs() 결과
    반환: [{"name", "x", "y", "w", "h", "time_offset_*", ...}, ...]
          (패널 이미지 기준 상대 좌표)
    """
    results = []
    if panel_img is None or panel_img.size == 0:
        return results

    if len(panel_img.shape) == 3:
        panel_gray = cv2.cvtColor(panel_img, cv2.COLOR_BGR2GRAY)
    else:
        panel_gray = panel_img

    ph, pw = panel_gray.shape[:2]

    for buff in buff_db:
        template_path = os.path.join(icon_dir, buff["icon_path"])
        template = imread_unicode(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            continue

        best = None  # (score, x, y, tw, th)

        for scale in _SCALES:
            th = max(1, int(round(template.shape[0] * scale)))
            tw = max(1, int(round(template.shape[1] * scale)))
            if th > ph or tw > pw:
                continue
            if abs(scale - 1.0) < 1e-6:
                scaled = template
            else:
                scaled = cv2.resize(template, (tw, th), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)

            res = cv2.matchTemplate(panel_gray, scaled, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            if max_val < MATCH_THRESHOLD:
                continue
            if best is None or max_val > best[0]:
                best = (float(max_val), int(max_loc[0]), int(max_loc[1]), tw, th)

        if best is None:
            continue

        score, x, y, tw, th = best
        results.append({
            "name": buff["name"],
            "x": x,
            "y": y,
            "w": tw,
            "h": th,
            "time_offset_x": buff["time_offset_x"],
            "time_offset_y": buff["time_offset_y"],
            "time_width": buff["time_width"],
            "time_height": buff["time_height"],
            "score": score,
        })

    return _remove_duplicate_matches(results)


def _remove_duplicate_matches(results, min_distance=12):
    """같은 위치 근처 중복 매칭 제거 (점수 높은 것 우선)."""
    sorted_results = sorted(results, key=lambda r: r.get("score", 0), reverse=True)
    filtered = []
    for r in sorted_results:
        duplicate = False
        for f in filtered:
            if abs(r["x"] - f["x"]) < min_distance and abs(r["y"] - f["y"]) < min_distance:
                duplicate = True
                break
            # 같은 버프명은 최고점 1개만
            if r["name"] == f["name"]:
                duplicate = True
                break
        if not duplicate:
            filtered.append(r)
    return filtered
