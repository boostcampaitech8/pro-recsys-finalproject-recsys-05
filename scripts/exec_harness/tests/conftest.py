from collections import deque
from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Callable

import pytest


@dataclass
class _Outcome:
    returncode: int = 0
    stdout: str = ""
    exception: BaseException | None = None


@dataclass
class _Scenario:
    matches: Callable[[object], bool]
    outcomes: deque[_Outcome]


class FakeSubprocess:
    """Command-aware subprocess.run fake used by harness unit tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[object, dict]] = []
        self._scenarios: list[_Scenario] = []

    def add(
        self,
        command: str | list[str] | tuple[str, ...],
        *,
        returncode: int = 0,
        stdout: str = "",
        exception: BaseException | None = None,
        times: int = 1,
    ) -> None:
        """Inject outcomes for an exact shell command or argv prefix."""
        if isinstance(command, str):
            matches = lambda actual: actual == command
        else:
            prefix = tuple(command)
            matches = lambda actual: (
                not isinstance(actual, str)
                and tuple(actual[: len(prefix)]) == prefix
            )
        self._scenarios.append(
            _Scenario(
                matches=matches,
                outcomes=deque(
                    _Outcome(returncode, stdout, exception) for _ in range(times)
                ),
            )
        )

    def run(self, command, **kwargs):
        self.calls.append((command, kwargs))
        for scenario in self._scenarios:
            if scenario.outcomes and scenario.matches(command):
                outcome = scenario.outcomes.popleft()
                if outcome.exception is not None:
                    raise outcome.exception
                return subprocess.CompletedProcess(
                    command, outcome.returncode, stdout=outcome.stdout
                )
        return subprocess.CompletedProcess(command, 0, stdout="")

    def count(self, command: str | list[str] | tuple[str, ...]) -> int:
        if isinstance(command, str):
            return sum(actual == command for actual, _ in self.calls)
        prefix = tuple(command)
        return sum(
            not isinstance(actual, str)
            and tuple(actual[: len(prefix)]) == prefix
            for actual, _ in self.calls
        )


@pytest.fixture
def repo_root() -> Path:
    """Return the repository root for subprocess-based harness tests."""
    return Path(__file__).resolve().parents[3]


@pytest.fixture
def fake_subprocess(monkeypatch: pytest.MonkeyPatch) -> FakeSubprocess:
    fake = FakeSubprocess()
    monkeypatch.setattr(subprocess, "run", fake.run)
    return fake
