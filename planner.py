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
import knowledge_manager


class PlannerError(RuntimeError):
    pass


def build_planner_prompt(
    user_prompt: str,
    repo_path: pathlib.Path,
    task_id: str,
    task_dir: pathlib.Path,
    project_memory: str = "",
    project_docs: str = "",
    available_skills: list[str] | None = None,
) -> str:
    # Chuẩn hóa đường dẫn tương thích cross-platform
    task_dir_str = str(task_dir.resolve()).replace("\\", "/")
    repo_path_str = str(repo_path.resolve()).replace("\\", "/")

    skills_list_str = ", ".join(available_skills) if available_skills else "N/A"

    memory_section = ""
    if project_memory:
        memory_section = f"""
# 🧠 KINH NGHIỆM ĐÃ TÍCH LŨY TỪ CÁC TASK TRƯỚC (PROJECT MEMORY):
{project_memory}
"""

    docs_section = ""
    if project_docs:
        docs_section = f"""
{project_docs}
"""

    return f"""Bạn là Tech Lead & Manager Agent tối cao cho dự án phần mềm này.
Nhiệm vụ của bạn là:
1. Khảo sát toàn diện repository đích (cấu trúc code, ngôn ngữ, convention, testing framework).
2. Tận dụng Kinh nghiệm từ các task trước (Project Memory) và Tài liệu kiến trúc dự án (nếu có).
3. Phân tích yêu cầu từ người dùng và chia nhỏ thành kế hoạch thực thi rõ ràng, chi tiết.
4. Đánh giá mức độ rủi ro (risk_level: LOW / MEDIUM / HIGH).
5. Phân loại tính chất task, QUYẾT ĐỊNH CHỈ ĐỊNH SUBAGENT CHUYÊN TRÁCH (assigned_subagent) và CHỌN CÁC KỸ NĂNG CẦN THIẾT (relevant_skills) từ kho kỹ năng:
   - Kho Kỹ năng khả dụng: [{skills_list_str}]
   - Danh sách Subagent Roles:
     • `backend_specialist`: Backend, API, Database, Xử lý dữ liệu, Services, Async/Concurrency.
     • `frontend_specialist`: Web UI, CSS, Component, Layout, Responsive, HTML, UX.
     • `senior_debugger`: Bug khó, ngoại lệ, phân tích root cause, vá lỗi bảo mật.
     • `refactor_architect`: Tái cấu trúc Clean Code, SOLID, Design Patterns.
     • `test_engineer`: Viết test cases chuyên sâu, mock, coverage, QA.
     • `general_coder`: Tác vụ tổng hợp hoặc CRUD cơ bản.

# YÊU CẦU TỪ NGƯỜI DÙNG:
{user_prompt}
{memory_section}{docs_section}
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
  "english_slug": "kebab-case-slug-in-english (chuẩn tiếng Anh ngắn gọn 3-5 từ, ví dụ: add-format-currency-utils, optimize-database-query, fix-auth-token-bug)",
  "description": "Mô tả chi tiết mục tiêu cần đạt được",
  "task_type": "data_engineering | backend | frontend | bugfix | refactor | testing | general",
  "relevant_skills": [
    "tên các skill được trang bị cho subagent từ danh sách [{skills_list_str}]"
  ],
  "assigned_subagent": {{
    "role": "data_engineer | backend_specialist | frontend_specialist | senior_debugger | refactor_architect | test_engineer | general_coder",
    "recommended_model": "gemini-3.8-flash-medium | claude-sonnet-4-6",
    "reason": "Lý do Manager chọn subagent và model này",
    "focus_instructions": "Chỉ đạo cụ thể của Manager gửi riêng cho Subagent này khi thực hiện"
  }},
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
(Mô tả các file hiện có liên quan, kinh nghiệm từ task trước và convention cần tuân thủ)

## 2. Manager Directive & Assigned Subagent
- **Assigned Role:** (Tên role subagent được phân công)
- **Recommended Model:** (Model được chỉ định)
- **Equipped Skills:** (Các skill được nạp: ví dụ api-design, testing-best-practices)
- **Key Focus:** (Trọng tâm kỹ thuật mà Subagent phải chú ý)

## 3. Implementation Steps
(Từng bước cụ thể: tạo file gì, sửa hàm nào, logic ra sao)

## 4. Test Strategy
(Các test cases cần viết để đảm bảo đúng tiêu chí nghiệm thu)

## 5. Verification
(Lệnh test kiểm tra cuối cùng)mplementation Plan — {task_id}

## 1. Inspect & Architecture
(Mô tả các file hiện có liên quan và convention cần tuân thủ)

## 2. Manager Directive & Assigned Subagent
- **Assigned Role:** (Tên role subagent được phân công)
- **Recommended Model:** (Model được chỉ định)
- **Key Focus:** (Trọng tâm kỹ thuật mà Subagent phải chú ý)

## 3. Implementation Steps
(Từng bước cụ thể: tạo file gì, sửa hàm nào, logic ra sao)

## 4. Test Strategy
(Các test cases cần viết để đảm bảo đúng tiêu chí nghiệm thu)

## 5. Verification
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


DEFAULT_PLANNER_MODELS = [
    "claude-opus-4-6-thinking",
    "claude-sonnet-4-6",
    "gemini-3.8-flash-medium",
]


def run_planner(
    user_prompt: str,
    repo_path: pathlib.Path,
    task_id: str,
    tasks_dir: pathlib.Path,
    mode: str,
    logs_dir: pathlib.Path,
    timeout_seconds: int = 600,
    models: list[str] | None = None,
) -> pathlib.Path:
    """Gọi Planner Subagent để khảo sát repo và tạo task.json + plan.md.

    Tự động fallback tuần tự theo danh sách models (mặc định: Opus Thinking -> Sonnet -> Gemini 3.8 Flash Medium).
    Trả về task_dir chứa 2 file đã tạo.
    """
    task_dir = (tasks_dir / task_id).resolve()
    task_dir.mkdir(parents=True, exist_ok=True)

    susu_home = tasks_dir.parent
    project_memory = knowledge_manager.load_repo_memory(repo_path, susu_home)
    project_docs = knowledge_manager.scan_project_docs(repo_path)
    available_skills = knowledge_manager.list_available_skills()

    if project_memory:
        print("🧠 [PROJECT MEMORY] Đã nạp kinh nghiệm tích lũy từ các task trước.")
    if project_docs:
        print("📖 [PROJECT DOCS] Đã nạp tài liệu kiến trúc dự án.")

    planner_prompt = build_planner_prompt(
        user_prompt=user_prompt,
        repo_path=repo_path,
        task_id=task_id,
        task_dir=task_dir,
        project_memory=project_memory,
        project_docs=project_docs,
        available_skills=available_skills,
    )

    timeout_flag = f"{timeout_seconds}s"
    agy_bin = agy_worker.get_agy_bin()
    add_dirs = ["--add-dir", str(repo_path.resolve()), "--add-dir", str(task_dir)]
    candidate_models = models if models else DEFAULT_PLANNER_MODELS

    last_error_log = None
    for idx, model in enumerate(candidate_models):
        print(f"\n[TECH LEAD MANAGER] Đang khảo sát repo & lập kế hoạch bằng Model: [{model}] (ưu tiên {idx + 1}/{len(candidate_models)})...")
        raw_log_path = logs_dir / f"{task_id}.planner.{model}.agy.log"
        last_error_log = raw_log_path
        model_flags = ["--model", model] if model else []

        if mode == "direct":
            argv = [
                agy_bin,
                "--dangerously-skip-permissions",
                *model_flags,
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
                *model_flags,
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
            model_str = f'--model "{model}" ' if model else ""
            inner = (
                f'"{agy_bin}" --dangerously-skip-permissions {model_str}'
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

        task_json_path = task_dir / "task.json"
        plan_md_path = task_dir / "plan.md"

        if exit_code == 0:
            # Trường hợp 1: agy đã tự tạo trực tiếp cả 2 file
            if task_json_path.exists() and plan_md_path.exists():
                try:
                    data = json.loads(task_json_path.read_text(encoding="utf-8"))
                    data["planned_by_model"] = model
                    task_json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                    print(f"✅ [TECH LEAD MANAGER] Đã lập kế hoạch & chỉ định Subagent thành công bằng Model: [{model}]!")
                    return task_dir
                except json.JSONDecodeError:
                    pass  # Nếu file json lỗi cú pháp, thử phục hồi từ stdout bên dưới

            # Trường hợp 2: Fallback phục hồi nếu agy in ra stdout
            parsed_json = _try_extract_json(output)
            if parsed_json:
                parsed_json["planned_by_model"] = model
                task_json_path.write_text(json.dumps(parsed_json, indent=2, ensure_ascii=False), encoding="utf-8")
                if not plan_md_path.exists():
                    plan_content = output.strip() or f"# Plan {task_id}\n\nThực hiện task: {user_prompt}"
                    plan_md_path.write_text(plan_content, encoding="utf-8")
                print(f"✅ [TECH LEAD MANAGER] Đã trích xuất kế hoạch & chỉ định Subagent thành công bằng Model: [{model}]!")
                return task_dir

        print(
            f"⚠️ [TECH LEAD MANAGER] Model [{model}] không hoàn thành hoặc gặp lỗi/hết quota (exit_code={exit_code})."
        )
        if idx < len(candidate_models) - 1:
            print(f"🔄 [TECH LEAD MANAGER] -> Đang tự động chuyển sang Model dự phòng tiếp theo: [{candidate_models[idx + 1]}]...")

    # Nếu tất cả các model đều thất bại nhưng có plan/task đã tạo từ trước
    task_json_path = task_dir / "task.json"
    plan_md_path = task_dir / "plan.md"
    if task_json_path.exists() and plan_md_path.exists():
        return task_dir

    raise PlannerError(
        f"Tất cả các model ({', '.join(candidate_models)}) đều thất bại khi lập kế hoạch. "
        f"Xem log gần nhất tại: {last_error_log}"
    )
