import pytest

from herzo_evals.models import Check, Scenario
from herzo_evals.selection import matrix_for, shard_cases


def cases(count):
    return [
        Scenario(
            id=f"case-{n:02d}",
            kind="checkpoint",
            skills=["measure"],
            prompts=["Measure it"],
            files={},
            checks=[Check(name="result", command=["true"])],
            rubric="Report a measured number with its denominator.",
            provenance="Control",
        )
        for n in range(count)
    ]


@pytest.mark.parametrize("count", [1, 6, 37, 50])
def test_shards_cover_every_case_once_and_remain_bounded(count):
    values = cases(count)
    matrix = matrix_for(values)
    shards = [shard_cases(values, row["index"], row["total"]) for row in matrix["include"]]
    assert all(1 <= len(shard) <= 4 for shard in shards)
    ids = [case.id for shard in shards for case in shard]
    assert len(ids) == len(set(ids)) == count
    assert set(ids) == {case.id for case in values}
    assert shards == [
        shard_cases(list(reversed(values)), row["index"], row["total"]) for row in matrix["include"]
    ]


def test_invalid_or_empty_shards_fail_explicitly():
    for index, total in [(-1, 2), (2, 2), (0, 0), (0, 51)]:
        with pytest.raises(ValueError, match="Shard"):
            shard_cases(cases(1), index, total)
    with pytest.raises(ValueError, match="No scenarios"):
        matrix_for([])
