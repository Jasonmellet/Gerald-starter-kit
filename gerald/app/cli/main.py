from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..config import get_settings
from ..db import create_all, get_session, run_migrations
from ..logging import configure_root_logger
from ..repositories import pipeline_runs as pipeline_runs_repo
from ..repositories import prospect_run_states as run_states_repo
from ..services import (
    discovery_service,
    drafting_service,
    digest_service,
    enrichment_service,
    follow_up_reply_service,
    outreach_preview_service,
    review_service,
    run_outreach_report_service,
    run_report_service,
    scoring_service,
    selection_service,
    send_service,
    signal_service,
)


app = typer.Typer(help="Gerald – X opportunity discovery and outreach copilot.")
console = Console()


@app.callback()
def _init() -> None:
    """
    Initialize logging and (optionally) database schema.
    """

    configure_root_logger()
    run_migrations()


@app.command()
def init_db() -> None:
    """Create database tables."""

    create_all()
    console.print("[green]Database tables created (if they did not already exist).[/green]")


@app.command()
def discover(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max new prospects to store (for test runs)."),
) -> None:
    """Discover prospects on X using default queries."""

    discovery_service.run_discovery(max_prospects=limit)


def _print_structured_summary(step: str, totals: dict) -> None:
    """Print parse successes, failures, repaired for a step."""
    s = totals.get("parse_successes", 0)
    f = totals.get("parse_failures", 0)
    r = totals.get("repaired", 0)
    v = totals.get("validation_failures", 0)
    console.print(
        f"  [bold]{step}[/bold]: successes={s}, parse_failures={f}, validation_failures={v}, repaired={r}"
    )


@app.command()
def analyze(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max prospects to process (for test runs)."),
) -> None:
    """Extract signals and enrich prospects."""

    signal_totals = signal_service.analyze_signals_for_all_prospects(limit=limit)
    enrichment_totals = enrichment_service.enrich_prospects(limit=limit)
    console.print("[dim]Structured output summary:[/dim]")
    _print_structured_summary("Signals", signal_totals)
    _print_structured_summary("Enrichment", enrichment_totals)


@app.command()
def score(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max prospects to score (for test runs)."),
) -> None:
    """Score prospects and create/update opportunities."""

    totals = scoring_service.score_opportunities(limit=limit)
    console.print("[dim]Structured output summary:[/dim]")
    _print_structured_summary("Scoring", totals)


@app.command()
def draft() -> None:
    """Generate outreach drafts for top opportunities."""

    drafting_service.draft_for_top_opportunities()


@app.command()
def digest() -> None:
    """Print top opportunities and write a markdown daily digest."""

    digest_service.build_digest()


review_app = typer.Typer(help="Review queue commands.")


@review_app.command("list")
def review_list() -> None:
    """List top new opportunities for review."""

    opps = review_service.list_opportunities()
    review_service.render_opportunities_table(opps)


@review_app.command("approve")
def review_approve(opportunity_id: int) -> None:
    """Approve an opportunity."""

    review_service.approve_opportunity(opportunity_id)


@review_app.command("reject")
def review_reject(opportunity_id: int) -> None:
    """Reject an opportunity."""

    review_service.reject_opportunity(opportunity_id)


@review_app.command("archive")
def review_archive(opportunity_id: int) -> None:
    """Archive an opportunity."""

    review_service.archive_opportunity(opportunity_id)


@review_app.command("edit")
def review_edit(opportunity_id: int) -> None:
    """Edit the DM draft for an opportunity (opens $EDITOR)."""

    review_service.edit_opportunity_draft(opportunity_id)


app.add_typer(review_app, name="review")


