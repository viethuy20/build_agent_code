"""
Orchestrator MVP v0.2

Thay đổi so với v0.1:
  - Chạy self-test agy MỘT LẦN khi khởi động, cache lại cách gọi phù hợp
    với máy hiện tại (direct / pty / winpty), dùng chung cho mọi attempt.
  - Thêm vòng tự sửa lỗi GIỚI HẠN TỐI ĐA 1 LẦN: nếu attempt 1 implement
    xong nhưng test FAIL (do code sai, không phải lỗi hạ tầng agy), gom
    log lỗi gửi lại cho agy kèm yêu cầu sửa, rồi test lại đúng 1 lần cuối.
  - Lỗi hạ tầng (agy crash/timeout/stdout rỗng) KHÔNG được retry — vì
    retry sẽ gặp lại đúng lỗi đó, tốn quota vô ích.

Flow:
  1. Đọc task.json + plan.md
  2. Tạo git branch agent/<TASK_ID>
  3. self_test() xác định cách gọi agy
  4. Attempt 1: build prompt gốc -> gọi agy -> orchestrator tự chạy test
  5. Nếu FAIL do code sai -> Attempt 2: build prompt kèm log lỗi -> gọi agy
     -> test lại LẦN CUỐI
  6. PASS ở bất kỳ attempt nào -> commit. FAIL ở attempt cuối -> dừng hẳn,
     giữ nguyên log của cả 2 lần để debug thủ công.

Cách chạy: giống v0.1
  python orchestrator/main.py --task tasks/TASK-001 --repo /path/to/repo
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import agy_worker
import git_manager
import test_runner
from logger import TaskLogger

MAX_ATTEMPTS = 2  # hardcode có chủ đích — xem lý do trong README


def load_task(task_dir: pathlib.Path) -> dict:
    task_json_path = task_dir / "task.json"
    plan_md_path = task_dir / "plan.md"

    if not task_json_path.exists():
        raise FileNotFoundError(f"Không tìm thấy {task_json_path}")
    if not plan_md_path.exists():
        raise FileNotFoundError(f"Không tìm thấy {plan_md_path}")

    task = json.loads(task_json_path.read_text(encoding="utf-8"))
    task["_plan_md"] = plan_md_path.read_text(encoding="utf-8")
    return task


def build_initial_prompt(task: dict) -> str:
    requirements = "\n".join(f"- {r}" for r in task.get("requirements", []))
    acceptance = "\n".join(f"- {a}" for a in task.get("acceptance_criteria", []))

    return f"""Bạn là implementation worker cho một task Data Engineering.
Không cần hỏi lại người dùng — hãy tự đọc repository hiện tại và implement
theo đúng kế hoạch dưới đây.

# Task: {task.get('title', task.get('task_id'))}

## Mô tả
{task.get('description', '')}

## Yêu cầu
{requirements}

## Tiêu chí nghiệm thu
{acceptance}

## Kế hoạch implementation (đã được duyệt trước)
{task['_plan_md']}

## Việc bạn cần làm
1. Đọc code hiện có trong repository để hiểu convention đang dùng.
2. Implement đúng theo kế hoạch ở trên, không tự ý mở rộng phạm vi.
3. Sau khi implement xong, DỪNG LẠI. Không cần tự chạy test hay tự commit
   — phần đó do hệ thống bên ngoài đảm nhiệm.
4. Không được: chạm vào credential thật, gọi API production, xoá dữ liệu,
   force-push, hoặc thay đổi file ngoài phạm vi task này.
"""


def build_fix_prompt(initial_prompt: str, test_command: str, test_output: str) -> str:
    return f"""{initial_prompt}

## CẬP NHẬT: lần implement trước đã chạy test và bị FAIL

Đây là LẦN SỬA LỖI, không phải implement lại từ đầu. Giữ nguyên các phần
code đã đúng, chỉ sửa phần gây lỗi dưới đây.

### Lệnh test đã fail
{test_command}

### Log lỗi đầy đủ
{test_output}

