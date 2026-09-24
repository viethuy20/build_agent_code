"""
Subagent 1: Planner Agent

Nhiệm vụ:
  - Tiếp nhận yêu cầu/prompt của người dùng.
  - Khảo sát repository đích (cấu trúc code, convention, test framework hiện có).
  - Tự động lập kế hoạch và sinh 2 file:
      1. tasks/<TASK_ID>/task.json (cấu trúc dữ liệu cho máy đọc)
      2. tasks/<TASK_ID>/plan.md   (kế hoạch chi tiết cho Coder Agent đọc)
  - TUYỆT ĐỐI KHÔNG sửa code trong repo ở bước này (chỉ inspect & plan).
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any

import agy_worker


class PlannerError(RuntimeError):
    pass


def build_planner_prompt(
    user_prompt: str,
    repo_path: pathlib.Path,
    task_id: str,
    task_dir: pathlib.Path,
) -> str:
    # Chuẩn hóa đường dẫn tương thích cross-platform
    task_dir_str = str(task_dir.resolve()).replace("\\", "/")
    repo_path_str = str(repo_path.resolve()).replace("\\", "/")

    return f"""Bạn là Architect / Planner Subagent cho một dự án phần mềm.
Nhiệm vụ của bạn là khảo sát repository và lập kế hoạch thực hiện task theo yêu cầu của người dùng.

# YÊU CẦU TỪ NGƯỜI DÙNG:
{user_prompt}

# THÔNG TIN MÔI TRƯỜNG:
- Repository đích: {repo_path_str}
- Task ID: {task_id}
- Thư mục lưu task: {task_dir_str}

# QUY TẮC BẮT BUỘC:
1. TUYỆT ĐỐI KHÔNG sửa, thêm hoặc xoá bất kỳ file nào trong repository đích ({repo_path_str}).
2. Khảo sát cấu trúc repo để xác định: ngôn ngữ, convention, thư mục test, công cụ test (pytest, unittest, npm test,...).
3. Tạo CHÍNH XÁC 2 file trong thư mục `{task_dir_str}`:

FILE 1: `{task_dir_str}/task.json`
Định dạng JSON hợp lệ:
{{
  "task_id": "{task_id}",
  "title": "Tiêu đề ngắn gọn mô tả task",
  "description": "Mô tả chi tiết mục tiêu cần đạt được",
  "requirements": [
    "Yêu cầu cụ thể 1",
    "Yêu cầu cụ thể 2"
  ],
  "acceptance_criteria": [
    "Tiêu chí nghiệm thu 1",
    "Tiêu chí nghiệm thu 2"
  ],
  "test_commands": [
    "Lệnh test chính xác để verify, ví dụ: python -m unittest discover hoặc pytest"
  ],
  "risk_level": "LOW",
  "risk_reasons": [
    "Lý do đánh giá rủi ro (đánh giá HIGH nếu thay đổi auth, db migration, xóa dữ liệu, bảo mật)"
  ]
}}

FILE 2: `{task_dir_str}/plan.md`
Định dạng Markdown:
# Implementation Plan — {task_id}

## 1. Inspect & Architecture
(Mô tả các file hiện có liên quan và convention cần tuân thủ)

## 2. Implementation Steps
(Từng bước cụ thể: tạo file gì, sửa hàm nào, logic ra sao)

## 3. Test Strategy
(Các test cases cần viết để đảm bảo đúng tiêu chí nghiệm thu)

## 4. Verification
(Lệnh test kiểm tra cuối cùng)

