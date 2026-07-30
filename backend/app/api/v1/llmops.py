"""
LLMOps API — /api/v1/llmops/

Endpoints for the LLMOps observability dashboard:
  - Metrics overview (calls, latency, cost, success rate)
  - Latency percentiles (P50/P95/P99)
  - Cost breakdown by model
  - Cost timeseries for charting
  - Recent call logs
  - Active alerts
  - Prompt registry (CRUD + versioning)
  - Experiments (A/B testing)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.llmops import PromptTemplate, Experiment
from app.schemas.llmops import (
    LLMCallLogResponse, MetricsOverview, LatencyPercentiles, CostByModel,
    CreatePromptRequest, PromptResponse, CreateExperimentRequest, ExperimentResponse,
    AlertResponse,
)
from app.llmops import metrics_service, prompt_registry, experiment_runner

router = APIRouter()


# ── Metrics Dashboard ─────────────────────────────────────────

@router.get("/metrics/overview", response_model=MetricsOverview)
async def get_metrics_overview(
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await metrics_service.get_overview(db, hours=hours)


@router.get("/metrics/latency", response_model=LatencyPercentiles)
async def get_latency_percentiles(
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await metrics_service.get_latency_percentiles(db, hours=hours)


@router.get("/metrics/cost-by-model", response_model=List[CostByModel])
async def get_cost_by_model(
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await metrics_service.get_cost_by_model(db, hours=hours)


@router.get("/metrics/cost-timeseries")
async def get_cost_timeseries(
    hours: int = 24,
    bucket_minutes: int = 60,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await metrics_service.get_cost_timeseries(db, hours=hours, bucket_minutes=bucket_minutes)


@router.get("/calls/recent", response_model=List[LLMCallLogResponse])
async def get_recent_calls(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await metrics_service.get_recent_calls(db, limit=limit)


@router.get("/alerts", response_model=List[AlertResponse])
async def get_active_alerts(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await metrics_service.get_active_alerts(db, limit=limit)


# ── Prompt Registry ───────────────────────────────────────────

@router.post("/prompts", response_model=PromptResponse, status_code=201)
async def create_prompt(
    payload: CreatePromptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompt = await prompt_registry.create_version(
        db, name=payload.name, template_text=payload.template_text,
        variables=payload.variables, description=payload.description,
        created_by=current_user.id, activate=payload.activate,
    )
    return prompt


@router.get("/prompts/{name}/active", response_model=PromptResponse)
async def get_active_prompt(
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompt = await prompt_registry.get_active_prompt(db, name)
    if not prompt:
        raise HTTPException(status_code=404, detail="No active prompt found with that name")
    return prompt


@router.get("/prompts/{name}/versions", response_model=List[PromptResponse])
async def list_prompt_versions(
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await prompt_registry.list_versions(db, name)


# ── Experiments ───────────────────────────────────────────────

@router.post("/experiments", response_model=ExperimentResponse, status_code=201)
async def create_experiment(
    payload: CreateExperimentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_split = sum(payload.traffic_split.values())
    if abs(total_split - 1.0) > 0.01:
        raise HTTPException(status_code=400, detail="traffic_split values must sum to 1.0")

    experiment = Experiment(
        name=payload.name, description=payload.description,
        variants=payload.variants, traffic_split=payload.traffic_split,
    )
    db.add(experiment)
    await db.flush()
    return experiment


@router.get("/experiments", response_model=List[ExperimentResponse])
async def list_experiments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    result = await db.execute(select(Experiment).order_by(Experiment.created_at.desc()))
    return result.scalars().all()


@router.post("/experiments/{experiment_id}/deactivate")
async def deactivate_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    exp.is_active = False
    return {"message": "Experiment deactivated"}
