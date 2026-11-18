"""Explicit, bounded local and CI entry point."""

import argparse
import asyncio
import io
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

from herzo_evals.models import Settings
from herzo_evals.runner import load_scenarios, paired_experiment, run_experiment
from herzo_evals.selection import matrix_for, shard_cases

REPO = Path(__file__).resolve().parents[3]


def snapshot_skills(repo: Path, ref: str, destination: Path) -> str:
    # Resolve first so a ref cannot become a git option or change during extraction.
    revision = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    ).stdout.strip()
    archive = subprocess.run(
        ["git", "-C", str(repo), "archive", revision, "skills/"],
        check=True,
        capture_output=True,
        timeout=20,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        members = tar.getmembers()
        if sum(member.size for member in members) > 10_000_000:
            raise ValueError("Skill archive is too large")
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError("Unsafe skill archive member")
        tar.extractall(destination, members=members, filter="data")
    return revision


def parse_shard(value: str) -> tuple[int, int]:
    try:
        index, total = (int(part) for part in value.split("/"))
        shard_cases([], index, total)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use INDEX/TOTAL, with 0 <= INDEX < TOTAL <= 50") from exc
    return index, total


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--list", action="store_true", help="List cases without credentials or Docker"
    )
    result.add_argument("--matrix", action="store_true", help="Print a bounded CI matrix as JSON")
    result.add_argument("--shard", type=parse_shard, default=(0, 1), metavar="INDEX/TOTAL")
    result.add_argument(
        "--candidate-only",
        action="store_true",
        help="Characterize the current pack without paying for a duplicate arm",
    )
    result.add_argument("--cases", type=Path, default=REPO / "evals/cases")
    result.add_argument("--case", action="append", default=[])
    result.add_argument("--kind", choices=["checkpoint", "episode", "compaction"], action="append")
    result.add_argument("--include-held-out", action="store_true")
    result.add_argument("--runtime", choices=["pi", "opencode"], default="pi")
    result.add_argument("--model", help="Explicit OpenRouter model ID, e.g. provider/model")
    result.add_argument("--judge-model", help="Explicit OpenRouter judge model ID")
    result.add_argument("--image", default="herzo-evals:local")
    result.add_argument("--skills-root", type=Path, default=REPO / "skills")
    result.add_argument(
        "--baseline-ref", help="Released Git revision to compare, preferably full SHA"
    )
    result.add_argument("--no-skill-baseline", action="store_true")
    result.add_argument("--repeat", type=int, choices=range(1, 6), default=1)
    result.add_argument("--concurrency", type=int, choices=range(1, 5), default=1)
    result.add_argument(
        "--timeout", type=int, default=600, help="Whole trial seconds, including checks"
    )
    result.add_argument("--output", type=Path, default=REPO / "evals/results/latest")
    result.add_argument(
        "--no-judge", action="store_true", help="Collect outcomes only, without LLM judging"
    )
    return result


def main() -> None:
    args = parser().parse_args()
    scenarios = load_scenarios(args.cases, args.case, args.include_held_out)
    if args.kind:
        scenarios = [case for case in scenarios if case.kind in args.kind]
    if args.matrix:
        print(json.dumps(matrix_for(scenarios)))
        return
    scenarios = shard_cases(scenarios, *args.shard)
    if args.list:
        for case in scenarios:
            print(f"{case.id}\t{case.kind}\t{','.join(case.skills)}")
        return
    if not scenarios:
        raise SystemExit("No scenarios selected")
    if not args.model or not args.judge_model:
        raise SystemExit("Specify --model and --judge-model OpenRouter IDs")
    if sum(map(bool, [args.baseline_ref, args.no_skill_baseline, args.candidate_only])) != 1:
        raise SystemExit("Choose --baseline-ref, --no-skill-baseline, or --candidate-only")
    if args.runtime != "pi" and any(case.kind == "compaction" for case in scenarios):
        raise SystemExit(
            "Compaction cases currently require the Pi adapter; select --kind explicitly"
        )
    if args.output.exists():
        raise SystemExit("Output directory already exists; choose a fresh --output path")
    settings = Settings(
        runtime=args.runtime,
        model=args.model,
        judge_model=args.judge_model,
        skills_root=args.skills_root.resolve(),
        image=args.image,
        timeout_seconds=args.timeout,
    )
    with tempfile.TemporaryDirectory(prefix="herzo-eval-baseline-") as scratch:
        baseline = None
        revision = "no-skills"
        if args.baseline_ref:
            revision = snapshot_skills(REPO, args.baseline_ref, Path(scratch))
            baseline = Path(scratch) / "skills"
        if args.candidate_only:
            results = {
                "candidate": asyncio.run(
                    run_experiment(
                        scenarios,
                        settings,
                        args.output / "candidate",
                        args.repeat,
                        args.concurrency,
                        "candidate",
                        judge=not args.no_judge,
                    )
                )
            }
        else:
            results = asyncio.run(
                paired_experiment(
                    scenarios,
                    settings,
                    baseline,
                    args.output,
                    args.repeat,
                    args.concurrency,
                    judge=not args.no_judge,
                )
            )
        (args.output / "comparison.json").write_text(
            json.dumps(
                {
                    "baseline_revision": None if args.candidate_only else revision,
                    "mode": "characterization" if args.candidate_only else "paired",
                    "shard": {"index": args.shard[0], "total": args.shard[1]},
                    "arms": results,
                    "interpretation": (
                        "Behavioral results are report-only; inspect each assertion and trace."
                    ),
                },
                indent=2,
            )
            + "\n"
        )
        print(f"Saved comparison to {args.output / 'comparison.json'}")
        infrastructure_failed = any(
            row["status"] != "completed"
            or (
                not args.no_judge
                and not row.get("assertions", {}).get("judge_available", {}).get("passed", False)
            )
            for arm in results.values()
            for row in arm
        )
        if infrastructure_failed:
            raise SystemExit("An execution or judging error occurred; inspect the report")
