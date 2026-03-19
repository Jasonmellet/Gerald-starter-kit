"""
Process meeting transcripts: customers, action items, topics, save to disk.
"""
import re
import json
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path


class MeetingProcessor:
    def __init__(self):
        self.customer_patterns = [
            r"(?:customer|client)\s+(\w+(?:\s+\w+)?)",
            r"(?:with|for)\s+(\w+(?:\s+\w+)?)\s+(?:customer|client)",
            r"(\w+(?:\s+\w+)?)\s+(?:account|project|engagement)",
        ]

    def process_transcript(
        self, transcript: List[Dict[str, Any]], meeting_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        full_text = self._combine_transcript(transcript)
        customers = self._extract_customers(full_text, transcript)
        action_items = self._extract_action_items(full_text, transcript)
        customer_summaries = self._summarize_by_customer(customers, full_text, transcript)
        topics = self._extract_topics(full_text)
        return {
            "meeting_info": meeting_info,
            "processed_at": datetime.now().isoformat(),
            "summary": {
                "total_segments": len(transcript),
                "customers_discussed": list(customers.keys()),
                "action_items_count": len(action_items),
                "key_topics": topics,
            },
            "customers": customer_summaries,
            "action_items": action_items,
            "full_transcript": transcript,
            "raw_text": full_text,
        }

    def _combine_transcript(self, transcript: List[Dict[str, Any]]) -> str:
        return "\n".join(
            f"{s.get('speaker', 'Unknown')}: {s.get('text', '')}" for s in transcript
        )

    def _extract_customers(
        self, full_text: str, transcript: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict]]:
        customers = {}
        for pattern in self.customer_patterns:
            for m in re.finditer(pattern, full_text, re.IGNORECASE):
                name = m.group(1).strip()
                if len(name) > 2:
                    if name not in customers:
                        customers[name] = []
                    start = max(0, m.start() - 100)
                    end = min(len(full_text), m.end() + 100)
                    customers[name].append(
                        {"context": full_text[start:end], "position": m.start()}
                    )
        for pattern in [
            r"(?:at|from|with)\s+([A-Z][\w\s&]+?)(?:\s+(?:today|yesterday)|\.|,|\n|$)",
            r"(?:company|organization)\s+(?:called|named)?\s+([A-Z][\w\s&]+)",
        ]:
            for m in re.finditer(pattern, full_text):
                company = m.group(1).strip()
                if company and company not in customers:
                    customers[company] = [{"context": m.group(0), "position": m.start()}]
        return customers

    def _extract_action_items(
        self, full_text: str, transcript: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        keywords = [
            "action item", "follow up", "follow-up", "to do", "todo",
            "need to", "should", "will", "going to", "by next", "by tomorrow",
        ]
        items = []
        for segment in transcript:
            text = segment.get("text", "").lower()
            speaker = segment.get("speaker", "Unknown")
            for kw in keywords:
                if kw in text:
                    for sent in re.split(r"[.!?]+", text):
                        if kw in sent and len(sent.strip()) > 10:
                            items.append({"text": sent.strip(), "speaker": speaker})
                            break
                    break
        seen = set()
        unique = []
        for item in items:
            n = re.sub(r"\s+", " ", item["text"].lower())
            if n not in seen:
                seen.add(n)
                unique.append(item)
        return unique

    def _summarize_by_customer(
        self,
        customers: Dict[str, List],
        full_text: str,
        transcript: List[Dict[str, Any]],
    ) -> Dict[str, Dict]:
        summaries = {}
        for name, mentions in customers.items():
            key_points = []
            for m in mentions:
                for sent in re.split(r"[.!?]+", m.get("context", "")):
                    if name.lower() in sent.lower() and len(sent) > 20:
                        key_points.append(sent.strip())
            seen = set()
            unique = []
            for p in key_points:
                n = re.sub(r"\s+", " ", p.lower())
                if n not in seen:
                    seen.add(n)
                    unique.append(p)
            summaries[name] = {"mention_count": len(mentions), "key_points": unique[:5]}
        return summaries

    def _extract_topics(self, full_text: str) -> List[str]:
        topic_keywords = {
            "pricing": ["price", "cost", "budget", "quote"],
            "timeline": ["timeline", "schedule", "deadline", "milestone"],
            "technical": ["technical", "integration", "api", "implementation"],
            "next_steps": ["next step", "follow up", "schedule"],
        }
        text_lower = full_text.lower()
        return list(set(t for t, kws in topic_keywords.items() if any(k in text_lower for k in kws)))

    def save_analysis(self, analysis: Dict[str, Any], output_dir: str) -> str:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        meeting_info = analysis.get("meeting_info", {})
        date_str = meeting_info.get("date", datetime.now().strftime("%Y-%m-%d"))
        subject = meeting_info.get("subject", "meeting")
        subject_clean = re.sub(r"[^\w\-]", "_", subject)[:50]
        filepath = Path(output_dir) / f"{date_str}_{subject_clean}_analysis.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        md_path = Path(output_dir) / f"{date_str}_{subject_clean}_summary.md"
        self._save_markdown(analysis, md_path)
        return str(filepath)

    def _save_markdown(self, analysis: Dict[str, Any], filepath: Path) -> None:
        meeting_info = analysis.get("meeting_info", {})
        summary = analysis.get("summary", {})
        customers = analysis.get("customers", {})
        action_items = analysis.get("action_items", [])
        lines = [
            f"# Meeting Summary: {meeting_info.get('subject', 'Unknown')}",
            "",
            f"**Date:** {meeting_info.get('date', 'Unknown')}",
            "",
            "## Overview",
            "",
            f"- Customers: {len(summary.get('customers_discussed', []))}",
            f"- Action items: {summary.get('action_items_count', 0)}",
            f"- Topics: {', '.join(summary.get('key_topics', []))}",
            "",
            "## Customers",
            "",
        ]
        for name, data in customers.items():
            lines.append(f"### {name}\n**Mentions:** {data.get('mention_count', 0)}\n")
            for p in data.get("key_points", []):
                lines.append(f"- {p}")
            lines.append("")
        lines.extend(["## Action Items", ""])
        for item in action_items:
            lines.append(f"- [{item.get('speaker', '?')}] {item.get('text', '')}")
        filepath.write_text("\n".join(lines), encoding="utf-8")
