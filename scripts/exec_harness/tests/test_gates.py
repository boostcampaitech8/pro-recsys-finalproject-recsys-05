import subprocess

import pytest

from exec_harness.gates import run_verify


pytestmark = pytest.mark.unit


def test_empty_verify_fails() -> None:
    ok, output = run_verify("", timeout=10)

    assert not ok
    assert "verify 필수" in output


def test_explicit_verify_skip_is_allowed(fake_subprocess) -> None:
    ok, output = run_verify("skip", timeout=10)

    assert ok
    assert "명시" in output
    assert fake_subprocess.calls == []


def test_verify_timeout_is_reported_as_failure(fake_subprocess) -> None:
    fake_subprocess.add(
        "slow verify",
        exception=subprocess.TimeoutExpired(cmd="slow verify", timeout=10),
    )

    ok, output = run_verify("slow verify", timeout=10)

    assert not ok
    assert "verify 타임아웃" in output
