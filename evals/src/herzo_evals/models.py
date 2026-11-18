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
            if (path.is_absolute() or ".." in path.parts or not path.parts
                    or path.parts[0] in {".git", ".pi", ".opencode", ".agents"}
                    or "\\" in name):
                raise ValueError(f"Unsafe fixture path: {name}")
        return files

    @model_validator(mode="after")
    def compaction_action(self) -> "Scenario":
        if self.kind == "compaction" and self.compact_after_turn is None:
            raise ValueError("Compaction cases require an actual compaction action")
        if self.compact_after_turn is not None and self.compact_after_turn >= len(self.prompts):
            raise ValueError("At least one prompt must follow compaction")
        return self


class Settings(StrictModel):
    runtime: Literal["pi", "opencode"]
    model: str = Field(min_length=3)
    judge_model: str = Field(min_length=3)
    skills_root: Path | None
    image: str = "herzo-evals:local"
    timeout_seconds: int = Field(default=600, ge=1, le=3600)
    max_output_bytes: int = Field(default=4_000_000, ge=1000, le=20_000_000)
    max_output_tokens: int = Field(default=8192, ge=512, le=32768)


class CheckResult(StrictModel):
    name: str
    passed: bool
    exit_code: int
    output: str


class TrialResult(StrictModel):
    status: Literal["completed", "timeout", "infrastructure_error", "output_limit"]
    events: list[dict[str, Any]] = Field(default_factory=list)
    diff: str = ""
    checks: list[CheckResult] = Field(default_factory=list)
    final_response: str = ""
    compactions: int = 0
    usage: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration: float = 0
