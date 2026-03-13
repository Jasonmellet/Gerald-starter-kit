from __future__ import annotations

from typing import Dict


def operator_templates(opportunity: Dict[str, str]) -> Dict[str, str]:
    topic = opportunity.get("topic", "general_growth")
    pain = opportunity.get("business_pain", "Growth execution is inconsistent.")
    icp = opportunity.get("target_icp_segment", "SMB operator")

    strong_opinion = (
        f"Most SMBs do not have a lead problem. They have a systems problem.\n\n"
        f"{pain}\n\n"
        "The fix is almost never another tool. It is one clear operating workflow with ownership.\n\n"
        "If you run a team today, where is your biggest handoff failing right now?"
    )
    contrarian = (
        f"Hot take for {icp}: if your dashboard looks better than your close rate, your system is broken.\n\n"
        f"Topic: {topic}\n"
        "Most teams optimize reporting before fixing execution.\n\n"
        "What metric are you tracking that actually changes behavior this week?"
    )
    how_to = (
        "Simple operator loop:\n"
        "1) Identify one recurring revenue leak\n"
        "2) Assign one owner\n"
        "3) Define one measurable handoff\n"
        "4) Review weekly\n\n"
        f"Applied to {topic}, this solves more than 90% of avoidable chaos.\n\n"
        "Which step breaks first in your org?"
    )
    return {
        "strong_opinion": strong_opinion,
        "contrarian": contrarian,
        "how_to": how_to,
    }

