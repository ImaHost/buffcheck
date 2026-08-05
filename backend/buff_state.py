"""버프 타이머: 로컬 카운트다운이 본체, OCR은 10초 이상 어긋날 때만 보정."""
import time


def _raw_has_minute(raw: str) -> bool:
    text = (raw or "").replace("조", "초").replace("븐", "분")
    return "분" in text


class BuffTimer:
    def __init__(self, name, remaining, confident=True, capture_age=0.0):
        adjusted = max(0.0, float(remaining) - float(capture_age or 0))
        self.name = name
        self.remaining = adjusted
        self._last_tick = time.monotonic()
        self._last_ocr = adjusted
        self._last_ocr_at = time.monotonic()
        self._pending = None
        self.confident = bool(confident)

    def tick(self):
        now = time.monotonic()
        elapsed = now - self._last_tick
        self._last_tick = now
        self.remaining = max(0.0, self.remaining - elapsed)

    def seconds_since_ocr(self):
        return time.monotonic() - self._last_ocr_at

    def apply_ocr_reading(
        self,
        ocr_remaining,
        confident=True,
        capture_age=0.0,
        ocr_raw="",
        resync_diff=10.0,
    ):
        """
        로컬 카운트다운을 기본으로 두고,
        |OCR - 로컬| >= resync_diff 일 때만 캡처 시간으로 다시 맞춤.
        """
        if ocr_remaining is None:
            return False

        ocr_remaining = max(0.0, float(ocr_remaining) - max(0.0, float(capture_age or 0)))
        diff = ocr_remaining - self.remaining
        abs_diff = abs(diff)
        has_minute = _raw_has_minute(ocr_raw)

        # 10초 미만 차이면 로컬 유지 (OCR 노이즈/지연 무시)
        if abs_diff < float(resync_diff):
            self._last_ocr = ocr_remaining
            self._last_ocr_at = time.monotonic()
            self._pending = None
            self.confident = self.confident or confident
            return False

        # --- 상향: 분 단위 갱신만 즉시, 그 외 큰 점프는 잡음으로 2회 확인 ---
        if diff >= float(resync_diff):
            if has_minute:
                self._set(ocr_remaining, confident)
                return True
            # 분 없이 갑자기 +10 이상은 잡음 가능성 → 연속 확인
            return self._confirm_pending(ocr_remaining, confident)

        # --- 하향: 10초 이상 어긋남 → 재동기화 (연속 1회면 충분, 급락은 2회) ---
        drop = -diff
        if drop >= 25:
            return self._confirm_pending(ocr_remaining, confident)
        self._set(ocr_remaining, confident)
        return True

    def _confirm_pending(self, value, confident):
        if self._pending and abs(self._pending[0] - value) <= 3:
            self._pending = (value, self._pending[1] + 1)
        else:
            self._pending = (value, 1)
        if self._pending[1] >= 2:
            self._set(value, confident)
            return True
        return False

    def _set(self, value, confident):
        self.remaining = float(value)
        self._last_ocr = float(value)
        self._last_ocr_at = time.monotonic()
        self._last_tick = time.monotonic()
        self._pending = None
        self.confident = bool(confident)
