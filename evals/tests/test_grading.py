from unittest.mock import AsyncMock

import pytest
from pydantic_evals import Case, Dataset

from herzo_evals.grading import BehaviorJudge, OutcomeChecks, judge_evidence
from herzo_evals.models import Check, CheckResult, Scenario, TrialResult


@pytest.fixture
def scenario():
    return Scenario(
        id="sample",
        kind="checkpoint",
        skills=["deslop"],
        prompts=["Edit the draft"],
        files={"draft.md": "It may help."},
        checks=[Check(name="meaning", command=["true"])],
        rubric="Preserve uncertainty and the original meaning.",
        provenance="Synthetic test",
    )


async def evaluate(evaluator, scenario, result):
    async def task(_):
        return result

    report = await Dataset(
        name="grading-regression", cases=[Case(inputs=scenario)], evaluators=[evaluator]
    ).evaluate(
        task,
        progress=False,
    )
    return report.cases[0].assertions


async def test_missing_independent_check_does_not_pass(scenario):
    verdicts = await evaluate(OutcomeChecks(), scenario, TrialResult(status="completed"))
    assert verdicts["trial_completed"].value is True
    assert verdicts["check_meaning"].value is False


async def test_failed_command_and_compaction_are_separate(scenario):
    case = scenario.model_copy(update={"kind": "compaction"})
    result = TrialResult(
        status="completed",
        checks=[
            CheckResult(name="meaning", passed=False, exit_code=1, output="bad"),
        ],
    )
    verdicts = await evaluate(OutcomeChecks(), case, result)
    assert not verdicts["check_meaning"].value
    assert not verdicts["compaction_observed"].value


async def test_judge_sees_actual_diff_and_ordered_events_not_scenario_answers(
    scenario, monkeypatch
):
    from pydantic_evals.evaluators import EvaluationReason, LLMJudge

    contexts = []

    async def inspect(self, ctx):
        contexts.append(ctx)
        return {"behavior": EvaluationReason(True, "Evidence checked")}

    monkeypatch.setattr(LLMJudge, "evaluate", inspect)
    result = TrialResult(
        status="completed",
        diff="+new behavior",
        events=[
            {"type": "tool_execution_start", "command": "run tests"},
            {"type": "message_update", "delta": "duplicate"},
            {"type": "tool_execution_end", "output": "FAILED"},
        ],
    )
    verdicts = await evaluate(BehaviorJudge(model="unused"), scenario, result)
    assert verdicts["judge_available"].value
    evidence = contexts[0].output
    assert evidence.index("tool_execution_start") < evidence.index("tool_execution_end")
    assert "+new behavior" in evidence
    assert "duplicate" not in evidence
    assert "provenance" not in evidence
    assert contexts[0].expected_output is None


async def test_infrastructure_error_never_calls_judge(scenario, monkeypatch):
    from pydantic_evals.evaluators import LLMJudge

    judge = AsyncMock()
    monkeypatch.setattr(LLMJudge, "evaluate", judge)
    verdicts = await evaluate(
        BehaviorJudge(model="unused"), scenario, TrialResult(status="infrastructure_error")
    )
    assert not verdicts["judge_available"].value
    judge.assert_not_called()


async def test_judge_timeout_is_reported_not_quality_failure(scenario, monkeypatch):
    import asyncio

    from pydantic_evals.evaluators import LLMJudge

    async def stall(*_):
        await asyncio.sleep(1)

    monkeypatch.setattr(LLMJudge, "evaluate", stall)
    verdicts = await evaluate(
        BehaviorJudge(model="unused", timeout_seconds=0.01),
        scenario,
        TrialResult(status="completed"),
    )
    assert not verdicts["judge_available"].value
    assert "timed out" in verdicts["judge_available"].reason


def test_oversized_evidence_is_not_silently_truncated(scenario):
    assert (
        judge_evidence(scenario, TrialResult(status="completed", diff="x" * 200), limit=50) is None
    )
