import sqlite3
import os

from config import DB_PATH
from app_paths import project_root

_DB_FULL = os.path.join(project_root(), DB_PATH)


def get_connection():
    return sqlite3.connect(_DB_FULL)


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS buffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            icon_path TEXT NOT NULL,
            icon_width INTEGER NOT NULL,
            icon_height INTEGER NOT NULL,
            time_offset_x INTEGER DEFAULT 24,
            time_offset_y INTEGER DEFAULT 0,
            time_width INTEGER DEFAULT 50,
            time_height INTEGER DEFAULT 20,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_all_buffs():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM buffs").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_buff(name, icon_path, w, h):
    conn = get_connection()
    # 리스트 UI: 아이콘 오른쪽~줄 끝까지 시간을 읽도록 넓은 기본값
    conn.execute("""
        INSERT INTO buffs (name, icon_path, icon_width, icon_height, time_offset_x, time_width, time_height)
        VALUES (?, ?, ?, ?, ?, 240, 22)
        ON CONFLICT(name) DO UPDATE SET
            icon_path=excluded.icon_path,
            icon_width=excluded.icon_width,
            icon_height=excluded.icon_height,
            time_offset_x=excluded.time_offset_x
    """, (name, icon_path, w, h, w))
    conn.commit()
    conn.close()
