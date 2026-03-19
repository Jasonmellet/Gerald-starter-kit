# X API — Manage Posts (Reference)

## How do I reply to a post using the X API?

To reply to a post with the X API v2, you **create a new Post** and include a `reply` object pointing at the original Post ID.

**Endpoint:** `POST /2/tweets` ([docs.x.com](https://docs.x.com))

**Payload (reply):**
```json
{
  "text": "Thanks for the update!",
  "reply": {
    "in_reply_to_tweet_id": "1234567890"
  }
}
```

**Minimal cURL:**
```bash
curl -X POST "https://api.x.com/2/tweets" \
  -H "Authorization: Bearer $USER_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Thanks for the update!","reply":{"in_reply_to_tweet_id":"1234567890"}}'
```

**Notes:**
- You need a **user access token** (OAuth 1.0a or OAuth 2.0 user context) with write permissions.
- `in_reply_to_tweet_id` must be the numeric ID of the post you’re replying to.

**API reply policy (self-serve tiers):** X restricts who can reply via the API. A 403 *"Reply to this conversation is not allowed because you have not been mentioned or otherwise engaged by the author"* means replies are only allowed when **the post author** has **mentioned** your account or **quoted** a post from your account. Replying from the web to someone else’s post does **not** satisfy this; the **author** must have engaged **you**. This applies to Free, Basic, Pro, and Pay-per-use; Enterprise is not restricted. See [Update to Reply Behavior in X API v2](https://devcommunity.x.com/t/update-to-reply-behavior-in-x-api-v2-restricting-programmatic-replies/257909).

---

## 1. Documentation Index

Fetch the complete documentation index at: **https://docs.x.com/llms.txt**

Use this file to discover all available pages before exploring further.

---

## Manage Posts

Create and delete Posts on behalf of authenticated users.

The Manage Posts endpoints let you create and delete Posts on behalf of authenticated users. Build applications that post content, create threads, or manage user Posts.

### Overview

- **Create Post** — Publish a new Post
- **Delete Post** — Delete an existing Post
- **Reply** — Reply to another Post
- **Quote** — Quote another Post

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/2/tweets` | Create a new Post |
| DELETE | `/2/tweets/:id` | Delete a Post |

---

## Creating Posts

### Basic Post

```bash
curl -X POST "https://api.x.com/2/tweets" \
  -H "Authorization: Bearer $USER_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from the API!"}'
```

### Reply to a Post

```bash
curl -X POST "https://api.x.com/2/tweets" \
  -H "Authorization: Bearer $USER_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This is a reply!",
    "reply": {
      "in_reply_to_tweet_id": "1234567890"
    }
  }'
```

### Quote a Post

```bash
curl -X POST "https://api.x.com/2/tweets" \
  -H "Authorization: Bearer $USER_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Check this out!",
    "quote_tweet_id": "1234567890"
  }'
```

### Post with media

```bash
curl -X POST "https://api.x.com/2/tweets" \
  -H "Authorization: Bearer $USER_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Photo of the day",
    "media": {
      "media_ids": ["1234567890123456789"]
    }
  }'
```

Upload media first using the Media Upload endpoint, then reference the `media_id` in your Post.

### Post with poll

```bash
curl -X POST "https://api.x.com/2/tweets" \
  -H "Authorization: Bearer $USER_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is your favorite color?",
    "poll": {
      "options": ["Red", "Blue", "Green", "Yellow"],
      "duration_minutes": 1440
    }
  }'
```

---

## Deleting Posts

```bash
curl -X DELETE "https://api.x.com/2/tweets/1234567890" \
  -H "Authorization: Bearer $USER_ACCESS_TOKEN"
```

**Note:** You can only delete Posts authored by the authenticated user.

---

## Getting started

**Prerequisites**

- An approved [developer account](https://developer.x.com/en/portal/petition/essential/basic-info)
- A Project and App in the Developer Console
- User Access Tokens via [OAuth 2.0 PKCE](https://developer.x.com/en/docs/authentication/oauth-2-0/oauth-2-0-authorization-code-flow-with-pkce) or [3-legged OAuth](https://developer.x.com/en/docs/authentication/oauth-1-0a/obtaining-access-tokens)

**Further reading**

- [Quickstart](https://docs.x.com/llms.txt) — Create your first Post
- Integration guide — Key concepts and best practices
- Media upload — Upload media for Posts
- API Reference — Full endpoint documentation

---

## What is a “user access token”?

It’s the token that means **“post as this specific X account.”** The API uses it in the `Authorization: Bearer <token>` header when creating or replying to posts.

- **Not** the same as your API Key / Secret (those identify the *app*).
- **Not** the same as the read-only Bearer token (that one is for app-level read access).
- It’s the result of **someone logging into X and authorizing your app** to act on their behalf. So “user” = the X account that will post.

### How do you get one?

You have to run an **OAuth 2.0 flow** (e.g. PKCE):

1. Your app sends the user to X’s login/authorize page (with your app’s Client ID, redirect URL, scopes like `tweet.write`).
2. The user logs in and approves.
3. X redirects back to your app with a short-lived **authorization code**.
4. Your app exchanges that code (with your Client Secret) for an **access token** (and optionally a refresh token). That access token is the **user access token** you put in `X_USER_ACCESS_TOKEN`.

So you don’t “look it up” in the developer portal; you get it once by doing the login flow, then you copy that token into `.env` (and refresh it when it expires, if you use refresh tokens).

**Docs:** [OAuth 2.0 overview](https://docs.x.com/fundamentals/authentication/oauth-2-0/overview), [User access token (PKCE)](https://docs.x.com/resources/fundamentals/authentication/oauth-2-0/user-access-token). Your app’s Client ID and Client Secret are under the app’s “Keys and tokens” in the [Developer Portal](https://developer.x.com/en/portal/dashboard).
