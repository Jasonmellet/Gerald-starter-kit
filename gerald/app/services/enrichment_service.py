from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from rich.console import Console

from ..clients.anthropic_client import AnthropicClient
from ..db import get_session
from ..logging import get_logger
from ..models import Prospect
from ..repositories import posts as posts_repo
from ..repositories import prospect_run_states as run_states_repo
from ..repositories import prospects as prospects_repo
from ..schemas import ProspectSummary
from ..structured_output import get_debug_dir, get_structured, repair_json_with_llm

logger = get_logger(__name__)
console = Console()
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "prospect_summary.txt"

ENRICHMENT_SCHEMA_HINT = (
    "JSON object: role_guess, company_guess (strings or null), summary (string), fit_notes (string or null)."
)

# Bio patterns: "Role @ Company" or "Role at Company" or "Building X" / "Working on X"
BIO_ROLE_AT_PATTERNS = [
    (r"(?i)founder\s*@\s*(\S+)", "Founder"),
    (r"(?i)ceo\s*@\s*(\S+)", "CEO"),
    (r"(?i)co-?founder\s*@\s*(\S+)", "Co-founder"),
    (r"(?i)cto\s*@\s*(\S+)", "CTO"),
    (r"(?i)cmo\s*@\s*(\S+)", "CMO"),
    (r"(?i)building\s+@?\s*([^.!,?\n]+)", "Builder"),
    (r"(?i)working\s+on\s+@?\s*([^.!,?\n]+)", "Builder"),
]


