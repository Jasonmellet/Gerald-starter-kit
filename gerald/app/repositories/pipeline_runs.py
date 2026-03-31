from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models import PipelineRun


def create_run(
    session: Session,
    window_start: datetime,
    window_end: datetime,
    discovery_limit: int,
    started_at: Optional[datetime] = None,
) -> PipelineRun:
    run = PipelineRun(
        started_at=started_at or window_end,
        discovery_window_start=window_start,
        discovery_window_end=window_end,
        discovery_limit=discovery_limit,
        status="running",
    )
    session.add(run)
    return run


def get_by_id(session: Session, run_id: int) -> Optional[PipelineRun]:
    return session.get(PipelineRun, run_id)


def update_run_counts(session: Session, run_id: int, **kwargs: Any) -> None:
    run = session.get(PipelineRun, run_id)
    if not run:
        return
    for key, value in kwargs.items():
        if hasattr(run, key):
            setattr(run, key, value)


def set_run_completed(
    session: Session,
    run_id: int,
    status: str = "completed",
    completed_at: Optional[datetime] = None,
    total_estimated_cost: Optional[float] = None,
) -> None:
    run = session.get(PipelineRun, run_id)
    if not run:
        return
    run.status = status
    if completed_at is not None:
        run.completed_at = completed_at
    if total_estimated_cost is not None:
        run.total_estimated_cost = total_estimated_cost