@app.command("run-pipeline")
def run_pipeline(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Cap prospects per step (discover/analyze/score) for test runs."),
) -> None:
    """Run the full pipeline: discover -> analyze -> score -> draft -> digest."""

    if limit:
        console.print(f"[bold]Running Gerald pipeline (limit={limit})...[/bold]")
    else:
        console.print("[bold]Running Gerald pipeline...[/bold]")

    disc_result = discovery_service.run_discovery(max_prospects=limit)
    prospects_created = (disc_result or {}).get("prospects_created", 0)

    signal_totals = signal_service.analyze_signals_for_all_prospects(limit=limit)
    enrichment_totals = enrichment_service.enrich_prospects(limit=limit)
    console.print("[dim]Structured output summary:[/dim]")
    _print_structured_summary("Signals", signal_totals)
    _print_structured_summary("Enrichment", enrichment_totals)

    score_totals = scoring_service.score_opportunities(limit=limit)
    console.print("[dim]Structured output summary:[/dim]")
    _print_structured_summary("Scoring", score_totals)

    opportunities_created = score_totals.get("parse_successes", 0)
    drafts_created = drafting_service.draft_for_top_opportunities(limit=50)

    digest_service.build_digest()

    from ..db import get_session
    from ..repositories import drafts as drafts_repo
    from ..repositories import opportunities as opp_repo

    with get_session() as session:
        opp_above_threshold = opp_repo.count_above_threshold(session, min_overall=50)
        opp_qualified = opp_repo.count_outreach_qualified(session)
        drafts_awaiting = drafts_repo.count_awaiting_approval(session)

    prospects_analyzed = enrichment_totals.get("prospects_processed", 0)

    console.print("[green]Pipeline completed.[/green]")
    console.print("[bold]Pipeline summary:[/bold]")
    console.print(f"  Prospects discovered: {prospects_created}")
    console.print(f"  Prospects analyzed: {prospects_analyzed}")
    console.print(f"  Opportunities created: {opportunities_created}")
    console.print(f"  Opportunities above outreach threshold: {opp_qualified}")
    console.print(f"  Drafts generated: {drafts_created}")
    console.print(f"  Drafts awaiting approval: {drafts_awaiting}")


@app.command("run-autonomous")
def run_autonomous() -> None:
    """Run one autonomous batch: create run, discover (30h, limit 100), analyze, score, draft, select top 5, send (log), write report."""

    settings = get_settings()
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(hours=settings.discovery_lookback_hours)
    limit = settings.daily_discovery_limit
    outreach_limit = settings.daily_outreach_limit

    with get_session() as session:
        run = pipeline_runs_repo.create_run(
            session, window_start=window_start, window_end=window_end, discovery_limit=limit
        )
        session.commit()
        run_id = run.id

    with get_session() as session:
        run = pipeline_runs_repo.get_by_id(session, run_id)
        if not run:
            console.print("[red]Run not found.[/red]")
            return
        console.print(f"[bold]Run {run_id}:[/bold] discover (30h, limit {limit}) -> analyze -> score -> draft -> select {outreach_limit} -> send -> report")

        discovery_service.run_discovery_for_run(session, run)
        session.commit()

        signal_service.analyze_signals_for_run(session, run_id)
        session.commit()
        pipeline_runs_repo.update_run_counts(
            session, run_id, analyzed_count=run_states_repo.count_analyzed_for_run(session, run_id)
        )

        enrichment_service.enrich_prospects_for_run(session, run_id)
        session.commit()

        scoring_service.score_opportunities_for_run(session, run_id)
        session.commit()
        pipeline_runs_repo.update_run_counts(
            session, run_id, scored_count=run_states_repo.count_scored_for_run(session, run_id)
        )

        drafting_service.draft_for_run(session, run_id, limit=outreach_limit * 3)

        # Select more than outreach_limit so we can go down the list until we've sent to enough (403/skips use up slots)
        pool_size = max(outreach_limit * 4, 20)
        top_opportunities = selection_service.select_top_for_run(session, run_id, limit=pool_size)
        pipeline_runs_repo.update_run_counts(session, run_id, selected_count=len(top_opportunities))

        # Send DMs (or dry-run) for selected prospects and write outreach report
        output_dir = Path("outputs")
        send_summary = send_service.send_dms_for_run(session, run_id)
        outreach_report_path = run_outreach_report_service.write_outreach_send_report(
            session, run_id,
            mode=str(send_summary.get("mode", "live")),
            summary=send_summary,
            output_dir=output_dir,
        )

        pipeline_runs_repo.set_run_completed(session, run_id, status="completed", completed_at=datetime.now(timezone.utc))

        run = pipeline_runs_repo.get_by_id(session, run_id)
        report_path = run_report_service.write_run_report(session, run, output_dir)
        session.commit()

    # Follow-up: 5 min after send, post a public reply to each prospect's latest tweet
    settings = get_settings()
    if settings.follow_up_reply_enabled and (send_summary.get("live_sent") or 0) > 0:
        console.print(f"[dim]Waiting {settings.follow_up_reply_delay_seconds}s before follow-up replies...[/dim]")
        time.sleep(settings.follow_up_reply_delay_seconds)
        with get_session() as session:
            follow_up_summary = follow_up_reply_service.send_replies_for_run(session, run_id)
        console.print(
            f"  Follow-up replies: eligible={follow_up_summary.get('contacts_eligible')}, "
            f"sent={follow_up_summary.get('replies_sent')}, skipped_no_tweet={follow_up_summary.get('skipped_no_tweet')}, "
            f"skipped_no_question={follow_up_summary.get('skipped_no_question')}, "
            f"skipped_reply_policy={follow_up_summary.get('skipped_reply_policy')}, failed={follow_up_summary.get('failed')}"
        )

    console.print("[green]Run-autonomous completed.[/green]")
    console.print(f"  Run report: {report_path}")
    console.print(f"  Outreach report: {outreach_report_path}")
    console.print(f"  Discovered: {run.discovered_count}, Analyzed: {run.analyzed_count}, Scored: {run.scored_count}, Selected: {run.selected_count}")
    console.print(f"  Outreach: attempted={send_summary.get('attempted')}, sent={send_summary.get('live_sent')}, failed={send_summary.get('failed')}, skipped={send_summary.get('skipped')}")


