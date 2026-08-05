"""실행 루트 경로 — 개발/PyInstaller/Electron 패키지 공통."""
import os
import sys


def project_root() -> str:
    env = os.environ.get("BUFFCHECK_ROOT")
    if env:
        return os.path.abspath(env)
    if getattr(sys, "frozen", False):
        return os.path.abspath(os.path.dirname(sys.executable))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
