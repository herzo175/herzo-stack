"""Shared, strict scenario and evidence contracts."""

from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Check(StrictModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    command: list[str] = Field(min_length=1)
    expected_exit: int = 0


class Scenario(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    kind: Literal["checkpoint", "episode", "compaction"]
    skills: list[str] = Field(min_length=1)
    prompts: list[str] = Field(min_length=1, max_length=30)
    files: dict[str, str]
    checks: list[Check] = Field(min_length=1)
    rubric: str = Field(min_length=20)
    provenance: str
    held_out: bool = False
    compact_after_turn: int | None = Field(default=None, ge=1)

    @field_validator("skills")
    @classmethod
    def skill_names(cls, names: list[str]) -> list[str]:
        import re

        if any(not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) for name in names):
            raise ValueError("Skills must be simple directory names")
        return names

    @field_validator("files")
    @classmethod
    def safe_files(cls, files: dict[str, str]) -> dict[str, str]:
        for name in files:
            path = PurePosixPath(name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or path.parts[0] in {".git", ".pi", ".opencode", ".agents", ".codex", ".claude"}
                or "\\" in name
            ):
                raise ValueError(f"Unsafe fixture path: {name}")
        return files

    @model_validator(mode="after")
    def unambiguous_case(self) -> "Scenario":
        if any(not prompt.strip() for prompt in self.prompts):
            raise ValueError("Every turn needs a nonempty user prompt")
        if len({check.name for check in self.checks}) != len(self.checks):
            raise ValueError("Independent check names must be unique")
        if len(set(self.skills)) != len(self.skills):
            raise ValueError("Selected skill names must be unique")
        return self

    @model_validator(mode="after")
    def compaction_action(self) -> "Scenario":
        if self.kind == "compaction" and self.compact_after_turn is None:
            raise ValueError("Compaction cases require an actual compaction action")
        if self.compact_after_turn is not None and self.compact_after_turn >= len(self.prompts):
            raise ValueError("At least one prompt must follow compaction")
        return self


OPEN_MODELS = frozenset({"deepseek/deepseek-v4.1-flash", "z-ai/glm-5.3", "qwen/qwen3.8-27b"})


def validate_model_pair(runtime: str, model: str) -> None:
    if runtime in {"pi", "opencode"} and model not in OPEN_MODELS:
        raise ValueError(f"{runtime} requires an open model from: {', '.join(sorted(OPEN_MODELS))}")
    required = {"claude": "anthropic/claude-", "codex": "openai/gpt-"}.get(runtime)
    if required and not model.startswith(required):
        raise ValueError(
            f"{runtime} requires a {required} model; use pi or opencode for other models"
        )


class Settings(StrictModel):
    runtime: Literal["pi", "opencode", "codex", "claude"]
    model: str = Field(min_length=3)
    judge_model: str = Field(min_length=3)
    skills_root: Path | None
    image: str = "herzo-evals:local"
    timeout_seconds: int = Field(default=600, ge=1, le=3600)
    max_output_bytes: int = Field(default=4_000_000, ge=1000, le=20_000_000)
    max_output_tokens: int = Field(default=8192, ge=512, le=32768)

    @model_validator(mode="after")
    def supported_model_pair(self) -> "Settings":
        validate_model_pair(self.runtime, self.model)
        return self


class CheckResult(StrictModel):
    name: str
    passed: bool
    exit_code: int
    output: str


class TrialResult(StrictModel):
    trial_id: str = ""
    status: Literal["completed", "timeout", "infrastructure_error", "output_limit"]
    events: list[dict[str, Any]] = Field(default_factory=list)
    diff: str = ""
    checks: list[CheckResult] = Field(default_factory=list)
    final_response: str = ""
    compactions: int = 0
    usage: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration: float = 0


class CorpusEntry(StrictModel):
    case_id: str
    family: str
    source_ids: list[str]
    origin: Literal["incident_reconstruction", "designed_control", "designed_extension"]
    skills: list[str]
    scope: Literal["general", "factory-specific", "project-specific"]
    held_out: bool
    coverage: str = Field(min_length=20)

    @model_validator(mode="after")
    def incident_has_source(self) -> "CorpusEntry":
        if self.origin == "incident_reconstruction" and not self.source_ids:
            raise ValueError("Incident reconstructions require a private source alias")
        return self
