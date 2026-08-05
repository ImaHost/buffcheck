"""유틸 — Windows 한글 경로에서도 이미지를 읽을 수 있게 함."""
import cv2
import numpy as np


def imread_unicode(path: str, flags=cv2.IMREAD_COLOR):
    """cv2.imread 대체. 비ASCII 경로에서도 동작."""
    try:
        data = np.fromfile(path, dtype=np.uint8)
    except OSError:
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)
