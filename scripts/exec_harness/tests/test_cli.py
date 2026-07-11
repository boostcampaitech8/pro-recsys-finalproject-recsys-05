from pathlib import Path
import subprocess

import pytest

from exec_harness import cli, runner


pytestmark = pytest.mark.unit


def _run_args(task_dir: Path, *extra: str) -> list[str]:
    return [
        "--task",
        str(task_dir),
        "--no-branch",
        "--no-commit",
        "--no-push",
        "--no-pr",
        "--no-review",
        *extra,
    ]


@pytest.fixture(autouse=True)
def isolate_runner(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runner, "RUNS_DIR", repo_root / "scripts/exec_harness/tests/runtime"
    )
    monkeypatch.setattr(runner, "find_codex", lambda: "codex")


@pytest.fixture
def task_sample(repo_root: Path) -> Path:
    return repo_root / "scripts/exec_harness/tests/fixtures/task_sample"


@pytest.fixture
def task_empty(repo_root: Path) -> Path:
    return repo_root / "scripts/exec_harness/tests/fixtures/task_empty"


@pytest.fixture
def task_missing_step(repo_root: Path) -> Path:
    return repo_root / "scripts/exec_harness/tests/fixtures/task_missing_step"


def test_invalid_from_exits_2_with_available_steps(
    task_sample: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = cli.main(["--task", str(task_sample), "--from", "step9", "--dry-run"])

    assert rc == 2
    output = capsys.readouterr().out
    assert "사용 가능한 step" in output
    assert "step1, step2" in output


def test_halted_run_returns_nonzero(task_sample: Path, fake_subprocess) -> None:
    fake_subprocess.add(["codex", "exec"], stdout="{}\n")
    fake_subprocess.add("echo ok", returncode=1, stdout="failed")

    rc = cli.main(_run_args(task_sample, "--self-repair", "0"))

    assert rc != 0


def test_gh_pr_failure_returns_nonzero(task_sample: Path, fake_subprocess) -> None:
    fake_subprocess.add(["codex", "exec"], stdout="{}\n", times=2)
    fake_subprocess.add(["gh", "pr", "create"], returncode=1, stdout="gh failed")
    args = _run_args(task_sample)
    args.remove("--no-pr")

    rc = cli.main(args)

    assert rc != 0


def test_push_failure_returns_nonzero(task_sample: Path, fake_subprocess) -> None:
    fake_subprocess.add(["codex", "exec"], stdout="{}\n", times=2)
    fake_subprocess.add(["git", "push"], returncode=1, stdout="push failed")
    args = _run_args(task_sample)
    args.remove("--no-push")

    rc = cli.main(args)

    assert rc != 0


def test_branch_failure_returns_nonzero(task_sample: Path, fake_subprocess) -> None:
    fake_subprocess.add(["git", "checkout"], returncode=1, stdout="checkout failed")
    args = _run_args(task_sample)
    args.remove("--no-branch")

    rc = cli.main(args)

    assert rc != 0


def test_codex_failure_after_retries_returns_nonzero(
    task_sample: Path, fake_subprocess
) -> None:
    fake_subprocess.add(
        ["codex", "exec"], returncode=7, stdout="codex failed", times=2
    )

    rc = cli.main(_run_args(task_sample, "--self-repair", "1"))

    assert rc != 0
    assert fake_subprocess.count(["codex", "exec"]) == 2


def test_codex_timeout_returns_nonzero(task_sample: Path, fake_subprocess) -> None:
    fake_subprocess.add(
        ["codex", "exec"],
        exception=subprocess.TimeoutExpired(cmd="codex exec", timeout=10),
    )

    rc = cli.main(_run_args(task_sample, "--timeout", "10"))

    assert rc != 0


def test_empty_verify_execplan_returns_nonzero(
    task_empty: Path, fake_subprocess
) -> None:
    rc = cli.main(_run_args(task_empty, "--self-repair", "0"))

    assert rc != 0
    assert fake_subprocess.count(["codex", "exec"]) == 0


def test_missing_task_returns_nonzero(task_sample: Path) -> None:
    rc = cli.main(_run_args(task_sample / "does-not-exist"))

    assert rc != 0


def test_missing_step_file_returns_nonzero(task_missing_step: Path) -> None:
    rc = cli.main(_run_args(task_missing_step))

    assert rc != 0
