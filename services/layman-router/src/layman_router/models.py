from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RouteTier(StrEnum):
    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"


class TaskType(StrEnum):
    SUMMARY = "summary"
    REWRITE = "rewrite"
    TRANSLATION = "translation"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    NORMAL_CODING = "normal_coding"
    CODE_EXPLANATION = "code_explanation"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    MATH = "math"
    GENERAL = "general"


class ModelPricing(BaseModel):
    input_per_million: float = Field(ge=0)
    cached_input_per_million: float = Field(ge=0)
    output_per_million: float = Field(ge=0)
    cache_write_per_million: float | None = Field(default=None, ge=0)


class TierConfig(BaseModel):
    model: str
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"]
    max_output_tokens: int = Field(gt=0)
    pricing: ModelPricing


class ProjectConfig(BaseModel):
    default_quality: Literal["economy", "standard", "production"] = "standard"
    default_budget: Literal["low", "medium", "high"] = "medium"
    rules: dict[str, RouteTier] = Field(default_factory=dict)


class RouterConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listen_host: str = "127.0.0.1"
    listen_port: int = Field(default=8787, ge=1, le=65535)
    upstream_base_url: str = "https://api.openai.com/v1"
    database_path: str = "~/.layman/usage.sqlite3"
    admin_token_env: str = "LAYMAN_ROUTER_ADMIN_TOKEN"
    admin_allow_non_loopback: bool = False
    dashboard_enabled: bool = True
    demo_mode: bool = False
    telemetry_retention_days: int = Field(default=90, ge=1, le=3650)
    upstream_timeout_seconds: float = Field(default=120.0, gt=0, le=900)
    price_version: str
    tiers: dict[RouteTier, TierConfig]
    projects: dict[str, ProjectConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_all_tiers(self) -> "RouterConfig":
        missing = set(RouteTier) - set(self.tiers)
        if missing:
            raise ValueError(f"Missing route tiers: {sorted(item.value for item in missing)}")
        return self


class TaskFeatures(BaseModel):
    task_type: TaskType
    complexity: Literal["low", "medium", "high"]
    risk: Literal["low", "medium", "high"]
    has_code: bool
    prompt_chars: int = Field(ge=0)
    tool_count: int = Field(ge=0)
    agentic: bool
    project_id: str
    quality: Literal["economy", "standard", "production"]
    budget: Literal["low", "medium", "high"]
    prompt_hash: str


class RouteDecision(BaseModel):
    selected_model: str
    reasoning_effort: str
    max_output_tokens: int
    route_tier: RouteTier
    route_reason: list[str]
    automatic: bool = True


class ValidationResult(BaseModel):
    passed: bool
    reason: str | None = None


class UsageRecord(BaseModel):
    request_id: str
    project_id: str
    prompt_hash: str
    task_type: str
    complexity: str
    risk: str
    route_tier: str
    selected_model: str
    reasoning_effort: str
    route_reason: list[str]
    input_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    latency_ms: int = 0
    estimated_cost_usd: float = 0
    estimated_always_deep_cost_usd: float = 0
    fallback_used: bool = False
    validator_passed: bool | None = None
    error_category: str | None = None
    upstream_request_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
