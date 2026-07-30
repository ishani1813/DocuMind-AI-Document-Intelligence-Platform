"""
LLMOps Service
==============
The observability and governance layer for all LLM calls in DocuMind.

Responsibilities:
  1. Track every LLM call (latency, tokens, cost, success/failure)
  2. Manage versioned prompt templates
  3. Run A/B experiments across prompts/models
  4. Compute aggregate metrics (P50/P95/P99 latency, cost trends)
  5. Trigger alerts on threshold breaches
"""

import time
import uuid
import random
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.config import settings
from app.models.llmops import LLMCallLog, PromptTemplate, Experiment, Alert, PromptStatus

logger = structlog.get_logger()

# ── Pricing table (USD per 1K tokens) — update as providers change pricing ─

PRICING = {
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "text-embedding-ada-002": {"input": 0.0001, "output": 0.0},
    "mistral": {"input": 0.0, "output": 0.0},      # Ollama = free, local compute
    "llama3": {"input": 0.0, "output": 0.0},
    "nomic-embed-text": {"input": 0.0, "output": 0.0},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost for a single LLM call."""
    pricing = PRICING.get(model, {"input": 0.0, "output": 0.0})
    cost = (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]
    return round(cost, 6)


def count_tokens_approx(text: str) -> int:
    """Approximate token count (~4 chars per token) — fast, no tiktoken dependency needed at call time."""
    return max(1, len(text) // 4)


class LLMOpsTracker:
    """
    Context-manager based tracker for a single LLM call.
    Usage:
        async with llmops_tracker.track(operation="chat", model="gpt-4", user_id=uid) as t:
            response = call_llm(...)
            t.set_output(response, input_tokens=123, output_tokens=45)
    """

    def __init__(self):
        self._db_session_factory = None

    def configure(self, db_session_factory):
        self._db_session_factory = db_session_factory

    @asynccontextmanager
    async def track(
        self,
        operation: str,
        model: str,
        provider: str = "openai",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        prompt_id: Optional[str] = None,
        prompt_version: Optional[int] = None,
        experiment_id: Optional[str] = None,
        variant: Optional[str] = None,
    ):
        ctx = _TrackingContext(
            operation=operation, model=model, provider=provider,
            user_id=user_id, session_id=session_id,
            prompt_id=prompt_id, prompt_version=prompt_version,
            experiment_id=experiment_id, variant=variant,
        )
        start = time.perf_counter()
        try:
            yield ctx
            ctx.success = True
        except Exception as e:
            ctx.success = False
            ctx.error_message = str(e)[:500]
            raise
        finally:
            ctx.latency_ms = int((time.perf_counter() - start) * 1000)
            await self._persist(ctx)

    async def _persist(self, ctx: "_TrackingContext"):
        if not settings.LLMOPS_ENABLED or self._db_session_factory is None:
            return
        try:
            async with self._db_session_factory() as db:
                log = LLMCallLog(
                    provider=ctx.provider,
                    model=ctx.model,
                    operation=ctx.operation,
                    prompt_id=ctx.prompt_id,
                    prompt_version=ctx.prompt_version,
                    user_id=ctx.user_id,
                    session_id=ctx.session_id,
                    latency_ms=ctx.latency_ms,
                    input_tokens=ctx.input_tokens,
                    output_tokens=ctx.output_tokens,
                    total_tokens=ctx.input_tokens + ctx.output_tokens,
                    estimated_cost_usd=estimate_cost(ctx.model, ctx.input_tokens, ctx.output_tokens),
                    success=ctx.success,
                    error_message=ctx.error_message,
                    retrieved_chunk_count=ctx.retrieved_chunk_count,
                    avg_relevance_score=ctx.avg_relevance_score,
                    used_hyde=ctx.used_hyde,
                    used_rerank=ctx.used_rerank,
                    experiment_id=ctx.experiment_id,
                    variant=ctx.variant,
                    input_preview=ctx.input_preview[:300] if ctx.input_preview else None,
                    output_preview=ctx.output_preview[:300] if ctx.output_preview else None,
                )
                db.add(log)
                await db.commit()

                # Check alert thresholds
                await self._check_alerts(db, ctx)
        except Exception as e:
            logger.warning("LLMOps tracking failed (non-fatal)", error=str(e))

    async def _check_alerts(self, db: AsyncSession, ctx: "_TrackingContext"):
        cost = estimate_cost(ctx.model, ctx.input_tokens, ctx.output_tokens)
        if cost > settings.LLMOPS_ALERT_COST_THRESHOLD:
            alert = Alert(
                alert_type="cost",
                severity="warning",
                message=f"High-cost LLM call: ${cost:.4f} for {ctx.model} ({ctx.operation})",
                metric_value=cost,
                threshold_value=settings.LLMOPS_ALERT_COST_THRESHOLD,
            )
            db.add(alert)

        if ctx.latency_ms > settings.LLMOPS_ALERT_LATENCY_MS:
            alert = Alert(
                alert_type="latency",
                severity="warning",
                message=f"Slow LLM call: {ctx.latency_ms}ms for {ctx.model} ({ctx.operation})",
                metric_value=ctx.latency_ms,
                threshold_value=settings.LLMOPS_ALERT_LATENCY_MS,
            )
            db.add(alert)

        await db.commit()


class _TrackingContext:
    def __init__(self, operation, model, provider, user_id, session_id,
                 prompt_id, prompt_version, experiment_id, variant):
        self.operation = operation
        self.model = model
        self.provider = provider
        self.user_id = user_id
        self.session_id = session_id
        self.prompt_id = prompt_id
        self.prompt_version = prompt_version
        self.experiment_id = experiment_id
        self.variant = variant

        self.latency_ms = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.success = True
        self.error_message = None
        self.retrieved_chunk_count = None
        self.avg_relevance_score = None
        self.used_hyde = False
        self.used_rerank = False
        self.input_preview = None
        self.output_preview = None

    def set_output(self, output_text: str, input_tokens: int = 0, output_tokens: int = 0):
        self.output_preview = output_text
        self.input_tokens = input_tokens or count_tokens_approx(self.input_preview or "")
        self.output_tokens = output_tokens or count_tokens_approx(output_text)

    def set_input(self, input_text: str):
        self.input_preview = input_text

    def set_rag_metadata(self, chunk_count: int, avg_score: float, used_hyde: bool = False, used_rerank: bool = False):
        self.retrieved_chunk_count = chunk_count
        self.avg_relevance_score = avg_score
        self.used_hyde = used_hyde
        self.used_rerank = used_rerank


# Singleton tracker
llmops_tracker = LLMOpsTracker()


# ── Prompt Registry ────────────────────────────────────────────

class PromptRegistry:
    """Manages versioned prompt templates — create, retrieve, render."""

    async def get_active_prompt(self, db: AsyncSession, name: str) -> Optional[PromptTemplate]:
        result = await db.execute(
            select(PromptTemplate)
            .where(PromptTemplate.name == name, PromptTemplate.status == PromptStatus.ACTIVE)
            .order_by(desc(PromptTemplate.version))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_version(
        self, db: AsyncSession, name: str, template_text: str,
        variables: Dict[str, str] = None, description: str = None,
        created_by: str = None, activate: bool = True,
    ) -> PromptTemplate:
        # Get latest version number
        result = await db.execute(
            select(func.max(PromptTemplate.version)).where(PromptTemplate.name == name)
        )
        max_version = result.scalar() or 0

        # Archive previous active version
        if activate:
            prev = await db.execute(
                select(PromptTemplate).where(
                    PromptTemplate.name == name, PromptTemplate.status == PromptStatus.ACTIVE
                )
            )
            for p in prev.scalars().all():
                p.status = PromptStatus.ARCHIVED

        prompt = PromptTemplate(
            name=name,
            version=max_version + 1,
            status=PromptStatus.ACTIVE if activate else PromptStatus.DRAFT,
            template_text=template_text,
            variables=variables or {},
            description=description,
            created_by=created_by,
        )
        db.add(prompt)
        await db.flush()
        return prompt

    def render(self, template: PromptTemplate, **kwargs) -> str:
        """Render a prompt template with variables."""
        text = template.template_text
        for key, value in kwargs.items():
            text = text.replace(f"{{{key}}}", str(value))
        return text

    async def list_versions(self, db: AsyncSession, name: str) -> List[PromptTemplate]:
        result = await db.execute(
            select(PromptTemplate)
            .where(PromptTemplate.name == name)
            .order_by(desc(PromptTemplate.version))
        )
        return result.scalars().all()


prompt_registry = PromptRegistry()


# ── Experiment / A-B Testing ──────────────────────────────────

class ExperimentRunner:
    """Assigns traffic to experiment variants and tracks results."""

    def assign_variant(self, experiment: Experiment, sticky_key: Optional[str] = None) -> str:
        """
        Assign a variant based on traffic split.
        If sticky_key provided (e.g. user_id), assignment is deterministic for that key.
        """
        variants = list(experiment.traffic_split.keys())
        weights = list(experiment.traffic_split.values())

        if sticky_key:
            # Deterministic hash-based assignment
            hash_val = hash(f"{experiment.id}:{sticky_key}") % 1000 / 1000
            cumulative = 0.0
            for variant, weight in zip(variants, weights):
                cumulative += weight
                if hash_val <= cumulative:
                    return variant
            return variants[-1]
        else:
            return random.choices(variants, weights=weights, k=1)[0]

    async def get_active_experiment(self, db: AsyncSession, name: str) -> Optional[Experiment]:
        result = await db.execute(
            select(Experiment).where(Experiment.name == name, Experiment.is_active == True)
        )
        return result.scalar_one_or_none()


experiment_runner = ExperimentRunner()


# ── Metrics Aggregation ────────────────────────────────────────

class MetricsService:
    """Computes aggregate LLMOps dashboards metrics."""

    async def get_overview(self, db: AsyncSession, hours: int = 24) -> Dict[str, Any]:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        result = await db.execute(
            select(
                func.count(LLMCallLog.id),
                func.avg(LLMCallLog.latency_ms),
                func.sum(LLMCallLog.estimated_cost_usd),
                func.sum(LLMCallLog.total_tokens),
                func.avg(LLMCallLog.success.cast(__import__("sqlalchemy").Integer)),
            ).where(LLMCallLog.created_at >= since)
        )
        row = result.first()
        total_calls, avg_latency, total_cost, total_tokens, success_rate = row

        return {
            "total_calls": total_calls or 0,
            "avg_latency_ms": round(avg_latency or 0, 1),
            "total_cost_usd": round(total_cost or 0, 4),
            "total_tokens": total_tokens or 0,
            "success_rate": round((success_rate or 1.0) * 100, 1),
            "period_hours": hours,
        }

    async def get_latency_percentiles(self, db: AsyncSession, hours: int = 24) -> Dict[str, float]:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await db.execute(
            select(LLMCallLog.latency_ms)
            .where(LLMCallLog.created_at >= since)
            .order_by(LLMCallLog.latency_ms)
        )
        latencies = [r[0] for r in result.all()]
        if not latencies:
            return {"p50": 0, "p95": 0, "p99": 0}

        def percentile(data, p):
            idx = int(len(data) * p / 100)
            return data[min(idx, len(data) - 1)]

        return {
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
        }

    async def get_cost_by_model(self, db: AsyncSession, hours: int = 24) -> List[Dict]:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await db.execute(
            select(
                LLMCallLog.model,
                func.count(LLMCallLog.id),
                func.sum(LLMCallLog.estimated_cost_usd),
                func.sum(LLMCallLog.total_tokens),
            )
            .where(LLMCallLog.created_at >= since)
            .group_by(LLMCallLog.model)
        )
        return [
            {"model": r[0], "calls": r[1], "cost_usd": round(r[2] or 0, 4), "tokens": r[3] or 0}
            for r in result.all()
        ]

    async def get_recent_calls(self, db: AsyncSession, limit: int = 50) -> List[LLMCallLog]:
        result = await db.execute(
            select(LLMCallLog).order_by(desc(LLMCallLog.created_at)).limit(limit)
        )
        return result.scalars().all()

    async def get_active_alerts(self, db: AsyncSession, limit: int = 20) -> List[Alert]:
        result = await db.execute(
            select(Alert)
            .where(Alert.is_resolved == False)
            .order_by(desc(Alert.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_cost_timeseries(self, db: AsyncSession, hours: int = 24, bucket_minutes: int = 60) -> List[Dict]:
        """Bucket cost data into time intervals for charting."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await db.execute(
            select(LLMCallLog.created_at, LLMCallLog.estimated_cost_usd, LLMCallLog.total_tokens)
            .where(LLMCallLog.created_at >= since)
            .order_by(LLMCallLog.created_at)
        )
        rows = result.all()

        buckets: Dict[str, Dict] = {}
        for created_at, cost, tokens in rows:
            bucket_key = created_at.replace(
                minute=(created_at.minute // bucket_minutes) * bucket_minutes if bucket_minutes < 60 else 0,
                second=0, microsecond=0
            ).isoformat()
            if bucket_key not in buckets:
                buckets[bucket_key] = {"timestamp": bucket_key, "cost_usd": 0.0, "tokens": 0, "calls": 0}
            buckets[bucket_key]["cost_usd"] += cost or 0
            buckets[bucket_key]["tokens"] += tokens or 0
            buckets[bucket_key]["calls"] += 1

        return sorted(buckets.values(), key=lambda x: x["timestamp"])


metrics_service = MetricsService()
