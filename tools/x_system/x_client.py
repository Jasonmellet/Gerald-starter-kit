from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode


def load_env() -> None:
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    os.environ.setdefault(key, val)


@dataclass(frozen=True)
class OAuth1Creds:
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str


class XClientError(Exception):
    pass


class XClient:
    def __init__(self) -> None:
        load_env()
        self.base_url = "https://api.x.com/2"
        self.bearer_token = os.environ.get("X_BEARER_TOKEN")
        self.oauth1 = self._load_oauth1()

    def _load_oauth1(self) -> OAuth1Creds:
        api_key = os.environ.get("X_API_KEY") or os.environ.get("x_api_key")
        api_secret = os.environ.get("X_API_SECRET") or os.environ.get("x_api_secret")
        access_token = os.environ.get("X_ACCESS_TOKEN") or os.environ.get("x_access_token")
        access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET") or os.environ.get("x_access_token_secret")
        if not all([api_key, api_secret, access_token, access_token_secret]):
            raise XClientError("Missing OAuth1 credentials in .env")
        return OAuth1Creds(
            api_key=api_key,  # type: ignore[arg-type]
            api_secret=api_secret,  # type: ignore[arg-type]
            access_token=access_token,  # type: ignore[arg-type]
            access_token_secret=access_token_secret,  # type: ignore[arg-type]
        )

    def _oauth1_post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import requests  # type: ignore[import]
            from requests_oauthlib import OAuth1  # type: ignore[import]
        except Exception as exc:
            raise XClientError("Missing requests/requests_oauthlib dependencies") from exc

        auth = OAuth1(
            self.oauth1.api_key,
            self.oauth1.api_secret,
            self.oauth1.access_token,
            self.oauth1.access_token_secret,
        )
        resp = requests.post(
            f"{self.base_url}{endpoint}",
            json=payload,
            auth=auth,
            timeout=15,
            headers={"Content-Type": "application/json", "User-Agent": "OpenClawXSystem/0.1"},
        )
        return self._parse_response(resp.status_code, resp.text)

    def _oauth1_delete(self, endpoint: str) -> Dict[str, Any]:
        try:
            import requests  # type: ignore[import]
            from requests_oauthlib import OAuth1  # type: ignore[import]
        except Exception as exc:
            raise XClientError("Missing requests/requests_oauthlib dependencies") from exc

        auth = OAuth1(
            self.oauth1.api_key,
            self.oauth1.api_secret,
            self.oauth1.access_token,
            self.oauth1.access_token_secret,
        )
        resp = requests.delete(
            f"{self.base_url}{endpoint}",
            auth=auth,
            timeout=15,
            headers={"User-Agent": "OpenClawXSystem/0.1"},
        )
        return self._parse_response(resp.status_code, resp.text)

    def _bearer_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.bearer_token:
            raise XClientError("X_BEARER_TOKEN missing in .env")

        import urllib.request

        url = f"{self.base_url}{endpoint}"
        if params:
            url = f"{url}?{urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self.bearer_token}", "User-Agent": "OpenClawXSystem/0.1"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            raise XClientError(str(exc)) from exc

    @staticmethod
    def _parse_response(status_code: int, text: str) -> Dict[str, Any]:
        try:
            data = json.loads(text) if text else {}
        except ValueError:
            data = {"raw": text}
        if not (200 <= status_code < 300):
            raise XClientError(f"X API error {status_code}: {text}")
        return data

    # ---- read endpoints ----
    def search_recent(self, query: str, max_results: int = 50) -> Dict[str, Any]:
        return self._bearer_get(
            "/tweets/search/recent",
            {
                "query": query,
                "max_results": str(min(max_results, 100)),
                "tweet.fields": "created_at,author_id,public_metrics,conversation_id,in_reply_to_user_id",
                "expansions": "author_id",
                "user.fields": "username,name,verified,description",
            },
        )

    def get_user_by_username(self, username: str) -> Dict[str, Any]:
        return self._bearer_get(
            f"/users/by/username/{username.lstrip('@')}",
            {"user.fields": "created_at,public_metrics,verified,description"},
        )

    def get_user_tweets(self, user_id: str, max_results: int = 10) -> Dict[str, Any]:
        return self._bearer_get(
            f"/users/{user_id}/tweets",
            {"max_results": str(min(max_results, 100)), "tweet.fields": "created_at,public_metrics"},
        )

    def get_tweet(self, tweet_id: str) -> Dict[str, Any]:
        return self._bearer_get(
            f"/tweets/{tweet_id}",
            {"tweet.fields": "created_at,author_id,conversation_id,in_reply_to_user_id,public_metrics"},
        )

    def search_replies(self, tweet_id: str, max_results: int = 50) -> List[Dict[str, Any]]:
        payload = self.search_recent(f"conversation_id:{tweet_id} is:reply", max_results=max_results)
        return payload.get("data", []) or []

    # ---- write endpoints (OAuth1 only) ----
    def create_post(self, text: str) -> Dict[str, Any]:
        return self._oauth1_post("/tweets", {"text": text})

    def delete_post(self, tweet_id: str) -> Dict[str, Any]:
        return self._oauth1_delete(f"/tweets/{tweet_id}")

    def reply_to_tweet(self, in_reply_to_tweet_id: str, text: str) -> Dict[str, Any]:
        return self._oauth1_post(
            "/tweets",
            {
                "text": text,
                "reply": {
                    "in_reply_to_tweet_id": in_reply_to_tweet_id,
                    "auto_populate_reply_metadata": True,
                },
            },
        )

    def send_dm(self, recipient_user_id: str, text: str) -> Dict[str, Any]:
        return self._oauth1_post(f"/dm_conversations/with/{recipient_user_id}/messages", {"text": text})

