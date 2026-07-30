from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel


class LLMCallLogResponse(BaseModel):
    id: str
    provider: str
    model: str
    operation: str
    latency_ms: int
    total_tokens: int
    estimated_cost_usd: float
    success: bool
    error_message: Optional[str] = None
    used_hyde: bool
    used_rerank: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class MetricsOverview(BaseModel):
    total_calls: int
    avg_latency_ms: float
    total_cost_usd: float
    total_tokens: int
    success_rate: float
    period_hours: int


class LatencyPercentiles(BaseModel):
    p50: float
    p95: float
    p99: float


class CostByModel(BaseModel):
    model: str
    calls: int
    cost_usd: float
    tokens: int


class CreatePromptRequest(BaseModel):
    name: str
    template_text: str
    variables: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    activate: bool = True


class PromptResponse(BaseModel):
    id: str
    name: str
    version: int
    status: str
    template_text: str
    variables: Dict
    description: Optional[str] = None
    total_calls: int
    avg_latency_ms: float
    avg_cost_usd: float
    success_rate: float
    created_at: datetime
    model_config = {"from_attributes": True}


class CreateExperimentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    variants: Dict[str, Dict]
    traffic_split: Dict[str, float]


class ExperimentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    variants: Dict
    traffic_split: Dict
    created_at: datetime
    model_config = {"from_attributes": True}


class AlertResponse(BaseModel):
    id: str
    alert_type: str
    severity: str
    message: str
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None
    is_resolved: bool
    created_at: datetime
    model_config = {"from_attributes": True}
