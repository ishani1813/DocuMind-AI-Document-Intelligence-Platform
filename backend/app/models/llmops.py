"""LLMOps observability models — tracks every LLM call for cost, latency, quality monitoring."""

import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, Integer, Text, JSON, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LLMProvider(str, enum.Enum):
    OPENAI = "openai"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"


class PromptStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"


class LLMCallLog(Base):
    """Every single LLM call is logged here — the core of LLMOps observability."""
    __tablename__ = "llm_call_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # What was called
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    operation: Mapped[str] = mapped_column(String(100), nullable=False)  # "chat", "embedding", "summarize", etc.
    prompt_id: Mapped[str] = mapped_column(String(36), nullable=True)    # FK to PromptTemplate, if used
    prompt_version: Mapped[int] = mapped_column(Integer, nullable=True)

    # Request context
    user_id: Mapped[str] = mapped_column(String(36), nullable=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=True)
    request_id: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid.uuid4()))

    # Performance metrics
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Cost tracking
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # Quality / outcome
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    # RAG-specific quality metrics
    retrieved_chunk_count: Mapped[int] = mapped_column(Integer, nullable=True)
    avg_relevance_score: Mapped[float] = mapped_column(Float, nullable=True)
    used_hyde: Mapped[bool] = mapped_column(Boolean, default=False)
    used_rerank: Mapped[bool] = mapped_column(Boolean, default=False)

    # Experiment tracking
    experiment_id: Mapped[str] = mapped_column(String(36), nullable=True)
    variant: Mapped[str] = mapped_column(String(50), nullable=True)  # "control", "treatment_a", etc.

    # Raw payload (truncated) for debugging
    input_preview: Mapped[str] = mapped_column(Text, nullable=True)
    output_preview: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PromptTemplate(Base):
    """Version-controlled prompt registry — the heart of prompt management."""
    __tablename__ = "prompt_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(Enum(PromptStatus), default=PromptStatus.DRAFT)

    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[dict] = mapped_column(JSON, default=dict)  # expected variable names + descriptions

    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=True)

    # Aggregate stats (updated periodically)
    total_calls: Mapped[int] = mapped_column(Integer, default=0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    avg_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    success_rate: Mapped[float] = mapped_column(Float, default=1.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Experiment(Base):
    """A/B test configuration for comparing prompts, models, or RAG strategies."""
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Variant configuration: {"control": {"model": "gpt-3.5"}, "treatment_a": {"model": "gpt-4"}}
    variants: Mapped[dict] = mapped_column(JSON, default=dict)
    traffic_split: Mapped[dict] = mapped_column(JSON, default=dict)  # {"control": 0.5, "treatment_a": 0.5}

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Alert(Base):
    """Triggered alerts for cost, latency, or error rate thresholds."""
    __tablename__ = "llmops_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "cost", "latency", "error_rate"
    severity: Mapped[str] = mapped_column(String(20), default="warning")  # "info", "warning", "critical"
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=True)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
