from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
import time

from ..config import get_settings
from ..logging import get_logger


logger = get_logger(__name__)


class XClientError(Exception):
    """Base error for X client issues."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ) -> None:
        if response_body:
            message = f"{message}\n{response_body}"
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class XClientRateLimitError(XClientError):
    """Raised when X responds with 429 after retries."""


class XClientNotFoundError(XClientError):
    """Raised when X responds with 404 for a resource."""


class XClient:
    """
    Minimal X (Twitter) API client focused on read workflows.

    This client assumes bearer-token auth for v2 APIs. It can be extended to
    support OAuth 1.1 or additional endpoints as needed.
    """

    def __init__(self, *, timeout: float = 10.0) -> None:
        settings = get_settings()
        if not settings.x_bearer_token:
            raise XClientError("X_BEARER_TOKEN is not configured in the environment.")

        self._base_url = "https://api.x.com/2"
        # Many environments still use api.twitter.com; adjust if necessary.
        self._fallback_base_url = "https://api.twitter.com/2"
        self._headers = {
            "Authorization": f"Bearer {settings.x_bearer_token}",
            "User-Agent": "GeraldXClient/0.1",
        }
        self._client = httpx.Client(timeout=timeout, headers=self._headers)

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform an HTTP request with basic retry / backoff for 429s.
        """

        url = f"{self._base_url}{path}"
        max_retries = 2
        base_delay = 1.0

        for attempt in range(max_retries + 1):
            try:
                resp = self._client.request(method, url, params=params)
                if resp.status_code == 404 and "api.x.com" in url:
                    # Fallback for older hosts
                    url = f"{self._fallback_base_url}{path}"
                    resp = self._client.request(method, url, params=params)
            except httpx.RequestError as exc:
                logger.error("X API request failed", extra={"path": path, "error": str(exc)})
                raise XClientError(f"Request failed: {exc}") from exc

            if resp.status_code == 429:
                if attempt < max_retries:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        "X API rate limited (429), backing off",
                        extra={"path": path, "attempt": attempt, "delay": delay},
                    )
                    time.sleep(delay)
                    continue
                logger.error("X API rate limit persisted after retries", extra={"path": path})
                raise XClientRateLimitError("Rate limited by X (429)", status_code=429)

            if resp.status_code == 404:
                logger.warning("X resource not found (404)", extra={"path": path})
                raise XClientNotFoundError("Resource not found", status_code=404)

            if resp.status_code >= 400:
                logger.error(
                    "X API error",
                    extra={"path": path, "status_code": resp.status_code, "body": resp.text},
                )
                raise XClientError(f"X API returned {resp.status_code}: {resp.text}", status_code=resp.status_code)

            return resp.json()

        # Should not reach here
        raise XClientError("Unexpected X client state")

    def search_recent_posts(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """
        Search recent posts (tweets) matching a query and return both tweets
        and a mapping of author_id -> user profile (when available).
        """

        params = {
            "query": query,
            "max_results": max(10, min(limit, 100)),
            "tweet.fields": "author_id,created_at,public_metrics",
            "expansions": "author_id",
            "user.fields": "created_at,description,location,entities,public_metrics,username,name",
        }
        data = self._request("GET", "/tweets/search/recent", params=params)
        tweets = data.get("data", []) or []
        includes = data.get("includes", {}) or {}
        users = includes.get("users", []) or []
        users_by_id = {u.get("id"): u for u in users if u.get("id")}
        return {"tweets": tweets, "users_by_id": users_by_id}

    def get_tweet(self, tweet_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single tweet by ID. Returns dict with id, text, etc., or None if not found.
        """
        params = {"tweet.fields": "author_id,created_at,public_metrics,text"}
        try:
            data = self._request("GET", f"/tweets/{tweet_id}", params=params)
            return data.get("data")
        except XClientNotFoundError:
            return None

    def get_user_by_handle(self, handle: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a user profile by handle (username).
        """

        params = {
            "user.fields": "created_at,description,location,entities,public_metrics",
        }
        data = self._request("GET", f"/users/by/username/{handle.lstrip('@')}", params=params)
        return data.get("data")

    def get_user_posts(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch recent posts for a given user id.
        """

        params = {
            "max_results": max(5, min(limit, 100)),
            "tweet.fields": "author_id,created_at,public_metrics,text",
        }
        data = self._request("GET", f"/users/{user_id}/tweets", params=params)
        return data.get("data", [])

    def get_users_bulk(self, user_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch multiple users by id in bulk, if supported.
        """

        if not user_ids:
            return []
        params = {
            "ids": ",".join(user_ids),
            "user.fields": "created_at,description,location,entities,public_metrics",
        }
        data = self._request("GET", "/users", params=params)
        return data.get("data", [])

    def send_direct_message(self, recipient_user_id: str, text: str) -> Dict[str, Any]:
        """
        Send a direct message via X API v2 only.

        Uses POST /2/dm_conversations/with/{participant_id}/messages with OAuth 1.0a
        user-context (x_api_key, x_api_secret, x_access_token, x_access_token_secret).
        On success returns { ok, status_code, external_message_id, raw }.
        On failure raises XClientError with optional response_body for persistence.
        """
        settings = get_settings()
        api_key = settings.x_api_key
        api_secret = settings.x_api_secret
        access_token = settings.x_access_token
        access_token_secret = settings.x_access_token_secret

        if not all([api_key, api_secret, access_token, access_token_secret]):
            logger.warning(
                "DM sending not configured: missing one or more X OAuth credentials",
                extra={"has_api_key": bool(api_key), "has_access_token": bool(access_token)},
            )
            raise XClientError("DM sending not configured (missing OAuth credentials)")

        try:
            import requests  # type: ignore[import]
            from requests_oauthlib import OAuth1  # type: ignore[import]
        except Exception as exc:  # pragma: no cover - environment-specific
            logger.error(
                "DM sending unavailable: requests/requests_oauthlib not installed",
                extra={"error": str(exc)},
            )
            raise XClientError(
                "DM API not available: install 'requests' and 'requests_oauthlib' to enable DM sending"
            ) from exc

        url = f"https://api.x.com/2/dm_conversations/with/{recipient_user_id}/messages"
        payload: Dict[str, Any] = {"text": text}
        auth = OAuth1(api_key, api_secret, access_token, access_token_secret)

        try:
            resp = requests.post(
                url,
                json=payload,
                auth=auth,
                timeout=10,
                headers={"Content-Type": "application/json"},
            )
        except Exception as exc:
            raise XClientError(f"DM send request failed: {exc}") from exc

        status_code = resp.status_code
        raw_text = resp.text
        try:
            data = resp.json()
        except ValueError:
            data = {"raw": raw_text}

        if not (200 <= status_code < 300):
            logger.error(
                "X DM API error",
                extra={"status_code": status_code, "body": raw_text},
            )
            if status_code in (401, 403):
                raise XClientError(
                    "X DM API auth or scope error (401/403). Check app permissions and user-context tokens.",
                    status_code=status_code,
                    response_body=raw_text,
                )
            raise XClientError(
                f"DM API returned {status_code}: {raw_text}",
                status_code=status_code,
                response_body=raw_text,
            )

        inner = (data or {}).get("data") or {}
        external_id = inner.get("dm_event_id")

        return {
            "ok": True,
            "status_code": status_code,
            "external_message_id": external_id,
            "raw": data,
        }

    def create_reply(self, in_reply_to_tweet_id: str, text: str) -> Dict[str, Any]:
        """
        Post a reply to a tweet via X API v2.

        Uses Bearer (OAuth 2.0 user access token) when X_USER_ACCESS_TOKEN is set;
        otherwise OAuth 1.0a. Doc: POST /2/tweets with Authorization: Bearer $USER_ACCESS_TOKEN.
        Returns {"ok": True, "tweet_id": data.id, "raw": data}. Raises XClientError on failure.
        """
        settings = get_settings()
        # Official spec: docs.x.com/x-api/posts/create-post — reply includes auto_populate_reply_metadata
        payload: Dict[str, Any] = {
            "text": text,
            "reply": {
                "in_reply_to_tweet_id": in_reply_to_tweet_id,
                "auto_populate_reply_metadata": True,
            },
        }
        headers = {"Content-Type": "application/json"}

        def _post_reply(post_url: str):  # noqa: B902
            user_token = (settings.x_user_access_token or "").strip()
            if user_token:
                headers["Authorization"] = f"Bearer {user_token}"
                return self._client.post(post_url, json=payload, timeout=10)
            api_key = settings.x_api_key
            api_secret = settings.x_api_secret
            access_token = settings.x_access_token
            access_token_secret = settings.x_access_token_secret
            if not all([api_key, api_secret, access_token, access_token_secret]):
                raise XClientError(
                    "Reply not configured: set X_USER_ACCESS_TOKEN (Bearer) or OAuth 1.0a credentials"
                )
            try:
                import requests  # type: ignore[import]
                from requests_oauthlib import OAuth1  # type: ignore[import]
            except Exception as exc:
                raise XClientError(
                    "Tweet API not available: install 'requests' and 'requests_oauthlib'"
                ) from exc
            auth = OAuth1(api_key, api_secret, access_token, access_token_secret)
            return requests.post(post_url, json=payload, auth=auth, timeout=10, headers=headers)

        url = "https://api.x.com/2/tweets"
        try:
            resp = _post_reply(url)
        except Exception as exc:
            raise XClientError(f"Reply request failed: {exc}") from exc
        # If X returns 403 "not allowed" on api.x.com, try legacy host (some OAuth 1.0a flows use it)
        if resp.status_code == 403 and resp.text and "not allowed" in resp.text:
            url = "https://api.twitter.com/2/tweets"
            try:
                resp = _post_reply(url)
            except Exception as exc:
                raise XClientError(f"Reply request failed: {exc}") from exc

        status_code = resp.status_code
        raw_text = resp.text
        try:
            data = resp.json()
        except ValueError:
            data = {"raw": raw_text}

        if not (200 <= status_code < 300):
            logger.error(
                "X reply API error",
                extra={"status_code": status_code, "body": raw_text},
            )
            if status_code == 403 and raw_text and "not allowed" in raw_text and "mentioned or otherwise engaged" in raw_text:
                raise XClientError(
                    "X API reply policy: replies are only allowed when the post author has mentioned or quoted your account (self-serve tier restriction). See docs/reference/x-api-manage-posts.md.",
                    status_code=status_code,
                    response_body=raw_text,
                )
            if status_code in (401, 403):
                raise XClientError(
                    "X tweet/reply API auth or scope error (401/403). Check app has Read and write for Tweets.",
                    status_code=status_code,
                    response_body=raw_text,
                )
            raise XClientError(
                f"Reply API returned {status_code}: {raw_text}",
                status_code=status_code,
                response_body=raw_text,
            )

        inner = (data or {}).get("data") or {}
        tweet_id = inner.get("id")

        return {
            "ok": True,
            "status_code": status_code,
            "tweet_id": tweet_id,
            "raw": data,
        }


