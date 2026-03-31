from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class SystemPaths:
    root: Path
    config_dir: Path
    data_dir: Path
    state_dir: Path
    logs_dir: Path


def build_paths() -> SystemPaths:
    tools_dir = Path(__file__).resolve().parent.parent
    return SystemPaths(
        root=tools_dir,
        config_dir=tools_dir / "x_system_config",
        data_dir=tools_dir / "x_system_data",
        state_dir=tools_dir / "x_system_state",
        logs_dir=tools_dir / "x_system_logs",
    )


def ensure_directories(paths: SystemPaths) -> None:
    for path in [paths.config_dir, paths.data_dir, paths.state_dir, paths.logs_dir]:
        path.mkdir(parents=True, exist_ok=True)
    for sub in ["research", "posts", "replies", "decisions", "learning"]:
        (paths.data_dir / sub).mkdir(parents=True, exist_ok=True)


def load_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json_file(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True), encoding="utf-8")


def load_system_config(paths: SystemPaths) -> Dict[str, Any]:
    return load_json_file(paths.config_dir / "config.json", {})


def load_queries(paths: SystemPaths) -> List[str]:
    data = load_json_file(paths.config_dir / "queries.json", {"queries": []})
    return [q for q in data.get("queries", []) if isinstance(q, str) and q.strip()]


def load_tracked_accounts(paths: SystemPaths) -> Dict[str, List[str]]:
    data = load_json_file(paths.config_dir / "tracked_accounts.json", {})
    return {
        "tier1": data.get("tier1", []),
        "tier2": data.get("tier2", []),
        "tier3": data.get("tier3", []),
    }

