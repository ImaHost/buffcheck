"""시간 텍스트용 색상 마스킹 전처리."""
import cv2
import numpy as np


def preprocess_for_ocr(img: np.ndarray) -> np.ndarray:
    """
    버프 남은시간 텍스트(흰/노란/빨간 계열)를 강조해 OCR용 이진 이미지를 만든다.
    마비노기 임박 시간은 빨간색 'N초'로 표시되는 경우가 많다.
    """
    if img is None or img.size == 0:
        return np.zeros((20, 50), dtype=np.uint8)

    if len(img.shape) == 2:
        gray = img
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        mask_white = cv2.inRange(hsv, np.array([0, 0, 150]), np.array([180, 90, 255]))
        mask_yellow = cv2.inRange(hsv, np.array([15, 40, 140]), np.array([45, 255, 255]))
        # 빨간 임박 시간 (HSV red wraps around 0)
        mask_red1 = cv2.inRange(hsv, np.array([0, 70, 100]), np.array([14, 255, 255]))
        mask_red2 = cv2.inRange(hsv, np.array([160, 70, 100]), np.array([180, 255, 255]))

        mask = mask_white | mask_yellow | mask_red1 | mask_red2

        if cv2.countNonZero(mask) < 5:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    cleaned = cv2.dilate(cleaned, kernel, iterations=1)

    inverted = cv2.bitwise_not(cleaned)

    h, w = inverted.shape[:2]
    if h < 36 or w < 100:
        scale = max(36 / max(h, 1), 100 / max(w, 1), 2.5)
        inverted = cv2.resize(
            inverted,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_CUBIC,
        )

    return inverted