def _parse_bio_patterns(bio: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract role and company from bio using deterministic patterns. Returns (role_guess, company_guess)."""
    if not (bio or "").strip():
        return (None, None)
    role_guess: Optional[str] = None
    company_guess: Optional[str] = None
    for pattern, role in BIO_ROLE_AT_PATTERNS:
        m = re.search(pattern, bio.strip())
        if m:
            company_guess = m.group(1).strip().rstrip(".,!?")
            if not role_guess:
                role_guess = role
            if company_guess:
                break
    return (role_guess, company_guess)


def _company_from_website(website: str) -> Optional[str]:
    """Infer company name from website URL (e.g. wagyr.com -> Wagyr)."""
    if not (website or "").strip():
        return None
    s = website.strip()
    if not s.startswith(("http://", "https://")):
        s = "https://" + s
    try:
        parsed = urlparse(s)
        host = (parsed.netloc or parsed.path or "").lower()
        if not host or host in ("", "localhost"):
            return None
        # Remove www.
        if host.startswith("www."):
            host = host[4:]
        # Take first part (e.g. getviktor.com -> getviktor) and title-case
        name = host.split(".")[0] if "." in host else host
        if not name or len(name) < 2:
            return None
        return name.replace("-", " ").title()
    except Exception:
        return None


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def enrich_prospects(limit: Optional[int] = None) -> dict:
    """
    Enrich prospects with role/company/summary/fit_notes. Returns summary with parse_successes, parse_failures, repaired.
    """
    anthropic_client = AnthropicClient()
    system_prompt = _load_prompt()
    debug_dir = get_debug_dir()

    def complete_fn(system: str, user_content: str) -> str:
        return anthropic_client.strong_complete(system=system, user_content=user_content, max_tokens=512)

    def repair_fn(raw: str) -> str:
        return repair_json_with_llm(raw, ENRICHMENT_SCHEMA_HINT, complete_fn)

    totals = {"parse_successes": 0, "parse_failures": 0, "repaired": 0, "validation_failures": 0, "prospects_processed": 0}

    with get_session() as session:
        prospects: List[Prospect] = list(prospects_repo.list_all(session, limit=limit, min_icp_score=2.0))
        totals["prospects_processed"] = len(prospects)
        for prospect in prospects:
            # Step 1: deterministic bio patterns
            role_from_bio, company_from_bio = _parse_bio_patterns(prospect.bio or "")
            if role_from_bio:
                prospect.role_guess = role_from_bio
            if company_from_bio:
                prospect.company_guess = company_from_bio
            # Step 2: company from website if still missing
            if not prospect.company_guess and prospect.website:
                company_from_web = _company_from_website(prospect.website)
                if company_from_web:
                    prospect.company_guess = company_from_web
            session.flush()

            # Skip LLM if we have both role and company from steps 1 and 2
            if prospect.role_guess and prospect.company_guess:
                session.commit()
                continue

            posts = list(posts_repo.list_for_prospect(session, prospect.id))
            if not prospect.bio and not posts:
                session.commit()
                continue

            context_parts = []
            if prospect.bio:
                context_parts.append(f"BIO:\n{prospect.bio}\n")
            if posts:
                texts = "\n\n".join(f"- {p.text}" for p in posts[:10])
                context_parts.append(f"RECENT_POSTS:\n{texts}")
            context = "\n\n".join(context_parts)

            try:
                raw = complete_fn(system_prompt, context)
            except Exception as exc:
                logger.error("Prospect enrichment failed", extra={"prospect_id": prospect.id, "error": str(exc)})
                totals["parse_failures"] += 1
                continue

            result, stats = get_structured(
                raw,
                schema_class=ProspectSummary,
                expect_list=False,
                step_name="prospect_enrichment",
                debug_dir=debug_dir,
                repair_fn=repair_fn,
            )

            if stats.parse_failures:
                totals["parse_failures"] += 1
                continue
            if stats.validation_failures or not result:
                totals["validation_failures"] += 1
                continue
            if stats.repaired:
                totals["repaired"] += 1
            totals["parse_successes"] += 1

            summary = result
            if summary.role_guess:
                prospect.role_guess = summary.role_guess
            if summary.company_guess:
                prospect.company_guess = summary.company_guess
            prospect.fit_notes = summary.fit_notes or prospect.fit_notes
            if summary.summary:
                # Prospect model has no summary field; fit_notes/summary from LLM go into fit_notes or we leave summary unused
                pass
            session.commit()

        logger.info("Prospect enrichment completed", extra=totals)

    return totals


def enrich_prospects_for_run(session, run_id: int) -> dict:
    """Enrich only prospects in this run's batch (deterministic + LLM fallback)."""
    anthropic_client = AnthropicClient()
    system_prompt = _load_prompt()
    debug_dir = get_debug_dir()

    def complete_fn(system: str, user_content: str) -> str:
        return anthropic_client.strong_complete(system=system, user_content=user_content, max_tokens=512)

    def repair_fn(raw: str) -> str:
        return repair_json_with_llm(raw, ENRICHMENT_SCHEMA_HINT, complete_fn)

    totals = {"parse_successes": 0, "parse_failures": 0, "repaired": 0, "validation_failures": 0}
    prospect_ids = run_states_repo.list_prospect_ids_for_run(session, run_id, only_discovered=True)

    for prospect_id in prospect_ids:
        prospect = session.get(Prospect, prospect_id)
        if not prospect:
            continue
        role_from_bio, company_from_bio = _parse_bio_patterns(prospect.bio or "")
        if role_from_bio:
            prospect.role_guess = role_from_bio
        if company_from_bio:
            prospect.company_guess = company_from_bio
        if not prospect.company_guess and prospect.website:
            company_from_web = _company_from_website(prospect.website)
            if company_from_web:
                prospect.company_guess = company_from_web
        session.flush()

        if prospect.role_guess and prospect.company_guess:
            session.commit()
            continue

        posts = list(posts_repo.list_for_prospect(session, prospect.id))
        if not prospect.bio and not posts:
            session.commit()
            continue

        context_parts = []
        if prospect.bio:
            context_parts.append(f"BIO:\n{prospect.bio}\n")
        if posts:
            texts = "\n\n".join(f"- {p.text}" for p in posts[:10])
            context_parts.append(f"RECENT_POSTS:\n{texts}")
        context = "\n\n".join(context_parts)

        try:
            raw = complete_fn(system_prompt, context)
        except Exception as exc:
            logger.error("Prospect enrichment failed", extra={"prospect_id": prospect.id, "error": str(exc)})
            totals["parse_failures"] += 1
            continue

        result, stats = get_structured(
            raw,
            schema_class=ProspectSummary,
            expect_list=False,
            step_name="prospect_enrichment",
            debug_dir=debug_dir,
            repair_fn=repair_fn,
        )

        if stats.parse_failures:
            totals["parse_failures"] += 1
            continue
        if stats.validation_failures or not result:
            totals["validation_failures"] += 1
            continue
        if stats.repaired:
            totals["repaired"] += 1
        totals["parse_successes"] += 1
        summary = result
        if summary.role_guess:
            prospect.role_guess = summary.role_guess
        if summary.company_guess:
            prospect.company_guess = summary.company_guess
        prospect.fit_notes = summary.fit_notes or prospect.fit_notes
        session.commit()

    logger.info("Enrichment for run completed", extra={"run_id": run_id, **totals})
    return totals

