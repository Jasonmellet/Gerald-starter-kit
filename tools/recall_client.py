"""
Recall.ai API Client for OpenClaw
Handles bot creation, meeting joining, and transcript retrieval.
"""

import os
import json
import time
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime


class RecallAIClient:
    """Client for interacting with Recall.ai API."""

    BASE_URL = "https://us-west-2.recall.ai/api/v1"  # Regional endpoint for this API key

    @staticmethod
    def _load_env_file(filepath: str = ".env") -> Dict[str, str]:
        """Load environment variables from a .env file."""
        env_vars = {}
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except FileNotFoundError:
            pass
        return env_vars

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key from parameter, env, or .env file."""
        if api_key:
            self.api_key = api_key.strip()
        else:
            # Try environment first, then .env file
            env_key = os.getenv("RECALL_API_KEY", "").strip()
            if env_key and not env_key.startswith("your_"):
                self.api_key = env_key
            else:
                # Load from .env file directly
                env_vars = self._load_env_file()
                self.api_key = env_vars.get("RECALL_API_KEY", "").strip()

        if not self.api_key or self.api_key.startswith("your_"):
            raise ValueError("RECALL_API_KEY not found in environment or .env file")
        # Recall.ai expects: Authorization: Token <api_key>
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def create_bot(self, meeting_url: str, name: str = "Gerald", transcription: bool = False) -> Dict[str, Any]:
        """
        Create a bot to join a meeting.
        
        Args:
            meeting_url: The meeting URL (Zoom, Google Meet, Teams, etc.)
            name: Display name for the bot in the meeting
            transcription: Whether to enable transcription (requires AssemblyAI credentials)
            
        Returns:
            Bot object with id, status, etc.
        """
        payload = {
            "meeting_url": meeting_url,
            "bot_name": name
        }
        
        # Only add transcription if explicitly requested and credentials are configured
        if transcription:
            payload["transcription_options"] = {
                "provider": "assembly_ai"
            }
        
        response = requests.post(
            f"{self.BASE_URL}/bot",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    @staticmethod
    def _current_status(bot: Dict[str, Any]) -> str:
        """Derive current status from status_changes (Recall API has no top-level status)."""
        changes = bot.get("status_changes") or []
        if not changes:
            return "unknown"
        return (changes[-1].get("code") or "unknown").lower()

    def get_bot(self, bot_id: str) -> Dict[str, Any]:
        """Get bot status and details. Adds computed 'status' from last status_changes event."""
        response = requests.get(
            f"{self.BASE_URL}/bot/{bot_id}",
            headers=self.headers
        )
        response.raise_for_status()
        data = response.json()
        data["status"] = self._current_status(data)
        return data
    
    def list_bots(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all bots. Adds computed 'status' from last status_changes event."""
        params = {}
        if status:
            params["status"] = status
        response = requests.get(
            f"{self.BASE_URL}/bot",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        for bot in results:
            bot["status"] = self._current_status(bot)
        return results
    
    def get_transcript(self, bot_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get transcript for a completed bot session.
        
        Returns:
            List of transcript segments with speaker and text,
            or None if transcript not ready.
        """
        bot = self.get_bot(bot_id)
        
        # Check if bot has finished and has transcript
        if bot.get("status") != "done":
            return None
        
        # Get transcript via the transcript endpoint
        response = requests.get(
            f"{self.BASE_URL}/bot/{bot_id}/transcript",
            headers=self.headers
        )
        
        if response.status_code == 404:
            return None
            
        response.raise_for_status()
        return response.json()
    
    def wait_for_completion(self, bot_id: str, timeout: int = 3600, poll_interval: int = 30) -> bool:
        """
        Poll until bot completes or times out.
        
        Args:
            bot_id: The bot ID to monitor
            timeout: Max seconds to wait
            poll_interval: Seconds between polls
            
        Returns:
            True if completed successfully, False if timeout or error
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            bot = self.get_bot(bot_id)
            status = bot.get("status")
            
            if status == "done":
                return True
            elif status in ["failed", "kicked", "left"]:
                print(f"Bot ended with status: {status}")
                return False
            
            time.sleep(poll_interval)
        
        print(f"Timeout waiting for bot {bot_id}")
        return False
    
    def leave_call(self, bot_id: str) -> bool:
        """Tell the bot to leave the call immediately. Frees the slot once it ends."""
        try:
            response = requests.post(
                f"{self.BASE_URL}/bot/{bot_id}/leave_call/",
                headers=self.headers,
            )
            return response.status_code == 200
        except Exception:
            return False

    def delete_bot(self, bot_id: str) -> bool:
        """Delete a bot and clean up resources. Recall may only allow delete for bots that have not yet joined."""
        try:
            response = requests.delete(
                f"{self.BASE_URL}/bot/{bot_id}",
                headers=self.headers
            )
            if response.status_code != 204:
                # Recall often returns 405 for bots that already joined/completed
                return False
            return True
        except Exception:
            return False


def test_connection():
    """Quick test to verify API key works."""
    try:
        client = RecallAIClient()
        bots = client.list_bots()
        print(f"✓ Recall.ai connection successful. Found {len(bots)} existing bots.")
        return True
    except Exception as e:
        print(f"✗ Recall.ai connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()
