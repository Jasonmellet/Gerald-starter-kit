from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


class AIHelper:
    """
    Optional helper. If unavailable or malformed output is returned, caller should fall back.
    """

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def _load_prompt(self, prompt_name: str) -> Optional[str]:
        prompt_path = Path(__file__).resolve().parent / "prompts" / prompt_name
        if not prompt_path.exists():
            return None
        try:
            return prompt_path.read_text(encoding="utf-8")
        except Exception:
            return None

    def _chat_json(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        if not self.enabled or not self.api_key:
            return None
        try:
            import requests  # type: ignore[import]
        except Exception:
            return None

        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
        }
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            if resp.status_code < 200 or resp.status_code >= 300:
                return None
            data = resp.json()
            content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
            if not content:
                return None
            return json.loads(content)
        except Exception:
            return None

    def _validate_content_payload(self, data: Dict[str, Any], expected_count: int) -> Optional[Dict[str, Any]]:
        topic = str(data.get("topic", "")).strip()
        posts = data.get("posts")
        top_3 = data.get("top_3_final")
        if not topic or not isinstance(posts, list) or not isinstance(top_3, list):
            return None
        if len(posts) < expected_count:
            return None

        normalized_posts: List[Dict[str, Any]] = []
        for row in posts[:expected_count]:
            if not isinstance(row, dict):
                return None
            text = str(row.get("text", "")).strip()
            reasoning = str(row.get("reasoning", "")).strip()
            scores = row.get("scores", {})
            if not text or not isinstance(scores, dict):
                return None

            hs = _coerce_int(scores.get("hook_strength"))
            sp = _coerce_int(scores.get("specificity"))
            au = _coerce_int(scores.get("authority"))
            ep = _coerce_int(scores.get("engagement_potential"))
            ic = _coerce_int(scores.get("icp_fit"))
            total = _coerce_int(scores.get("total"), hs + sp + au + ep + ic)

            normalized_posts.append(
                {
                    "text": text,
                    "reasoning": reasoning,
                    "scores": {
                        "hook_strength": hs,
                        "specificity": sp,
                        "authority": au,
                        "engagement_potential": ep,
                        "icp_fit": ic,
                        "total": total,
                    },
                }
            )

        normalized_top3: List[Dict[str, str]] = []
        for row in top_3[:3]:
            if not isinstance(row, dict):
                continue
            text = str(row.get("text", "")).strip()
            why = str(row.get("why_it_should_work", "")).strip()
            if text:
                normalized_top3.append({"text": text, "why_it_should_work": why})
        if len(normalized_top3) < 3:
            # If model missed this, derive from top scored posts.
            sorted_posts = sorted(normalized_posts, key=lambda p: int(p["scores"]["total"]), reverse=True)
            normalized_top3 = [
                {
                    "text": p["text"],
                    "why_it_should_work": p.get("reasoning", "") or "High specificity and strong ICP resonance.",
                }
                for p in sorted_posts[:3]
            ]

        return {"topic": topic, "posts": normalized_posts, "top_3_final": normalized_top3}

    def generate_topic_posts(
        self,
        topic: str,
        audience: str,
        business_pain: str,
        research_insights: str,
        candidate_count: int = 10,
    ) -> Optional[Dict[str, Any]]:
        prompt_tpl = self._load_prompt("content_intel_post_generator.txt")
        if not prompt_tpl:
            return None
        system_prompt = (
            "You are a senior operator-focused content strategist. "
            "Return only valid JSON. Do not add markdown fences."
        )
        user_prompt = (
            prompt_tpl.replace("{{CANDIDATE_COUNT}}", str(candidate_count))
            .replace("{{TOPIC}}", topic)
            .replace("{{AUDIENCE}}", audience)
            .replace("{{PAIN}}", business_pain)
            .replace("{{INSIGHTS}}", research_insights or "- No insights provided.")
        )
        raw = self._chat_json(system_prompt, user_prompt)
        if not raw:
            return None
        return self._validate_content_payload(raw, expected_count=candidate_count)

    def improve_post(self, text: str, context: Optional[Dict[str, str]] = None) -> Optional[str]:
        if not self.enabled:
            return None
        context = context or {}
        tightened = text.strip()
        if len(tightened) > 275:
            tightened = tightened[:272].rstrip() + "..."
        if "Most SMBs" not in tightened and context.get("topic"):
            tightened = f"{tightened}\n\n({context['topic']} operator note)"
        return tightened

    def classify_reply_hint(self, reply_text: str) -> Optional[str]:
        if not self.enabled or not self.api_key:
            return None
        body = reply_text.lower()
        if "help" in body or "struggle" in body:
            return "public_reply_dm"
        if len(body.strip()) < 8:
            return "ignore"
        return "public_reply_only"

