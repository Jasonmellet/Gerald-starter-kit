# X (Twitter) OAuth 2.0 — Real Callback URL Setup

You need a **real** (HTTPS) callback URL so X can redirect users back to your app after they authorize. Two ways to get one:

---

## Option A: Tunnel (no domain required)

Use **ngrok** or **Cloudflare Tunnel** so a public HTTPS URL forwards to your Mac.

1. **Install ngrok:** https://ngrok.com/download  
   Or: `brew install ngrok`

2. **Run your callback server** (see below) on a port, e.g. 8765:
   ```bash
   python3 tools/x_oauth_callback_server.py --port 8765
   ```

3. **Expose it:**
   ```bash
   ngrok http 8765
   ```
   You’ll get a URL like `https://abc123.ngrok-free.app`.

4. **Use that as your callback base:**  
   Callback URL = `https://abc123.ngrok-free.app/x/callback`  
   Add it in the X Developer Portal (see “Where to add the URL” below).  
   Set in `.env`:
   ```bash
   X_CALLBACK_BASE_URL=https://abc123.ngrok-free.app
   ```

5. **Start the OAuth flow:** Open in browser:
   ```
   https://abc123.ngrok-free.app/x/start
   ```
   After you authorize on X, you’ll be redirected back and the server will save tokens to `credentials/x_oauth_tokens.json`.

**Note:** With a free ngrok URL, the hostname changes each time you restart ngrok. Update the callback URL in the X portal and `X_CALLBACK_BASE_URL` when that happens, or use a fixed ngrok domain if you have one.

---

## Option B: Your own domain (HTTPS)

If you have a domain and a server (VPS, Railway, Fly.io, etc.) with HTTPS:

1. **Callback URL:** `https://yourdomain.com/x/callback`  
   (Or any path you choose, e.g. `https://api.yourdomain.com/oauth/x/callback`.)

2. **Add it in the X Developer Portal** (see below).

3. **Run the same callback server** on that host, or deploy a small app that:
   - Serves `GET /x/callback?code=...&state=...`
   - Exchanges `code` for access/refresh tokens (OAuth 2.0 PKCE)
   - Saves tokens (or sends them to your Openclaw machine)

4. Set in `.env`:
   ```bash
   X_CALLBACK_BASE_URL=https://yourdomain.com
   ```

---

## Where to add the URL in X Developer Portal

1. Go to **[X Developer Portal](https://developer.x.com)** → **Projects & Apps** → your app.
2. Open **Settings** (or **User authentication settings**).
3. Under **Callback URI / Redirect URL** (or **OAuth 2.0 redirect URLs**), add **exactly**:
   - Tunnel: `https://YOUR-NGROK-URL/x/callback`
   - Own domain: `https://yourdomain.com/x/callback`
4. Save. You can list up to **10** callback URLs per app; the one you use in the flow must match **exactly** (including path and trailing slash if you use it).

---

## .env variables for OAuth 2.0 callback flow

Your app uses **OAuth 2.0 with PKCE**. You need:

| Variable | Description |
|----------|-------------|
| `X_CLIENT_ID` | OAuth 2.0 Client ID (from app’s “Keys and tokens”) |
| `X_CALLBACK_BASE_URL` | Base URL for callback (e.g. `https://abc123.ngrok-free.app` or `https://yourdomain.com`) — no trailing slash |

Optional (for token exchange from a server):

| Variable | Description |
|----------|-------------|
| `X_CLIENT_SECRET` | Only if your app type has a client secret (e.g. Web App). Not used for public PKCE-only clients. |

The callback server builds `redirect_uri` as: `{X_CALLBACK_BASE_URL}/x/callback`.

---

## Quick test (tunnel)

```bash
# Terminal 1: run callback server
cd /Users/jcore/Desktop/Openclaw
python3 tools/x_oauth_callback_server.py --port 8765

# Terminal 2: expose with ngrok
ngrok http 8765
# Copy the https://....ngrok-free.app URL

# Add in X portal: https://....ngrok-free.app/x/callback
# In .env: X_CALLBACK_BASE_URL=https://....ngrok-free.app

# Browser: open https://....ngrok-free.app/x/start
# Authorize → you’re redirected back and tokens are saved
```
