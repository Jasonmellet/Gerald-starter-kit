#!/usr/bin/env python3
"""
Meeting orchestrator health check.

Runs as a periodic watchdog and alerts via Telegram if the meeting orchestrator
appears unhealthy for N checks in a row.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


DEFAULT_CHAT_ID = "8130598479"
DEFAULT_FAIL_THRESHOLD = 3
DEFAULT_COOLDOWN_MINUTES = 360
DEFAULT_RECENT_WINDOW_MINUTES = 20
DEFAULT_MAX_LOG_LINES = 400


def _now() -> datetime:
    return datetime.now()


def _to_iso(ts: datetime) -> str:
    return ts.isoformat()


def _from_iso(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _runtime_root() -> Path:
    # Launchd runtime is intentionally moved off Desktop to ~/Openclaw.
    home_runtime = Path.home() / "Openclaw"
    if (home_runtime / "logs" / "meeting_orchestrator_launchd.log").exists():
        return home_runtime
    return _repo_root()


def _read_tail(path: Path, max_lines: int) -> list[str]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if len(lines) <= max_lines:
            return lines
        return lines[-max_lines:]
    except Exception:
        return []


def _is_recent(path: Path, minutes: int) -> bool:
    if not path.exists():
        return False
    cutoff = _now() - timedelta(minutes=minutes)
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return mtime >= cutoff


def _health_snapshot(runtime_root: Path, recent_window_minutes: int, max_log_lines: int) -> dict:
    log_out = runtime_root / "logs" / "meeting_orchestrator_launchd.log"
    log_err = runtime_root / "logs" / "meeting_orchestrator_launchd.err"

    out_lines = _read_tail(log_out, max_log_lines)
    err_lines = _read_tail(log_err, max_log_lines)

    out_recent = _is_recent(log_out, recent_window_minutes)
    has_recent_poll = any("Polling..." in line for line in out_lines[-120:])
    has_recent_init = any("Recall.ai connected" in line or "Gmail connected" in line for line in out_lines[-200:])

    fatal_markers = (
        "Operation not permitted",
        "can't open file",
        "Traceback",
        "Initialization failed",
        "Cannot start - initialization failed",
    )
    recent_err = err_lines[-40:]

    def _is_stale_desktop_error(line: str) -> bool:
        # After migration to ~/Openclaw, old Desktop launchd errors can remain in tail.
        return str(runtime_root).endswith("/Openclaw") and "/Desktop/Openclaw/" in line

    fatal_count = 0
    for line in recent_err:
        if _is_stale_desktop_error(line):
            continue
        if any(marker in line for marker in fatal_markers):
            fatal_count += 1

    healthy = out_recent and has_recent_poll and has_recent_init and fatal_count == 0

    reason = []
    if not out_recent:
        reason.append("no_recent_launchd_log_activity")
    if not has_recent_poll:
        reason.append("no_recent_poll_loop")
    if not has_recent_init:
        reason.append("no_recent_client_init")
    if fatal_count > 0:
        reason.append(f"fatal_errors={fatal_count}")

    return {
        "healthy": healthy,
        "runtime_root": str(runtime_root),
        "log_out": str(log_out),
        "log_err": str(log_err),
        "fatal_count": fatal_count,
        "reasons": reason,
    }


def _state_path(runtime_root: Path) -> Path:
    return runtime_root / "logs" / "meeting_orchestrator_health_state.json"


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {
            "consecutive_failures": 0,
            "last_alerted_at": None,
            "last_status": "unknown",
            "last_check_at": None,
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "consecutive_failures": 0,
            "last_alerted_at": None,
            "last_status": "unknown",
            "last_check_at": None,
        }


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _send_telegram_alert(repo_root: Path, message: str) -> bool:
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", DEFAULT_CHAT_ID)
    sender = repo_root / "tools" / "sessions_send.py"
    if not sender.exists():
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(sender), chat_id, message],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


def main() -> int:
    repo_root = _repo_root()
    runtime_root = _runtime_root()

    fail_threshold = int(os.environ.get("MEETING_HEALTH_FAIL_THRESHOLD", str(DEFAULT_FAIL_THRESHOLD)))
    cooldown_minutes = int(os.environ.get("MEETING_HEALTH_ALERT_COOLDOWN_MINUTES", str(DEFAULT_COOLDOWN_MINUTES)))
    recent_window_minutes = int(
        os.environ.get("MEETING_HEALTH_RECENT_WINDOW_MINUTES", str(DEFAULT_RECENT_WINDOW_MINUTES))
    )
    max_log_lines = int(os.environ.get("MEETING_HEALTH_MAX_LOG_LINES", str(DEFAULT_MAX_LOG_LINES)))

    snapshot = _health_snapshot(runtime_root, recent_window_minutes, max_log_lines)
    state_file = _state_path(runtime_root)
    state = _load_state(state_file)

    now = _now()
    last_alerted_at = _from_iso(state.get("last_alerted_at"))
    cooldown_ok = last_alerted_at is None or (now - last_alerted_at) >= timedelta(minutes=cooldown_minutes)

    if snapshot["healthy"]:
        was_unhealthy = state.get("last_status") == "unhealthy"
        state["consecutive_failures"] = 0
        state["last_status"] = "healthy"
        state["last_check_at"] = _to_iso(now)
        _save_state(state_file, state)
        if was_unhealthy:
            recovery = (
                "✅ Meeting orchestrator recovered.\n"
                f"- Runtime: {snapshot['runtime_root']}\n"
                "- Polling and client init look healthy again."
            )
            _send_telegram_alert(repo_root, recovery)
        return 0

    failures = int(state.get("consecutive_failures", 0)) + 1
    state["consecutive_failures"] = failures
    state["last_status"] = "unhealthy"
    state["last_check_at"] = _to_iso(now)

    should_alert = failures >= fail_threshold and cooldown_ok
    if should_alert:
        reason_text = ", ".join(snapshot["reasons"]) if snapshot["reasons"] else "unknown"
        msg = (
            "🚨 Meeting orchestrator health alert\n"
            f"- Consecutive failed checks: {failures}\n"
            f"- Runtime: {snapshot['runtime_root']}\n"
            f"- Reason: {reason_text}\n"
            f"- Error log: {snapshot['log_err']}\n"
            f"- Output log: {snapshot['log_out']}"
        )
        sent = _send_telegram_alert(repo_root, msg)
        if sent:
            state["last_alerted_at"] = _to_iso(now)

    _save_state(state_file, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
