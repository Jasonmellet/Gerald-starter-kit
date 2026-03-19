"""
Config for meeting bot. Loads .env from this package directory.
No OpenClaw dependency.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
STATE_DIR = BASE_DIR / "state"
OUTPUT_DIR = BASE_DIR / "output"
CREDENTIALS_DIR = BASE_DIR / "credentials"


def load_env():
    def load_file(path: Path) -> None:
        if not path.exists():
            return
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if k.strip() and v:
                    os.environ.setdefault(k.strip(), v)
    load_file(ENV_FILE)
    # Fallback: parent .env (e.g. Openclaw repo root) so you don't duplicate RECALL_API_KEY etc.
    load_file(BASE_DIR.parent / ".env")


def get(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


# Paths (after load_env)
STATE_FILE = STATE_DIR / "meeting_state.json"
GMAIL_CREDENTIALS = CREDENTIALS_DIR / "gmail-credentials.json"
GMAIL_TOKEN = CREDENTIALS_DIR / "gmail-token.pickle"