Hãy phân tích log lỗi trên, xác định nguyên nhân, và sửa code cho đúng.
Sau khi sửa xong, DỪNG LẠI — không tự chạy lại test.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="DE Agent Orchestrator MVP v0.2")
    parser.add_argument("--task", required=True, help="Thư mục task, vd: tasks/TASK-001")
    parser.add_argument("--repo", required=True, help="Đường dẫn tới git repo đích")
    parser.add_argument("--base-branch", default="main", help="Branch gốc để tạo nhánh agent/")
    parser.add_argument("--timeout", type=int, default=1800, help="Timeout cho mỗi lần gọi agy (giây)")
    args = parser.parse_args()

    project_root = pathlib.Path(__file__).resolve().parent.parent
    task_dir = pathlib.Path(args.task).resolve()
    repo_path = pathlib.Path(args.repo).resolve()
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    task = load_task(task_dir)
    task_id = task.get("task_id", task_dir.name)

    logger = TaskLogger(task_id, logs_dir)
    logger.section(f"TASK {task_id} CREATED")
    logger.log(f"repo={repo_path}")
    logger.log(f"task_dir={task_dir}")

    try:
        # --- 1. Git branch cô lập ---
        git_manager.ensure_clean_worktree(repo_path)
        branch = git_manager.create_task_branch(repo_path, task_id, args.base_branch)
        logger.log(f"BRANCH CREATED: {branch}")

        # --- 2. Self-test agy MỘT LẦN, cache mode cho toàn bộ lần chạy ---
        logger.log("AGY SELF-TEST STARTED (dò cách gọi phù hợp với máy này)")
        mode = agy_worker.self_test(repo_path, logs_dir)
        logger.log(f"AGY SELF-TEST RESULT: mode={mode}")
        if mode == "unrecoverable":
            logger.log(
                "Không tìm được cách nào lấy output thật từ agy trên máy này. "
                "Kiểm tra `agy --version` hoặc cài winpty (Windows)."
            )
            logger.section(f"TASK {task_id} FAILED")
            return 1

        initial_prompt = build_initial_prompt(task)
        current_prompt = initial_prompt
        commit_hash = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            logger.section(f"ATTEMPT {attempt}/{MAX_ATTEMPTS}")
            logger.log("GEMINI/AGY STARTED")

            agy_result = agy_worker.run_agy(
                prompt=current_prompt,
                workdir=repo_path,
                logs_dir=logs_dir,
                task_id=task_id,
                mode=mode,
                attempt=attempt,
                timeout_seconds=args.timeout,
            )

            if not agy_result.ok:
                logger.log("GEMINI/AGY FAILED")
                logger.log(f"REASON: {agy_result.note}")
                if agy_result.is_infra_error:
                    logger.log(
                        "Đây là lỗi hạ tầng (không phải code sai) -> KHÔNG retry, "
                        "vì attempt sau sẽ gặp lại đúng lỗi này."
                    )
                logger.section(f"TASK {task_id} FAILED")
                return 1

            logger.log("GEMINI/AGY FINISHED")

            changed_files = git_manager.diff_stat(repo_path)
            logger.log(f"FILES CHANGED:\n{changed_files or '(không có thay đổi nào được ghi nhận)'}")

            if not git_manager.has_uncommitted_changes(repo_path):
                logger.log("Agy không tạo ra thay đổi nào trong repo.")
                logger.section(f"TASK {task_id} FAILED")
                return 1

            # --- 3. Orchestrator tự verify, không tin agy tự báo cáo ---
            logger.log("TEST STARTED")
            test_result = test_runner.run_tests(task.get("test_commands", []), repo_path)

            if test_result.passed:
                logger.log("TEST PASSED")
                commit_message = f"[agent] {task_id} (attempt {attempt}): {task.get('title', '')}"
                commit_hash = git_manager.commit_all(repo_path, commit_message)
                logger.log(f"COMMIT CREATED: {commit_hash}")
                logger.section(f"TASK {task_id} COMPLETED (attempt {attempt})")
                return 0

            logger.log("TEST FAILED")
            logger.log(f"COMMAND: {test_result.command}")
            logger.log(f"OUTPUT:\n{test_result.output}")

            if attempt >= MAX_ATTEMPTS:
                logger.section(f"TASK {task_id} FAILED (đã hết {MAX_ATTEMPTS} lần thử)")
                logger.log(
                    f"Không commit. Code lỗi vẫn nằm trên branch {branch} "
                    "để bạn xem xét bằng tay."
                )
                return 1

            # Chuẩn bị prompt sửa lỗi cho attempt tiếp theo
            logger.log("Chuẩn bị prompt sửa lỗi cho attempt tiếp theo...")
            current_prompt = build_fix_prompt(
                initial_prompt, test_result.command, test_result.output
            )

        return 1  # không nên tới đây, nhưng để an toàn

    except (git_manager.GitError, agy_worker.AgyNotAvailable, FileNotFoundError) as exc:
        logger.log(f"ERROR: {exc}")
        logger.section(f"TASK {task_id} FAILED")
        return 1
    finally:
        logger.close()


if __name__ == "__main__":
    sys.exit(main())
