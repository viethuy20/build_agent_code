"""
Orchestrator tự chạy lại test, không tin báo cáo "tests passed" từ agent.

Nguyên tắc: Model reports intent; orchestrator verifies outcome.
"""

from __future__ import annotations

import dataclasses
import pathlib
import subprocess


@dataclasses.dataclass
class TestRunResult:
    passed: bool
    command: str = ""
    output: str = ""


def run_tests(commands: list[str], workdir: pathlib.Path, timeout_seconds: int = 600) -> TestRunResult:
    """Chạy tuần tự từng command trong test_commands.

    Dừng ngay ở command đầu tiên fail (fail-fast), trả về log của command đó.
    Chỉ PASS nếu tất cả command đều exit code 0.
    """
    if not commands:
        return TestRunResult(passed=False, output="Không có test_commands nào được khai báo trong task.json")

    combined_log = []

    for cmd in commands:
        combined_log.append(f"$ {cmd}")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            combined_log.append(f"TIMEOUT sau {timeout_seconds}s")
            return TestRunResult(passed=False, command=cmd, output="\n".join(combined_log))

        combined_log.append(result.stdout)
        if result.stderr:
            combined_log.append(result.stderr)

        if result.returncode != 0:
            combined_log.append(f"EXIT CODE: {result.returncode}")
            return TestRunResult(passed=False, command=cmd, output="\n".join(combined_log))

    return TestRunResult(passed=True, output="\n".join(combined_log))
