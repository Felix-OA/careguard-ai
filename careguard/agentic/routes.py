from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, HTTPException, Path, Query

from .jobs import AgenticCampaignService
from .models import (
    AgenticCampaign, AgenticCampaignRequest, AgenticComparison, AgenticComparisonRequest,
    AgenticObjective, AgenticReport, AgenticStrategy, ObjectiveRun, TrajectoryTurn,
)
from .objectives import load_objective_pack
from .strategies import STRATEGIES


router = APIRouter(prefix="/agentic", tags=["agentic"])


@lru_cache
def agentic_service() -> AgenticCampaignService:
    from careguard.api.app import connector_for, data_root, database
    from careguard.dashboard.routes import dashboard_service

    service = dashboard_service()

    def configured_connector(target):
        configuration = service.target_configuration(target.target_id)
        raw = service._raw_target_configuration(target.target_id)
        if not configuration.enabled:
            raise ValueError("target is disabled")
        return connector_for(
            target, chat_path=configuration.chat_path,
            timeout_seconds=configuration.timeout_seconds,
            credential_env_reference=raw.get("credential_env_reference"),
        )

    return AgenticCampaignService(
        database(), data_root(), configured_connector, service.effective_policy_version,
    )


@router.get("/objectives", response_model=list[AgenticObjective])
def objectives() -> list[AgenticObjective]:
    return load_objective_pack().objectives


@router.get("/strategies", response_model=list[AgenticStrategy])
def strategies() -> list[AgenticStrategy]:
    return STRATEGIES


@router.post("/campaigns", response_model=AgenticCampaign)
async def create_campaign(request: AgenticCampaignRequest) -> AgenticCampaign:
    try:
        return await agentic_service().create_and_run(request)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            500, "agentic campaign failed safely; inspect the local service logs",
        ) from exc


@router.get("/campaigns", response_model=list[AgenticCampaign])
def campaigns(
    page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=100),
) -> list[AgenticCampaign]:
    items = agentic_service().campaigns()
    offset = (page - 1) * page_size
    return items[offset:offset + page_size]


@router.get("/campaigns/{campaign_id}", response_model=AgenticCampaign)
def campaign(campaign_id: str = Path(pattern=r"^ac-[a-f0-9]{24}$")) -> AgenticCampaign:
    item = agentic_service().campaign(campaign_id)
    if not item:
        raise HTTPException(404, "agentic campaign not found")
    return item


@router.post("/campaigns/{campaign_id}/cancel", response_model=AgenticCampaign)
def cancel_campaign(campaign_id: str = Path(pattern=r"^ac-[a-f0-9]{24}$")) -> AgenticCampaign:
    try:
        item = agentic_service().cancel(campaign_id)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    if not item:
        raise HTTPException(404, "agentic campaign not found")
    return item


@router.get("/campaigns/{campaign_id}/objectives", response_model=list[ObjectiveRun])
def campaign_objectives(campaign_id: str = Path(pattern=r"^ac-[a-f0-9]{24}$")) -> list[ObjectiveRun]:
    if not agentic_service().campaign(campaign_id):
        raise HTTPException(404, "agentic campaign not found")
    return agentic_service().objective_runs(campaign_id)


@router.get("/campaigns/{campaign_id}/trajectories", response_model=list[TrajectoryTurn])
def campaign_trajectories(
    campaign_id: str = Path(pattern=r"^ac-[a-f0-9]{24}$"),
    objective_run_id: str | None = Query(default=None, pattern=r"^aor-[a-f0-9]{24}$"),
) -> list[TrajectoryTurn]:
    if not agentic_service().campaign(campaign_id):
        raise HTTPException(404, "agentic campaign not found")
    if objective_run_id:
        payload = agentic_service().database.get_agentic_objective_payload(objective_run_id)
        if not payload:
            raise HTTPException(404, "agentic objective run not found")
        try:
            objective_run = ObjectiveRun.model_validate_json(payload)
        except Exception as exc:
            raise HTTPException(404, "agentic objective run not found") from exc
        if objective_run.campaign_id != campaign_id:
            raise HTTPException(404, "agentic objective run not found in this campaign")
    return agentic_service().turns(campaign_id, objective_run_id)


@router.get("/campaigns/{campaign_id}/report", response_model=AgenticReport)
def campaign_report(campaign_id: str = Path(pattern=r"^ac-[a-f0-9]{24}$")) -> AgenticReport:
    report = agentic_service().campaign_report(campaign_id)
    if not report:
        raise HTTPException(404, "agentic campaign not found")
    return report


@router.post("/compare", response_model=AgenticComparison)
def compare(request: AgenticComparisonRequest) -> AgenticComparison:
    try:
        return agentic_service().compare(request.baseline_campaign_id, request.guarded_campaign_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/comparisons", response_model=list[AgenticComparison])
def comparisons(
    page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=100),
) -> list[AgenticComparison]:
    items = agentic_service().comparisons()
    offset = (page - 1) * page_size
    return items[offset:offset + page_size]


@router.get("/comparisons/{comparison_id}", response_model=AgenticComparison)
def comparison(comparison_id: str = Path(pattern=r"^acmp-[a-f0-9]{24}$")) -> AgenticComparison:
    item = agentic_service().comparison(comparison_id)
    if not item:
        raise HTTPException(404, "agentic comparison not found")
    return item


@router.get("/comparisons/{comparison_id}/report", response_model=AgenticReport)
def agentic_comparison_report(
    comparison_id: str = Path(pattern=r"^acmp-[a-f0-9]{24}$"),
) -> AgenticReport:
    report = agentic_service().comparison_report(comparison_id)
    if not report:
        raise HTTPException(404, "agentic comparison not found")
    return report
