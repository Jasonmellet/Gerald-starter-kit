#!/usr/bin/env bash
# Print X OAuth authorization link. If ngrok is running on 8765, detect its URL and update .env.
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$REPO/.env"

# Try to get live ngrok URL from local API (requires ngrok running: ngrok http 8765)
NGROK_URL=$(curl -s -m 2 http://127.0.0.1:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for t in d.get('tunnels', []):
        if t.get('proto') == 'https':
            print(t.get('public_url', '').rstrip('/'))
            break
except Exception:
    pass
" 2>/dev/null)

if [[ -n "$NGROK_URL" ]]; then
    # Update .env if different
    if grep -q "^X_CALLBACK_BASE_URL=" "$ENV_FILE" 2>/dev/null; then
        sed -i.bak "s|^X_CALLBACK_BASE_URL=.*|X_CALLBACK_BASE_URL=$NGROK_URL|" "$ENV_FILE"
    else
        echo "X_CALLBACK_BASE_URL=$NGROK_URL" >> "$ENV_FILE"
    fi
    echo "Using ngrok URL: $NGROK_URL"
    echo ""
    echo "1. In X Developer Portal, set Callback URL to:"
    echo "   $NGROK_URL/x/callback"
    echo ""
    echo "2. Open this link in your browser (logged into X):"
    echo "   $NGROK_URL/x/start"
    echo ""
    exit 0
fi

# No ngrok API: read from .env and print link
CALLBACK_BASE=""
if [[ -f "$ENV_FILE" ]]; then
    CALLBACK_BASE=$(grep "^X_CALLBACK_BASE_URL=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'" | sed 's|/$||')
fi
if [[ -n "$CALLBACK_BASE" ]]; then
    echo "Authorization link (from .env):"
    echo "  $CALLBACK_BASE/x/start"
    echo ""
    echo "Callback URL for X Developer Portal:"
    echo "  $CALLBACK_BASE/x/callback"
    exit 0
fi

echo "No X_CALLBACK_BASE_URL found and ngrok not detected."
echo ""
echo "To get a new link:"
echo "  1. Terminal 1: python3 tools/x_oauth_callback_server.py --port 8765"
echo "  2. Terminal 2: ngrok http 8765"
echo "  3. Copy the https://....ngrok-free.app URL from ngrok"
echo "  4. In .env set: X_CALLBACK_BASE_URL=https://YOUR-NGROK-URL"
echo "  5. In X Developer Portal add: https://YOUR-NGROK-URL/x/callback"
echo "  6. Run this script again, or open: https://YOUR-NGROK-URL/x/start"
exit 1
