from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.anthropic_final_model = os.environ.get("ANTHROPIC_PERFORMANCE_MODEL", "claude-opus-4-6")

    def _load_prompt(self, prompt_name: str) -> Optional[str]:
        prompt_path = Path(__file__).resolve().parent / "prompts" / prompt_name
        if not prompt_path.exists():
            return None
        try:
            return prompt_path.read_text(encoding="utf-8")
        except Exception:
            return None

    def _chat_json(self, system_prompt: str, user_prompt: str) -> Tuple[Optional[Dict[str, Any]], str]:
        if not self.enabled:
            return None, "disabled"
        if not self.api_key:
            return None, "missing_api_key"
        try:
            import requests  # type: ignore[import]
        except Exception:
            return None, "missing_requests_dependency"

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
                return None, f"http_{resp.status_code}"
            data = resp.json()
            content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
            if not content:
                return None, "empty_model_content"
            return json.loads(content), "ok"
        except Exception:
            return None, "request_or_json_exception"

    @staticmethod
    def _extract_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
        text = (raw_text or "").strip()
        if not text:
            return None
        # Remove markdown fences if model adds them.
        text = text.replace("```json", "```")
        if text.startswith("```") and text.endswith("```"):
            text = text[3:-3].strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        # Fallback: first {...} object in response.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    def _anthropic_json(self, system_prompt: str, user_prompt: str) -> Tuple[Optional[Dict[str, Any]], str]:
        if not self.enabled:
            return None, "disabled"
        if not self.anthropic_api_key:
            return None, "missing_anthropic_api_key"
        try:
            import requests  # type: ignore[import]
        except Exception:
            return None, "missing_requests_dependency"

        payload = {
            "model": self.anthropic_final_model,
            "max_tokens": 1200,
            "temperature": 0.2,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
                timeout=45,
            )
            if resp.status_code < 200 or resp.status_code >= 300:
                return None, f"http_{resp.status_code}"
            data = resp.json()
            blocks = data.get("content") or []
            text_parts = []
            for block in blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(str(block.get("text", "")))
            parsed = self._extract_json_object("\n".join(text_parts))
            if not parsed:
                return None, "invalid_json_payload"
            return parsed, "ok"
        except Exception:
            return None, "request_or_json_exception"

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
        payload, _ = self._chat_json(system_prompt, user_prompt)
        if not payload:
            return None
        return self._validate_content_payload(payload, expected_count=candidate_count)

    def generate_topic_posts_with_meta(
        self,
        topic: str,
        audience: str,
        business_pain: str,
        research_insights: str,
        candidate_count: int = 10,
    ) -> Dict[str, Any]:
        """
        LLM-first generation plus telemetry for fallback diagnostics.
        Returns:
          {
            "payload": Optional[dict],
            "telemetry": {
              "llm_used": bool,
              "fallback_used": bool,
              "fallback_reason": str,
              "model": str,
              "api_status": str,
            }
          }
        """
        telemetry: Dict[str, Any] = {
            "llm_used": False,
            "fallback_used": False,
            "fallback_reason": "",
            "model": self.model,
            "api_status": "not_attempted",
        }

        prompt_tpl = self._load_prompt("content_intel_post_generator.txt")
        if not prompt_tpl:
            telemetry["fallback_used"] = True
            telemetry["fallback_reason"] = "missing_prompt_template"
            telemetry["api_status"] = "missing_prompt_template"
            return {"payload": None, "telemetry": telemetry}

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

        raw, api_status = self._chat_json(system_prompt, user_prompt)
        telemetry["api_status"] = api_status
        telemetry["llm_used"] = bool(raw is not None and api_status == "ok")
        if not raw:
            telemetry["fallback_used"] = True
            telemetry["fallback_reason"] = f"llm_unavailable:{api_status}"
            return {"payload": None, "telemetry": telemetry}

        validated = self._validate_content_payload(raw, expected_count=candidate_count)
        if not validated:
            telemetry["fallback_used"] = True
            telemetry["fallback_reason"] = "invalid_llm_payload"
            return {"payload": None, "telemetry": telemetry}

        return {"payload": validated, "telemetry": telemetry}

    def select_final_post_with_opus(
        self,
        topic: str,
        shortlist: List[Dict[str, Any]],
        content_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Use Anthropic Opus (performance model) to pick + polish final publish text.
        Returns:
          {
            "selected_text": str | None,
            "selected_candidate_id": str | None,
            "why": str,
            "status": str,
            "model": str
          }
        """
        if not shortlist:
            return {
                "selected_text": None,
                "selected_candidate_id": None,
                "why": "empty_shortlist",
                "status": "no_shortlist",
                "model": self.anthropic_final_model,
            }

        prompt_tpl = self._load_prompt("final_post_selector_opus.txt")
        if not prompt_tpl:
            return {
                "selected_text": None,
                "selected_candidate_id": None,
                "why": "missing_prompt_template",
                "status": "missing_prompt",
                "model": self.anthropic_final_model,
            }

        candidates_payload = {
            "topic": topic,
            "shortlist": shortlist,
            "content_context": content_context or {},
        }
        system_prompt = (
            "You are a rigorous operator-grade editor selecting one final X post. "
            "Return valid JSON only."
        )
        user_prompt = (
            prompt_tpl
            .replace("{{TOPIC}}", str(topic))
            .replace("{{CANDIDATES_JSON}}", json.dumps(candidates_payload, ensure_ascii=True))
        )
        parsed, status = self._anthropic_json(system_prompt, user_prompt)
        if not parsed:
            return {
                "selected_text": None,
                "selected_candidate_id": None,
                "why": f"opus_unavailable:{status}",
                "status": status,
                "model": self.anthropic_final_model,
            }

        selected_text = str(parsed.get("selected_text", "")).strip()
        selected_id = str(parsed.get("selected_candidate_id", "")).strip() or None
        why = str(parsed.get("why", "")).strip() or "opus_selected"
        if not selected_text:
            return {
                "selected_text": None,
                "selected_candidate_id": selected_id,
                "why": "missing_selected_text",
                "status": "invalid_payload",
                "model": self.anthropic_final_model,
            }
        return {
            "selected_text": selected_text,
            "selected_candidate_id": selected_id,
            "why": why,
            "status": "ok",
            "model": self.anthropic_final_model,
        }

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

