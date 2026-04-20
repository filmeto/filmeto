from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, List, Sequence


DEFAULT_STATE_PATH = Path(".workspace/ai_tdd_lint_state.json")


@dataclass
class TddResult:
    ok: bool
    message: str
    exit_code: int


def _normalize_targets(targets: Iterable[str]) -> List[str]:
    cleaned = [str(t).strip() for t in targets if str(t).strip()]
    # Keep deterministic matching while preserving caller order intent.
    return cleaned


def _run_pytest(targets: Sequence[str], cwd: Path) -> int:
    cmd = ["pytest", *targets]
    completed = subprocess.run(cmd, cwd=str(cwd))
    return int(completed.returncode)


def _load_state(state_path: Path) -> dict:
    if not state_path.is_file():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state_path: Path, payload: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _same_targets(a: Sequence[str], b: Sequence[str]) -> bool:
    return list(a) == list(b)


def record_red(
    targets: Sequence[str],
    *,
    cwd: Path,
    state_path: Path = DEFAULT_STATE_PATH,
    runner: Callable[[Sequence[str], Path], int] = _run_pytest,
) -> TddResult:
    normalized = _normalize_targets(targets)
    if not normalized:
        return TddResult(False, "No test targets provided for red phase.", 2)

    exit_code = runner(normalized, cwd)
    if exit_code == 0:
        return TddResult(
            False,
            "Red phase failed: tests passed unexpectedly. Write failing tests first.",
            1,
        )

    payload = {
        "targets": normalized,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "red_exit_code": exit_code,
    }
    _save_state(state_path, payload)
    return TddResult(True, "Red phase recorded (tests failed as expected).", 0)


def verify_green(
    targets: Sequence[str],
    *,
    cwd: Path,
    state_path: Path = DEFAULT_STATE_PATH,
    runner: Callable[[Sequence[str], Path], int] = _run_pytest,
) -> TddResult:
    normalized = _normalize_targets(targets)
    if not normalized:
        return TddResult(False, "No test targets provided for green phase.", 2)

    state = _load_state(state_path)
    previous_targets = state.get("targets") if isinstance(state, dict) else None
    if not isinstance(previous_targets, list):
        return TddResult(
            False,
            "Green phase blocked: no prior red record found. Run red phase first.",
            1,
        )

    if not _same_targets(previous_targets, normalized):
        return TddResult(
            False,
            "Green phase blocked: test targets differ from recorded red phase.",
            1,
        )

    exit_code = runner(normalized, cwd)
    if exit_code != 0:
        return TddResult(
            False,
            "Green phase failed: tests still failing after implementation.",
            exit_code,
        )

    state_path.unlink(missing_ok=True)
    return TddResult(True, "Green phase passed. TDD cycle complete.", 0)


def lint(
    targets: Sequence[str],
    *,
    cwd: Path,
    state_path: Path = DEFAULT_STATE_PATH,
    runner: Callable[[Sequence[str], Path], int] = _run_pytest,
) -> TddResult:
    return verify_green(targets, cwd=cwd, state_path=state_path, runner=runner)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai_tdd_lint",
        description="Enforce red->green TDD cycle for targeted unit tests.",
    )
    parser.add_argument(
        "--state-file",
        default=str(DEFAULT_STATE_PATH),
        help="State file path used to persist red phase record.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("red", "green", "lint"):
        cmd = sub.add_parser(name)
        cmd.add_argument("targets", nargs="+", help="pytest targets (files/tests)")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    state_path = Path(args.state_file)
    cwd = Path.cwd()

    if args.command == "red":
        result = record_red(args.targets, cwd=cwd, state_path=state_path)
    elif args.command == "green":
        result = verify_green(args.targets, cwd=cwd, state_path=state_path)
    else:
        result = lint(args.targets, cwd=cwd, state_path=state_path)

    print(result.message)
    return int(result.exit_code)

