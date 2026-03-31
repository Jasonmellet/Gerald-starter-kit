"""
Recall.ai API client. Bot creation, transcript retrieval.
"""
import os
import time
import requests
from typing import Optional, Dict, Any, List


class RecallAIClient:
    BASE_URL = "https://us-west-2.recall.ai/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            self.api_key = api_key.strip()
        else:
            self.api_key = (os.getenv("RECALL_API_KEY") or "").strip()
        if not self.api_key or self.api_key.startswith("your_"):
            raise ValueError("RECALL_API_KEY not set or invalid")
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

    def create_bot(self, meeting_url: str, name: str = "Notetaker", transcription: bool = True) -> Dict[str, Any]:
        payload = {"meeting_url": meeting_url, "bot_name": name}
        if transcription:
            payload["recording_config"] = {
                "transcript": {
                    "provider": {
                        "recallai_streaming": {"mode": "prioritize_accuracy"}
                    }
                }
            }
        r = requests.post(f"{self.BASE_URL}/bot", headers=self.headers, json=payload)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _current_status(bot: Dict[str, Any]) -> str:
        changes = bot.get("status_changes") or []
        if not changes:
            return "unknown"
        return (changes[-1].get("code") or "unknown").lower()

    def get_bot(self, bot_id: str) -> Dict[str, Any]:
        r = requests.get(f"{self.BASE_URL}/bot/{bot_id}", headers=self.headers)
        r.raise_for_status()
        data = r.json()
        data["status"] = self._current_status(data)
        return data

    def list_bots(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {} if not status else {"status": status}
        r = requests.get(f"{self.BASE_URL}/bot", headers=self.headers, params=params)
        r.raise_for_status()
        results = r.json().get("results", [])
        for bot in results:
            bot["status"] = self._current_status(bot)
        return results

    def get_transcript(self, bot_id: str) -> Optional[List[Dict[str, Any]]]:
        bot = self.get_bot(bot_id)
        if bot.get("status") != "done":
            return None
        recordings = bot.get("recordings") or []
        if not recordings:
            print("  [Recall] No recordings on bot")
            return None
        media = recordings[0].get("media_shortcuts") or {}
        transcript_artifact = media.get("transcript")
        if not isinstance(transcript_artifact, dict):
            print("  [Recall] No transcript in media_shortcuts")
            return None
        download_url = (transcript_artifact.get("data") or {}).get("download_url")
        if not download_url:
            tid = transcript_artifact.get("id")
            if not tid:
                return None
            resp = requests.get(f"{self.BASE_URL}/transcript/{tid}/", headers=self.headers)
            if resp.status_code != 200:
                return None
            download_url = (resp.json().get("data") or {}).get("download_url")
        if not download_url:
            return None
        down = requests.get(download_url)
        down.raise_for_status()
        raw = down.json()
        if not isinstance(raw, list):
            return None
        segments = []
        for item in raw:
            participant = item.get("participant") or {}
            name = participant.get("name") or "Unknown"
            words = item.get("words") or []
            text = " ".join(w.get("text", "") for w in words).strip()
            if text:
                segments.append({"speaker": name, "text": text})
        return segments if segments else None

    def delete_bot(self, bot_id: str) -> bool:
        try:
            r = requests.delete(f"{self.BASE_URL}/bot/{bot_id}", headers=self.headers)
            return r.status_code == 204
        except Exception:
            return False
