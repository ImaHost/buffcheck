"""실행 중 갱신되는 설정 (영역좌표 등)."""

# 캡처/아이콘 매칭 주기 (초)
CAPTURE_INTERVAL = 0.5

# 로컬 카운트다운 emit 주기 (초)
TICK_INTERVAL = 1.0

# 추적 중 버프 OCR 재확인 주기 (초) — 자주 안 읽음
OCR_REFRESH_SEC = 5.0

# 로컬 시간과 OCR 차이가 이 값(초) 이상일 때만 재동기화
OCR_RESYNC_DIFF = 10.0

# 최초 잠금 시 추가 보정(초). 캡처~OCR 경과는 capture_age로만 반영.
# (고정 1초 선차감은 게임보다 빨리 깎여 보였음)
INITIAL_LOCK_LAG_SEC = 0.0

# 빨간 UI 시간 허용 상한 (초)
RED_TIME_MAX = 99

# 아이콘 이미지 폴더 (프로젝트 루트 기준)
ICON_DIR = "buff_icons"

# SQLite DB 경로 (프로젝트 루트 기준)
DB_PATH = "icons.db"

# 템플릿 매칭 임계값 (멀티스케일 최고점 기준)
MATCH_THRESHOLD = 0.72

# 알림에 표시할 남은 시간 임계값 (초)
NOTIFY_THRESHOLD = 30
