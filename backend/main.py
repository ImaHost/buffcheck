"""메인 루프 진입점 - 화면 캡처 → 아이콘 매칭 → OCR → JSON emit."""
import json
import os
import re
import sys
import threading
import time

import mss
import numpy as np

# backend 디렉터리에서 실행해도 import 되도록
sys.path.insert(0, os.path.dirname(__file__))

# Windows cp949 콘솔에서 한글/특수문자 print 시 프로세스 사망 방지
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import (
    CAPTURE_INTERVAL,
    ICON_DIR,
    INITIAL_LOCK_LAG_SEC,
    NOTIFY_THRESHOLD,
    OCR_REFRESH_SEC,
    OCR_RESYNC_DIFF,
    TICK_INTERVAL,
)
from db import get_all_buffs, init_db
from icon_matcher import find_all_icons
from time_ocr import read_time_for_match
from buff_state import BuffTimer
from app_paths import project_root
from auto_register import auto_register_from_panel

_ROOT = project_root()
_ICON_DIR = os.path.join(_ROOT, ICON_DIR)
_DEBUG_DIR = os.path.join(_ROOT, "debug", "ocr")

state = {
    "region": None,
    "running": False,
    "notify_threshold": NOTIFY_THRESHOLD,
}
active_buffs = {}
buff_db = []
_last_log = {}
_buff_lock = threading.Lock()
_last_meta = {"matchCount": 0, "detections": []}


def reload_icons():
    global buff_db
    buff_db = get_all_buffs()
    print(f"[backend] loaded {len(buff_db)} buff icons", file=sys.stderr, flush=True)
    return len(buff_db)


def listen_commands():
    """stdin에서 Electron이 보낸 명령(JSON) 수신."""
    for line in sys.stdin:
        try:
            cmd = json.loads(line)
        except json.JSONDecodeError:
            continue

        cmd_type = cmd.get("type")

        if cmd_type == "set_region":
            state["region"] = {
                "x": int(cmd["x"]),
                "y": int(cmd["y"]),
                "width": int(cmd["width"]),
                "height": int(cmd["height"]),
            }
            print(
                f"[backend] region set: {state['region']}",
                file=sys.stderr,
                flush=True,
            )

        elif cmd_type == "start":
            if state["region"] is None:
                emit({"type": "error", "message": "감시 영역이 지정되지 않았습니다."})
                print("[backend] start denied: no region", file=sys.stderr, flush=True)
                continue
            count = reload_icons()
            if count == 0:
                emit({
                    "type": "error",
                    "message": "등록된 버프 아이콘이 없습니다. buff_icons에 PNG를 넣고 DB를 빌드하세요.",
                })
                print("[backend] start denied: no icons", file=sys.stderr, flush=True)
                continue
            with _buff_lock:
                active_buffs.clear()
                _last_meta["matchCount"] = 0
                _last_meta["detections"] = []
            state["running"] = True
            emit({"type": "status", "running": True, "iconCount": count})
            print("[backend] monitoring started", file=sys.stderr, flush=True)

        elif cmd_type == "stop":
            state["running"] = False
            with _buff_lock:
                active_buffs.clear()
                _last_meta["matchCount"] = 0
                _last_meta["detections"] = []
            emit({"type": "status", "running": False, "buffs": []})
            print("[backend] stopped", file=sys.stderr, flush=True)

        elif cmd_type == "reload_icons":
            count = reload_icons()
            emit({"type": "status", "iconCount": count})

        elif cmd_type == "set_notify_threshold":
            try:
                sec = int(cmd.get("seconds", NOTIFY_THRESHOLD))
            except (TypeError, ValueError):
                sec = NOTIFY_THRESHOLD
            sec = max(1, min(60, sec))
            state["notify_threshold"] = sec
            print(
                f"[backend] notify threshold: {sec}s",
                file=sys.stderr,
                flush=True,
            )
            emit({"type": "status", "notifyThreshold": sec})

        elif cmd_type == "auto_register":
            # 영역 캡처 → 아이콘 자동 등록 → DB 리로드
            try:
                x = int(cmd["x"])
                y = int(cmd["y"])
                width = int(cmd["width"])
                height = int(cmd["height"])
            except (KeyError, TypeError, ValueError) as e:
                emit({
                    "type": "auto_register_result",
                    "ok": False,
                    "message": f"영역 좌표 오류: {e}",
                })
                continue

            try:
                with mss.MSS() as sct:
                    shot = sct.grab({
                        "left": x,
                        "top": y,
                        "width": max(1, width),
                        "height": max(1, height),
                    })
                    panel = np.ascontiguousarray(np.array(shot)[:, :, :3])
                result = auto_register_from_panel(panel)
                count = reload_icons()
                emit({
                    "type": "auto_register_result",
                    "ok": True,
                    "added": result.get("added") or [],
                    "skipped": result.get("skipped") or [],
                    "boxCount": result.get("boxCount") or 0,
                    "iconCount": count,
                    "message": (
                        f"신규 {len(result.get('added') or [])}개 등록 "
                        f"(유지 {len(result.get('skipped') or [])}개)"
                    ),
                })
                emit({"type": "status", "iconCount": count})
            except Exception as e:
                print(f"[backend] auto_register error: {e}", file=sys.stderr, flush=True)
                emit({
                    "type": "auto_register_result",
                    "ok": False,
                    "message": str(e),
                })


