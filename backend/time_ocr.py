"""시간 텍스트 OCR — 빨간 'N초' / 'N분' 중심."""
import re
import shutil
import os

import cv2
import numpy as np
import pytesseract

from config import RED_TIME_MAX
from app_paths import project_root

_ROOT = project_root()
_LOCAL_TESSDATA = os.environ.get("TESSDATA_PREFIX") or os.path.join(_ROOT, "tessdata")

try:
    _cmd = os.environ.get("TESSERACT_CMD")
    if _cmd and os.path.isfile(_cmd):
        pytesseract.pytesseract.tesseract_cmd = _cmd
    elif not shutil.which("tesseract"):
        for candidate in (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ):
            if os.path.isfile(candidate):
                pytesseract.pytesseract.tesseract_cmd = candidate
                break
except Exception:
    pass


def _tessdata_dir_arg() -> str:
    kor = os.path.join(_LOCAL_TESSDATA, "kor.traineddata")
    eng = os.path.join(_LOCAL_TESSDATA, "eng.traineddata")
    if os.path.isfile(kor) and os.path.isfile(eng):
        # Windows: 따옴표 넣으면 경로에 따옴표가 포함되어 실패
        path = os.path.normpath(_LOCAL_TESSDATA).replace("\\", "/")
        return f"--tessdata-dir {path}"
    return ""


_TESSDATA_ARG = _tessdata_dir_arg()
_HAS_KOR = os.path.isfile(os.path.join(_LOCAL_TESSDATA, "kor.traineddata"))
_LANG = "kor+eng" if (_HAS_KOR and _TESSDATA_ARG) else "eng"

_DIGIT_CONFIGS = (
    r"--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.:",
    r"--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789.:",
)

_FULL_CONFIGS = (
    r"--oem 3 --psm 7",
    r"--oem 3 --psm 8",
)


def _cfg(base: str, use_local: bool = True) -> str:
    if use_local and _TESSDATA_ARG:
        return f"{base} {_TESSDATA_ARG}".strip()
    return base


def red_mask(bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (0, 70, 100), (14, 255, 255)) | cv2.inRange(
        hsv, (160, 70, 100), (180, 255, 255)
    )


