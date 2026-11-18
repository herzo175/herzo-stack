"""Deterministic, disjoint case partitions for bounded CI jobs."""

from herzo_evals.models import Scenario


def shard_cases(cases: list[Scenario], index: int, total: int) -> list[Scenario]:
    if not 1 <= total <= 50 or not 0 <= index < total:
        raise ValueError("Shard must be INDEX/TOTAL with 0 <= INDEX < TOTAL <= 50")
    return [
        case
        for position, case in enumerate(sorted(cases, key=lambda c: c.id))
        if position % total == index
    ]


def matrix_for(cases: list[Scenario]) -> dict:
    if not cases:
        raise ValueError("No scenarios selected")
    # Four paired cases fit below the job deadline even if each consumes its whole budget.
    total = (len(cases) + 3) // 4
    if total > 50:
        raise ValueError("Corpus requires more than 50 shards; increase grouping deliberately")
    return {"include": [{"index": index, "total": total} for index in range(total)]}