def emit(data: dict):
    """Windows cp949 콘솔에서도 죽지 않도록 UTF-8로 stdout에 기록."""
    line = json.dumps(data, ensure_ascii=False) + "\n"
    try:
        sys.stdout.buffer.write(line.encode("utf-8"))
        sys.stdout.buffer.flush()
    except Exception:
        # 최후 수단: ASCII escape
        sys.stdout.write(json.dumps(data, ensure_ascii=True) + "\n")
        sys.stdout.flush()


def _safe_str(value, limit=80):
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("\r", " ")
    return text[:limit]


def _snapshot_and_emit(match_count=None, detections=None, do_tick=True):
    """로컬 카운트다운을 반영해 UI로 보낸다 (1초 단위 갱신용)."""
    with _buff_lock:
        if do_tick:
            for t in list(active_buffs.values()):
                t.tick()

        # 만료(0초) 제거 — 명세: 갱신 알림은 유효한 남은 시간만
        for name in list(active_buffs.keys()):
            if active_buffs[name].remaining <= 0:
                del active_buffs[name]

        buffs = [
            {"name": t.name, "remaining": round(t.remaining, 1)}
            for t in active_buffs.values()
            if t.remaining > 0
        ]
        threshold = float(state.get("notify_threshold") or NOTIFY_THRESHOLD)
        renewals = [
            b for b in buffs
            if 0 < b["remaining"] <= threshold
        ]

        if match_count is not None:
            _last_meta["matchCount"] = int(match_count)
        if detections is not None:
            # 추적 중이면 OCR 실패 칸에도 로컬 남은 시간 채움
            by_name = {t.name: t for t in active_buffs.values()}
            filled = []
            for d in detections:
                item = dict(d)
                timer = by_name.get(d["name"])
                if timer is not None and item.get("remaining") is None:
                    item["remaining"] = round(timer.remaining, 1)
                filled.append(item)
            _last_meta["detections"] = filled

        emit({
            "type": "frame",
            "buffs": buffs,
            "renewals": renewals,
            "detections": _last_meta.get("detections") or [],
            "matchCount": _last_meta.get("matchCount") or 0,
            "trackedCount": len(buffs),
        })


def tick_loop():
    """OCR과 무관하게 1초마다 남은 시간을 깎아 UI에 전달."""
    while True:
        time.sleep(TICK_INTERVAL)
        if not state["running"]:
            continue
        with _buff_lock:
            if not active_buffs:
                continue
        try:
            _snapshot_and_emit(do_tick=True)
        except Exception as e:
            print(f"[backend] tick error: {e}", file=sys.stderr, flush=True)


def _should_ocr(name: str, panel_img, match) -> bool:
    """
    OCR 수행 여부.
    - 미추적: 빨간 임박 시간이 보일 때만 (최초 시각 잠금)
    - 추적 중: 주기적 검증만 (평소는 로컬 타이머)
    """
    with _buff_lock:
        timer = active_buffs.get(name)
        if timer is None:
            return _row_has_red_time(panel_img, match)
        return timer.seconds_since_ocr() >= OCR_REFRESH_SEC


def main_loop():
    init_db()
    count = reload_icons()
    emit({"type": "status", "iconCount": count})

    with mss.MSS() as sct:
        while True:
            if not state["running"] or state["region"] is None:
                time.sleep(0.5)
                continue

            r = state["region"]
            if r["width"] <= 0 or r["height"] <= 0:
                time.sleep(0.5)
                continue

            try:
                shot = sct.grab({
                    "left": r["x"],
                    "top": r["y"],
                    "width": r["width"],
                    "height": r["height"],
                })
                capture_mono = time.monotonic()
                panel_img = np.array(shot)[:, :, :3]
                panel_img = np.ascontiguousarray(panel_img)
            except Exception as e:
                print(f"[backend] capture error: {e}", file=sys.stderr, flush=True)
                time.sleep(CAPTURE_INTERVAL)
                continue

            try:
                process_frame(panel_img, capture_mono=capture_mono)
            except Exception as e:
                print(f"[backend] frame error: {e}", file=sys.stderr, flush=True)

            time.sleep(CAPTURE_INTERVAL)


def _row_has_red_time(panel_img, match) -> bool:
    """해당 줄 우측 시간칸에 빨간 픽셀이 있으면 임박 후보."""
    try:
        from time_ocr import crop_time_for_match, red_mask
        import cv2

        strip, mode = crop_time_for_match(panel_img, match)
        if strip is None or strip.size == 0:
            return False
        if mode == "red":
            return True
        return int(cv2.countNonZero(red_mask(strip))) >= 20
    except Exception:
        return False


