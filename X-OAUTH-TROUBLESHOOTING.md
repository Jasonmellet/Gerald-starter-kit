# X OAuth: "You weren't able to give access to the App"

This error usually means the app is not allowed to request the permissions (scopes) you're asking for.

## 1. Enable Direct Messages in the Developer Portal

To use **dm.read** / **dm.write** (for sending DMs), the app must have DM access turned on:

1. Go to **[X Developer Portal](https://developer.x.com)** → **Projects & Apps** → select your **project** → select your **app**.
2. Open **Settings** (or **User authentication settings**).
3. Under **App permissions** (or **Type of App** / **Access level**), set:
   - **Read and write and Direct Messages** (the option that explicitly includes Direct Messages).
4. If you see **OAuth 2.0 scopes**, ensure **dm.read** and **dm.write** are enabled/checked.
5. **Save** and try the OAuth flow again: open **https://gerald-says-hi.ngrok.io/x/start**, log in, and authorize.

## 2. Try without DM first (to confirm the flow works)

If you're not sure whether the problem is DM or something else (e.g. callback URL):

1. In your **.env** file add a temporary line so we don't request DM:
   ```
   X_OAUTH_SCOPES=tweet.read users.read offline.access
   ```
2. Restart the callback server (stop it and run `python3 tools/x_oauth_callback_server.py --port 8766` again).
3. Open **https://gerald-says-hi.ngrok.io/x/start** and authorize again.
4. If that **succeeds**, the issue is the app's DM permission. Follow step 1 above to enable **Read and write and Direct Messages**, then **remove** the `X_OAUTH_SCOPES` line from `.env`, restart the server, and run `/x/start` again to get tokens with DM.

## 3. Callback URL must match exactly

In the app's **Callback URI / Redirect URL** list you must have exactly:

```
https://gerald-says-hi.ngrok.io/x/callback
```

No trailing slash. Same protocol (https) and host as in your `.env` `X_CALLBACK_BASE_URL`.
