#!/bin/bash
# Reattach orphan transcript files to sessions.json

SESSIONS_FILE="$HOME/.openclaw/agents/main/sessions/sessions.json"

if [ ! -f "$SESSIONS_FILE" ]; then
    echo "Error: sessions.json not found at $SESSIONS_FILE"
    exit 1
fi

# Create a backup
cp "$SESSIONS_FILE" "$SESSIONS_FILE.backup.$(date +%s)"

# Use Python to safely merge orphan entries into the JSON object
python3 - "$SESSIONS_FILE" << 'PY'
import json
import sys
from pathlib import Path

sessions_path = Path(sys.argv[1])

with sessions_path.open() as f:
    data = json.load(f)

orphan_entries = {
    "agent:main:main:orphan:24421a7e-0fb4-42fd-9059-73f88711b175": {
        "origin": {
            "label": "Orphaned session 2026-03-07",
            "provider": "webchat",
            "surface": "webchat",
            "chatType": "direct",
            "from": "webchat",
            "to": "webchat",
            "accountId": "default",
        },
        "sessionId": "24421a7e-0fb4-42fd-9059-73f88711b175",
        "updatedAt": 1741344426582,
        "systemSent": True,
        "lastMessage": {
            "role": "assistant",
            "channel": "webchat",
            "to": "webchat",
            "accountId": "default",
        },
        "lastChannel": "webchat",
        "lastTo": "webchat",
        "lastAccountId": "default",
        "sessionFile": "/Users/jcore/.openclaw/agents/main/sessions/24421a7e-0fb4-42fd-9059-73f88711b175.jsonl",
    },
    "agent:main:main:orphan:425975fb-6d38-4c4b-9622-dfc651f94720": {
        "origin": {
            "label": "Orphaned session 2026-03-09",
            "provider": "webchat",
            "surface": "webchat",
            "chatType": "direct",
            "from": "webchat",
            "to": "webchat",
            "accountId": "default",
        },
        "sessionId": "425975fb-6d38-4c4b-9622-dfc651f94720",
        "updatedAt": 1741528800097,
        "systemSent": True,
        "lastMessage": {
            "role": "assistant",
            "channel": "webchat",
            "to": "webchat",
            "accountId": "default",
        },
        "lastChannel": "webchat",
        "lastTo": "webchat",
        "lastAccountId": "default",
        "sessionFile": "/Users/jcore/.openclaw/agents/main/sessions/425975fb-6d38-4c4b-9622-dfc651f94720.jsonl",
    },
    "agent:main:main:orphan:889a9724-074e-4044-a0d8-78db50e29f9b": {
        "origin": {
            "label": "Orphaned session 2026-03-08",
            "provider": "webchat",
            "surface": "webchat",
            "chatType": "direct",
            "from": "webchat",
            "to": "webchat",
            "accountId": "default",
        },
        "sessionId": "889a9724-074e-4044-a0d8-78db50e29f9b",
        "updatedAt": 1741427674281,
        "systemSent": True,
        "lastMessage": {
            "role": "assistant",
            "channel": "webchat",
            "to": "webchat",
            "accountId": "default",
        },
        "lastChannel": "webchat",
        "lastTo": "webchat",
        "lastAccountId": "default",
        "sessionFile": "/Users/jcore/.openclaw/agents/main/sessions/889a9724-074e-4044-a0d8-78db50e29f9b.jsonl",
    },
    "agent:main:main:orphan:9dfd3db7-9dea-4447-bc7f-569c99f5361e": {
        "origin": {
            "label": "Orphaned session 2026-03-08",
            "provider": "webchat",
            "surface": "webchat",
            "chatType": "direct",
            "from": "webchat",
            "to": "webchat",
            "accountId": "default",
        },
        "sessionId": "9dfd3db7-9dea-4447-bc7f-569c99f5361e",
        "updatedAt": 1741439146865,
        "systemSent": True,
        "lastMessage": {
            "role": "assistant",
            "channel": "webchat",
            "to": "webchat",
            "accountId": "default",
        },
        "lastChannel": "webchat",
        "lastTo": "webchat",
        "lastAccountId": "default",
        "sessionFile": "/Users/jcore/.openclaw/agents/main/sessions/9dfd3db7-9dea-4447-bc7f-569c99f5361e.jsonl",
    },
    "agent:main:main:orphan:b2270ccc-eaaa-4ee9-a2e7-4439af03ab24": {
        "origin": {
            "label": "Orphaned session 2026-03-07",
            "provider": "webchat",
            "surface": "webchat",
            "chatType": "direct",
            "from": "webchat",
            "to": "webchat",
            "accountId": "default",
        },
        "sessionId": "b2270ccc-eaaa-4ee9-a2e7-4439af03ab24",
        "updatedAt": 1741348615553,
        "systemSent": True,
        "lastMessage": {
            "role": "assistant",
            "channel": "webchat",
            "to": "webchat",
            "accountId": "default",
        },
        "lastChannel": "webchat",
        "lastTo": "webchat",
        "lastAccountId": "default",
        "sessionFile": "/Users/jcore/.openclaw/agents/main/sessions/b2270ccc-eaaa-4ee9-a2e7-4439af03ab24.jsonl",
    },
    "agent:main:main:orphan:b3b78b6b-3d7b-4553-8a2d-8104d3830e02": {
        "origin": {
            "label": "Orphaned session 2026-03-09",
            "provider": "webchat",
            "surface": "webchat",
            "chatType": "direct",
            "from": "webchat",
            "to": "webchat",
            "accountId": "default",
        },
        "sessionId": "b3b78b6b-3d7b-4553-8a2d-8104d3830e02",
        "updatedAt": 1741525200094,
        "systemSent": True,
        "lastMessage": {
            "role": "assistant",
            "channel": "webchat",
            "to": "webchat",
            "accountId": "default",
        },
        "lastChannel": "webchat",
        "lastTo": "webchat",
        "lastAccountId": "default",
        "sessionFile": "/Users/jcore/.openclaw/agents/main/sessions/b3b78b6b-3d7b-4553-8a2d-8104d3830e02.jsonl",
    },
    "agent:main:main:orphan:fe530a45-7764-4f72-a197-1b61eb5fb094": {
        "origin": {
            "label": "Orphaned session 2026-03-06",
            "provider": "webchat",
            "surface": "webchat",
            "chatType": "direct",
            "from": "webchat",
            "to": "webchat",
            "accountId": "default",
        },
        "sessionId": "fe530a45-7764-4f72-a197-1b61eb5fb094",
        "updatedAt": 1741291890940,
        "systemSent": True,
        "lastMessage": {
            "role": "assistant",
            "channel": "webchat",
            "to": "webchat",
            "accountId": "default",
        },
        "lastChannel": "webchat",
        "lastTo": "webchat",
        "lastAccountId": "default",
        "sessionFile": "/Users/jcore/.openclaw/agents/main/sessions/fe530a45-7764-4f72-a197-1b61eb5fb094.jsonl",
    },
}

# If they're already present, do nothing
if any(key in data for key in orphan_entries):
    print("Orphan entries already present; nothing to do.")
    sys.exit(0)

data.update(orphan_entries)

tmp_path = sessions_path.with_suffix(".json.tmp")
with tmp_path.open("w") as f:
    json.dump(data, f, indent=2)

print("✅ Orphan sessions reattached successfully")
PY