Hãy bắt đầu khảo sát và tạo ngay 2 file trên vào thư mục `{task_dir_str}`!
"""


def _try_extract_json(text: str) -> dict[str, Any] | None:
    """Fallback: trích xuất JSON từ markdown block nếu agy in ra stdout thay vì ghi file."""
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Thử tìm object JSON đầu tiên
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        pass
    return None


def run_planner(
    user_prompt: str,
    repo_path: pathlib.Path,
    task_id: str,
    tasks_dir: pathlib.Path,
    mode: str,
    logs_dir: pathlib.Path,
    timeout_seconds: int = 600,
) -> pathlib.Path:
    """Gọi Planner Subagent để khảo sát repo và tạo task.json + plan.md.

    Trả về task_dir chứa 2 file đã tạo.
    """
    task_dir = (tasks_dir / task_id).resolve()
    task_dir.mkdir(parents=True, exist_ok=True)

    planner_prompt = build_planner_prompt(
        user_prompt=user_prompt,
        repo_path=repo_path,
        task_id=task_id,
        task_dir=task_dir,
    )

    raw_log_path = logs_dir / f"{task_id}.planner.agy.log"
    timeout_flag = f"{timeout_seconds}s"
    agy_bin = agy_worker.get_agy_bin()

    # Thêm cả repo_path và task_dir vào --add-dir để agy có quyền đọc repo và ghi vào task_dir
    add_dirs = ["--add-dir", str(repo_path.resolve()), "--add-dir", str(task_dir)]

    if mode == "direct":
        argv = [
            agy_bin,
            "--dangerously-skip-permissions",
            *add_dirs,
            "--print-timeout",
            timeout_flag,
            "-p",
            planner_prompt,
        ]
        exit_code, output = agy_worker._stream_process(
            argv,
            cwd=repo_path,
            log_path=raw_log_path,
            timeout_seconds=timeout_seconds,
            heartbeat_seconds=None,
        )
    elif mode == "winpty":
        argv = [
            "winpty",
            agy_bin,
            "--dangerously-skip-permissions",
            *add_dirs,
            "--print-timeout",
            timeout_flag,
            "-p",
            planner_prompt,
        ]
        exit_code, output = agy_worker._stream_process(
            argv,
            cwd=repo_path,
            log_path=raw_log_path,
            timeout_seconds=timeout_seconds,
            heartbeat_seconds=None,
        )
    elif mode == "pty":
        import os

        env = os.environ.copy()
        env["AGY_PROMPT"] = planner_prompt
        inner = (
            f'"{agy_bin}" --dangerously-skip-permissions '
            f'--add-dir "{str(repo_path.resolve())}" --add-dir "{str(task_dir)}" '
            f'--print-timeout "{timeout_flag}" -p "$AGY_PROMPT"'
        )
        argv = ["script", "-qec", inner, "/dev/null"]
        exit_code, output = agy_worker._stream_process(
            argv,
            cwd=repo_path,
            log_path=raw_log_path,
            timeout_seconds=timeout_seconds,
            heartbeat_seconds=None,
            env=env,
        )
    else:
        raise PlannerError(f"Chế độ mode='{mode}' không được hỗ trợ để chạy Planner.")

    if exit_code != 0:
        raise PlannerError(f"Planner Subagent thất bại với exit code {exit_code}. Xem log: {raw_log_path}")

    task_json_path = task_dir / "task.json"
    plan_md_path = task_dir / "plan.md"

    # Trường hợp 1: agy đã tự tạo trực tiếp cả 2 file
    if task_json_path.exists() and plan_md_path.exists():
        # Validate định dạng JSON
        try:
            json.loads(task_json_path.read_text(encoding="utf-8"))
            return task_dir
        except json.JSONDecodeError:
            pass  # Nếu file json lỗi cú pháp, thử phục hồi từ stdout bên dưới

    # Trường hợp 2: Fallback phục hồi nếu agy in ra stdout
    parsed_json = _try_extract_json(output)
    if parsed_json:
        task_json_path.write_text(json.dumps(parsed_json, indent=2, ensure_ascii=False), encoding="utf-8")

    if not plan_md_path.exists():
        # Nếu chưa có plan.md, lưu output của model làm plan
        plan_content = output.strip() or f"# Plan {task_id}\n\nThực hiện task: {user_prompt}"
        plan_md_path.write_text(plan_content, encoding="utf-8")

    # Kiểm tra lần cuối
    if not task_json_path.exists():
        # Tạo task.json tối thiểu nếu thiếu
        fallback_task = {
            "task_id": task_id,
            "title": user_prompt[:60],
            "description": user_prompt,
            "requirements": [user_prompt],
            "acceptance_criteria": ["Test pass"],
            "test_commands": ["python -m unittest discover"],
            "risk_level": "LOW",
            "risk_reasons": [],
        }
        task_json_path.write_text(json.dumps(fallback_task, indent=2, ensure_ascii=False), encoding="utf-8")

    return task_dir
