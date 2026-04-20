import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.ai_tdd_lint import record_red, verify_green


def test_record_red_requires_failing_tests(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    res = record_red(
        ["tests/test_app/test_data/test_shot_task_executor.py"],
        cwd=tmp_path,
        state_path=state,
        runner=lambda _targets, _cwd: 0,
    )
    assert not res.ok
    assert not state.exists()


def test_record_red_persists_state_on_failure(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    res = record_red(
        ["tests/test_app/test_data/test_shot_task_executor.py"],
        cwd=tmp_path,
        state_path=state,
        runner=lambda _targets, _cwd: 1,
    )
    assert res.ok
    assert state.exists()


def test_verify_green_requires_matching_red_targets(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    record_red(
        ["tests/test_app/test_data/test_shot_task_executor.py"],
        cwd=tmp_path,
        state_path=state,
        runner=lambda _targets, _cwd: 1,
    )
    res = verify_green(
        ["tests/test_app/test_data/test_screenplay_storyboard_layout.py"],
        cwd=tmp_path,
        state_path=state,
        runner=lambda _targets, _cwd: 0,
    )
    assert not res.ok
    assert state.exists()


def test_verify_green_clears_state_after_pass(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    record_red(
        ["tests/test_app/test_data/test_shot_task_executor.py"],
        cwd=tmp_path,
        state_path=state,
        runner=lambda _targets, _cwd: 1,
    )
    res = verify_green(
        ["tests/test_app/test_data/test_shot_task_executor.py"],
        cwd=tmp_path,
        state_path=state,
        runner=lambda _targets, _cwd: 0,
    )
    assert res.ok
    assert not state.exists()

