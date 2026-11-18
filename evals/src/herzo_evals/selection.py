"""Deterministic, disjoint case partitions for bounded CI jobs."""

from herzo_evals.models import Scenario

MAX_SHARDS = 64
JOB_SECONDS = 120 * 60
SETUP_RESERVE_SECONDS = 15 * 60
JUDGE_SECONDS = 90


def shard_cases(cases: list[Scenario], index: int, total: int) -> list[Scenario]:
    if not 1 <= total <= MAX_SHARDS or not 0 <= index < total:
        raise ValueError(f"Shard must satisfy 0 <= INDEX < TOTAL <= {MAX_SHARDS}")
    return [
        case
        for position, case in enumerate(sorted(cases, key=lambda c: c.id))
        if position % total == index
    ]


def matrix_for(
    cases: list[Scenario],
    *,
    repeat: int = 1,
    arms: int = 2,
    trial_seconds: int = 600,
) -> dict:
    if not cases:
        raise ValueError("No scenarios selected")
    if not 1 <= repeat <= 5 or arms not in {1, 2} or not 1 <= trial_seconds <= 3600:
        raise ValueError("Invalid per-case budget")
    per_case = repeat * arms * (trial_seconds + JUDGE_SECONDS + 30)
    capacity = min(4, (JOB_SECONDS - SETUP_RESERVE_SECONDS) // per_case)
    if capacity < 1:
        raise ValueError("Per-case budget exceeds a CI shard; lower repetitions or trial timeout")
    total = (len(cases) + capacity - 1) // capacity
    if total > MAX_SHARDS:
        raise ValueError(f"Corpus requires more than {MAX_SHARDS} shards; review the run budget")
    return {"include": [{"index": index, "total": total} for index in range(total)]}