def _prepare_red_digits(bgr: np.ndarray):
    """
    빨간 시간 전용: 검정 배경 + 흰 글자 + 바운딩박스 크롭 + 스케일업.
    dilate는 숫자를 뭉개서 제외. 확대 후 다시 이진화해 선명하게.
    """
    if bgr is None or bgr.size == 0:
        return None
    rm = red_mask(bgr)
    ys, xs = np.where(rm > 0)
    if len(xs) < 8:
        return None

    x1 = max(0, int(xs.min()) - 3)
    x2 = min(rm.shape[1], int(xs.max()) + 4)
    y1 = max(0, int(ys.min()) - 3)
    y2 = min(rm.shape[0], int(ys.max()) + 4)
    crop = rm[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    h, w = crop.shape[:2]
    big = cv2.resize(crop, (max(1, w * 5), max(1, h * 5)), interpolation=cv2.INTER_CUBIC)
    # 확대 blur 제거 → 선명한 이진
    _, big = cv2.threshold(big, 80, 255, cv2.THRESH_BINARY)
    return cv2.copyMakeBorder(big, 12, 12, 16, 16, cv2.BORDER_CONSTANT, value=0)


def _prepare_white_digits(bgr: np.ndarray):

    """흰/밝은 시간 텍스트 → 검정 배경 흰 글자."""
    if bgr is None or bgr.size == 0:
        return None
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if len(bgr.shape) == 3 else bgr
    _, thr = cv2.threshold(gray, 170, 255, cv2.THRESH_BINARY)
    ys, xs = np.where(thr > 0)
    if len(xs) < 8:
        return None
    x1 = max(0, int(xs.min()) - 2)
    x2 = min(thr.shape[1], int(xs.max()) + 3)
    y1 = max(0, int(ys.min()) - 2)
    y2 = min(thr.shape[0], int(ys.max()) + 3)
    crop = thr[y1:y2, x1:x2]
    h, w = crop.shape[:2]
    scale = max(4.0, 48 / max(h, 1), 140 / max(w, 1))
    big = cv2.resize(
        crop,
        (max(1, int(w * scale)), max(1, int(h * scale))),
        interpolation=cv2.INTER_NEAREST,
    )
    return cv2.copyMakeBorder(big, 8, 8, 10, 10, cv2.BORDER_CONSTANT, value=0)


def crop_time_for_match(panel_img: np.ndarray, match: dict):
    """아이콘 줄의 우측 시간칸을 자른다. (게임 배경 빨간 이펙트에 덜 민감)"""
    if panel_img is None or panel_img.size == 0:
        return None, "empty"

    ph, pw = panel_img.shape[:2]
    y1 = max(0, int(match["y"]) - 3)
    y2 = min(ph, int(match["y"]) + max(int(match["h"]) + 8, 20))
    icon_r = int(match["x"]) + int(match["w"]) + 4

    x1 = max(icon_r + 70, pw - 130)
    if x1 >= pw:
        return None, "no-room"

    strip = panel_img[y1:y2, x1:pw]
    if strip.size == 0:
        return None, "empty"

    # 시간칸 안 빨간 픽셀이 '적당히' 있으면 임박(빨간 초) 후보
    mask = red_mask(strip)
    red_px = int(cv2.countNonZero(mask))
    area = max(1, strip.shape[0] * strip.shape[1])
    if 20 <= red_px <= max(80, area // 3):
        return strip, "red"
    return strip, "edge"


def _normalize_raw(raw: str) -> str:
    return (raw or "").replace("조", "초").replace("븐", "분").replace(" ", "")


def _has_time_unit(raw: str) -> bool:
    text = _normalize_raw(raw)
    return "분" in text or "초" in text


def _ocr_confident(raw: str, remaining, crop_mode: str) -> bool:
    """분/초 단위가 있거나, 빨간 임박 초로 읽힌 경우만 신뢰."""
    if remaining is None:
        return False
    if _has_time_unit(raw):
        return True
    # 순수 숫자는 빨간 임박(≤30초)만 신뢰
    return crop_mode == "red" and 1 <= float(remaining) <= RED_TIME_MAX


def _ocr_score(result: dict, red_mode: bool = False) -> int:
    """파싱 결과 우선순위. 빨간 임박은 'N초'/짧은 숫자만 높게."""
    if not result:
        return -1
    rem = result.get("remaining")
    raw = _normalize_raw(result.get("raw") or "")
    if rem is None:
        return 1 if raw else 0

    if red_mode:
        if "분" in raw or rem > RED_TIME_MAX:
            return -50
        score = 50
        if "초" in raw and 1 <= rem <= RED_TIME_MAX:
            score += 120
        # 두 자리(10~99)가 한 자리 오인식(41→1)보다 우선
        if 10 <= rem <= RED_TIME_MAX:
            score += 60
        elif 1 <= rem <= 9:
            score += 10
            if "초" not in raw:
                score -= 80
        digits = "".join(ch for ch in raw if ch.isdigit())
        if digits == str(int(rem)):
            score += 20
        if len(digits) >= 2:
            score += 30
        return score

    score = 50
    if "분" in raw:
        score += 120
    if "초" in raw:
        score += 80
    if "분" in raw and "초" in raw:
        score += 40
    if "분" not in raw and "초" not in raw:
        if rem <= 30:
            score += 10
        else:
            score -= 40
    return score


def read_time_for_match(panel_img: np.ndarray, match: dict):
    """시간칸 OCR. 흰 글씨(분/초)와 빨간 임박 초를 모두 시도."""
    strip, mode = crop_time_for_match(panel_img, match)
    if strip is None:
        return {"remaining": None, "raw": "", "error": "시간 영역 없음", "confident": False}, mode

    result = read_time_debug(strip, prefer_red=(mode == "red"))
    remaining = result.get("remaining")
    raw = result.get("raw") or ""

    if mode == "red":
        if remaining is not None and remaining > RED_TIME_MAX:
            result = {
                "remaining": None,
                "raw": raw,
                "error": f"빨간 시간 범위 초과: {remaining}",
                "confident": False,
            }
        elif remaining is not None and "분" in _normalize_raw(raw):
            result = {
                "remaining": None,
                "raw": raw,
                "error": "빨간 시간에 분 단위 오인식",
                "confident": False,
            }
        elif remaining is not None and remaining <= 9 and "초" not in _normalize_raw(raw):
            # '41'→'1' 같은 한 자리 잘림 거부
            result = {
                "remaining": None,
                "raw": raw,
                "error": "한 자리 숫자만 — 신뢰 부족",
                "confident": False,
            }
        elif remaining is not None:
            result["confident"] = True
        else:
            result["confident"] = False
        return result, mode

    if remaining is not None and not _has_time_unit(raw):
        result = {
            "remaining": None,
            "raw": raw,
            "error": "단위 없는 숫자 OCR 무시",
            "confident": False,
        }
    else:
        result["confident"] = _ocr_confident(raw, remaining, mode)

    return result, mode


def _valid_time(sec, raw: str, red_mode: bool = False) -> bool:
    raw = raw or ""
    if sec is None:
        return False
    raw_n = _normalize_raw(raw)
    if red_mode:
        if "분" in raw_n:
            return False
        return 1 <= sec <= RED_TIME_MAX
    if "초" in raw_n or "분" in raw_n:
        return 0 <= sec <= 36000
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits or len(digits) > 3:
        return False
    if sec <= 0:
        return False
    return 1 <= sec <= 30


def read_time_debug(img, prefer_red: bool = False):
    """returns {remaining, raw, error}"""
    if img is None or getattr(img, "size", 0) == 0:
        return {"remaining": None, "raw": "", "error": "빈 이미지"}

    variants = []
    if prefer_red:
        prepared = _prepare_red_digits(img)
        if prepared is not None:
            variants.append(prepared)
            variants.append(cv2.bitwise_not(prepared))
    else:
        white = _prepare_white_digits(img)
        if white is not None:
            variants.append(white)
        try:
            from color_mask import preprocess_for_ocr
            variants.append(preprocess_for_ocr(img))
        except Exception:
            pass
        h, w = img.shape[:2]
        scale = max(4.0, 48 / max(h, 1), 150 / max(w, 1))
        big = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else big
        _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.extend([cv2.bitwise_not(thr), gray])

    if not variants:
        return {"remaining": None, "raw": "", "error": "전처리 실패"}

    best = {"remaining": None, "raw": "", "error": None}
    best_score = -1
    last_err = None

    if prefer_red:
        # psm7만 쓰면 '41'→'1'로 잘림. psm7+8 모두 시도
        attempts = (
            (True, "eng", _DIGIT_CONFIGS),
            (True, _LANG, (r"--oem 3 --psm 7", r"--oem 3 --psm 8")),
        )
    else:
        attempts = (
            (True, _LANG, _FULL_CONFIGS[:1]),
            (True, "eng", _DIGIT_CONFIGS[:1]),
        )

    for variant in variants:
        for use_local, lang, configs in attempts:
            for config in configs:
                try:
                    text = pytesseract.image_to_string(
                        variant, lang=lang, config=_cfg(config, use_local=use_local)
                    )
                except Exception as e:
                    last_err = str(e).split("\n")[0][:140]
                    continue
                raw = (text or "").strip().replace("\n", " ")
                parsed = _parse_time_text(text)
                ok = parsed is not None and _valid_time(parsed, raw, red_mode=prefer_red)
                cand = {
                    "remaining": int(parsed) if ok else None,
                    "raw": raw,
                    "error": None if ok else (f"파싱 실패: {raw}" if raw else None),
                }
                score = _ocr_score(cand, red_mode=prefer_red)
                if score > best_score:
                    best_score = score
                    best = cand
                # 빨간 임박: 'N초'로 읽혔을 때만 조기 종료
                if ok and prefer_red and "초" in _normalize_raw(raw) and 1 <= int(parsed) <= RED_TIME_MAX:
                    best["error"] = None
                    return best
                if (
                    ok
                    and not prefer_red
                    and "분" in _normalize_raw(raw)
                    and "초" in _normalize_raw(raw)
                ):
                    best["error"] = None
                    return best

    if best.get("remaining") is not None:
        best["error"] = None
        return best
    if not best.get("raw"):
        return {"remaining": None, "raw": "", "error": last_err or "OCR 텍스트 없음"}
    return {
        "remaining": None,
        "raw": best.get("raw") or "",
        "error": best.get("error") or f"파싱 실패: {best.get('raw')}",
    }


def read_time_from_region(img):
    return read_time_debug(img)["remaining"]


def _parse_time_text(text):
    if not text:
        return None

    cleaned = text.strip().replace(" ", "").replace("\n", "").replace(",", ".")
    cleaned = cleaned.replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1")
    cleaned = cleaned.replace("조", "초").replace("분", "분")
    if not cleaned:
        return None

    m_min = re.search(r"(\d+(?:\.\d+)?)\s*분", cleaned)
    if m_min:
        # "20분57초" / "4분 31초"
        m_combo = re.search(r"(\d+)\s*분\s*(\d+)\s*초", cleaned)
        if m_combo:
            return int(m_combo.group(1)) * 60 + int(m_combo.group(2))
        return max(0, int(round(float(m_min.group(1)) * 60)))

    m_sec = re.search(r"(\d+(?:\.\d+)?)\s*초", cleaned)
    if m_sec:
        return max(0, int(round(float(m_sec.group(1)))))

    m = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", cleaned)
    if m:
        if m.group(3) is not None:
            return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        return int(m.group(1)) * 60 + int(m.group(2))

    m_dec = re.search(r"^(\d+)\.(\d+)$", cleaned)
    if m_dec:
        return max(0, int(round(float(cleaned) * 60)))

    # 순수 숫자 — 최대 3자리만
    m_num = re.search(r"^(\d{1,3})$", cleaned)
    if m_num:
        return int(m_num.group(1))

    digits = re.sub(r"[^\d]", "", cleaned)
    if digits and len(digits) <= 3:
        try:
            return int(digits)
        except ValueError:
            return None
    return None