def _get_latest_completed_run_id() -> Optional[int]:
    with get_session() as session:
        from ..models import PipelineRun

        run = (
            session.query(PipelineRun)
            .filter(PipelineRun.status == "completed")
            .order_by(PipelineRun.id.desc())
            .first()
        )
        return run.id if run else None


@app.command("preview-outreach")
def preview_outreach(run_id: int) -> None:
    """Preview selected prospects and DM drafts for a run (no sending)."""

    with get_session() as session:
        rows = outreach_preview_service.get_run_outreach_preview(session, run_id, include_sent=True)
        if not rows:
            console.print(f"[yellow]No selected prospects found for run {run_id}.[/yellow]")
            return

        table = Table(show_header=True, header_style="bold")
        table.add_column("Handle")
        table.add_column("x_user_id")
        table.add_column("Priority")
        table.add_column("Freshness (h)")
        table.add_column("Opportunity ID")
        table.add_column("DM Preview")

        for row in rows:
            body = (row.get("draft_body") or "")[:200]
            table.add_row(
                f"@{row.get('handle')}",
                str(row.get("x_user_id") or ""),
                f"{row.get('priority_score') or 0:.1f}",
                f"{row.get('freshness_hours') or 0:.1f}",
                str(row.get("opportunity_id") or ""),
                body,
            )

        console.print(table)


@app.command("preview-latest-top")
def preview_latest_top() -> None:
    """Preview latest completed run's selected prospects and DM bodies."""

    run_id = _get_latest_completed_run_id()
    if not run_id:
        console.print("[yellow]No completed runs found.[/yellow]")
        return
    console.print(f"[bold]Latest completed run: {run_id}[/bold]")
    preview_outreach(run_id)


@app.command("send-outreach")
def send_outreach(run_id: int) -> None:
    """Send (or dry-run) outreach DMs for a specific run using current send mode."""

    from ..db import get_session  # re-import for clarity

    with get_session() as session:
        summary = send_service.send_dms_for_run(session, run_id)
        settings = get_settings()
        mode = summary.get("mode") or settings.outreach_send_mode

        # Update run sent_count with live_sent only
        live_sent = int(summary.get("live_sent") or 0)
        pipeline_runs_repo.update_run_counts(session, run_id, sent_count=live_sent)

        output_dir = Path("outputs")
        report_path = run_outreach_report_service.write_outreach_send_report(
            session, run_id, mode=str(mode), summary=summary, output_dir=output_dir
        )

    console.print("[bold]Outreach send summary[/bold]")
    console.print(f"- run id: {summary.get('run_id')}")
    console.print(f"- mode: {summary.get('mode')}")
    console.print(f"- selected candidates: {summary.get('selected_candidates')}")
    console.print(f"- attempted sends: {summary.get('attempted')}")
    console.print(f"- live sent: {summary.get('live_sent')}")
    console.print(f"- dry-run only: {summary.get('dry_run')}")
    console.print(f"- skipped: {summary.get('skipped')}")
    console.print(f"- failed: {summary.get('failed')}")
    console.print(f"- report: {report_path}")


@app.command("send-outreach-latest")
def send_outreach_latest() -> None:
    """Send (or dry-run) outreach for the latest completed run."""

    run_id = _get_latest_completed_run_id()
    if not run_id:
        console.print("[yellow]No completed runs found.[/yellow]")
        return
    console.print(f"[bold]Sending outreach for latest completed run {run_id}[/bold]")
    send_outreach(run_id)


if __name__ == "__main__":
    app()