def process_frame(panel_img, capture_mono=None):
    """
    지속 캡처로 아이콘 존재만 확인.
    시간은 한 번 OCR로 잠근 뒤 로컬 타이머로 흐르게 하고,
    |로컬 - 캡처 OCR| >= OCR_RESYNC_DIFF 일 때만 재동기화.
    OCR 실패는 추적 끊지 않음 (아이콘이 사라질 때만 제거).
    """
    if capture_mono is None:
        capture_mono = time.monotonic()

    matches = find_all_icons(panel_img, buff_db, _ICON_DIR)
    matches = sorted(
        matches,
        key=lambda m: (0 if _row_has_red_time(panel_img, m) else 1, m.get("y", 0)),
    )
    seen = set()
    detections = []

    for m in matches:
        name = m["name"]
        seen.add(name)
        do_ocr = _should_ocr(name, panel_img, m)

        with _buff_lock:
            timer = active_buffs.get(name)
            local_remaining = round(timer.remaining, 1) if timer else None
            local_confident = bool(timer.confident) if timer else False

        if not do_ocr:
            detections.append({
                "name": name,
                "score": round(float(m.get("score", 0)), 3),
                "remaining": local_remaining,
                "ocrOk": False,
                "ocrRaw": "",
                "ocrError": "",
                "cropMode": "local",
                "confident": local_confident,
            })
            continue

        ocr, crop_mode = read_time_for_match(panel_img, m)
        remaining = ocr.get("remaining")
        confident = bool(ocr.get("confident"))
        ocr_raw = _safe_str(ocr.get("raw"))
        ocr_error = _safe_str(ocr.get("error"))
        # 캡처 시각 → OCR 완료까지의 경과 (프레임 내 처리 지연)
        capture_age = max(0.0, time.monotonic() - capture_mono)
        if remaining is not None:
            remaining = max(0.0, float(remaining) - capture_age)

        # OCR 실패해도 아이콘이 보이면 로컬 타이머 유지
        if remaining is None or remaining <= 0 or not confident:
            detections.append({
                "name": name,
                "score": round(float(m.get("score", 0)), 3),
                "remaining": local_remaining,
                "ocrOk": False,
                "ocrRaw": ocr_raw,
                "ocrError": ocr_error or "ocr_fail_keep_local",
                "cropMode": crop_mode,
                "confident": local_confident,
            })
            key = f"{name}:ocr-skip:{ocr_raw}"
            if _last_log.get(name) != key:
                _last_log[name] = key
                keep = (
                    f" keep={local_remaining}s"
                    if local_remaining is not None
                    else " (no lock yet)"
                )
                print(
                    f"[backend] match {name} score={m.get('score', 0):.2f} "
                    f"mode={crop_mode} OCR=skip{keep} raw={ocr_raw!r}",
                    file=sys.stderr,
                    flush=True,
                )
            continue

        with _buff_lock:
            if name not in active_buffs:
                # capture_age는 위에서 이미 remaining에 반영됨
                active_buffs[name] = BuffTimer(
                    name,
                    remaining,
                    confident=True,
                    capture_age=INITIAL_LOCK_LAG_SEC,
                )
                action = "lock"
            else:
                before = active_buffs[name].remaining
                active_buffs[name].apply_ocr_reading(
                    remaining,
                    confident=True,
                    capture_age=0,
                    ocr_raw=ocr_raw,
                    resync_diff=OCR_RESYNC_DIFF,
                )
                after = active_buffs[name].remaining
                if abs(after - before) >= 0.5:
                    action = f"resync {before:.0f}->{after:.0f}"
                else:
                    action = f"keep local={after:.0f} (ocr={remaining:.0f})"

            shown = round(active_buffs[name].remaining, 1)

        detections.append({
            "name": name,
            "score": round(float(m.get("score", 0)), 3),
            "remaining": shown,
            "ocrOk": True,
            "ocrRaw": ocr_raw,
            "ocrError": "",
            "cropMode": crop_mode,
            "confident": True,
        })

        key = f"{name}:{action}:{shown}"
        if _last_log.get(name) != key:
            _last_log[name] = key
            print(
                f"[backend] match {name} score={m.get('score', 0):.2f} "
                f"mode={crop_mode} {action} age={capture_age:.1f}s "
                f"raw={ocr_raw!r}",
                file=sys.stderr,
                flush=True,
            )

    # 아이콘이 영역에서 사라진 버프만 제거
    with _buff_lock:
        for name in list(active_buffs.keys()):
            if name not in seen:
                del active_buffs[name]
            elif active_buffs[name].remaining <= 0:
                del active_buffs[name]

    _snapshot_and_emit(match_count=len(matches), detections=detections, do_tick=False)


if __name__ == "__main__":
    threading.Thread(target=listen_commands, daemon=True).start()
    threading.Thread(target=tick_loop, daemon=True).start()
    main_loop()
