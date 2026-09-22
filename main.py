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
import datetime
import json
import pathlib
import sys

import agy_worker
import git_manager
from logger import TaskLogger
import planner
import test_runner

# Đảm bảo in tiếng Việt trên console Windows không bị UnicodeEncodeError
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
    parser = argparse.ArgumentParser(
        prog="susu",
        description="Susu — Multi-Agent AI Software Engineering CLI (Planner + Coder + Tester)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Ví dụ sử dụng:\n"
               "  susu \"Thêm hàm multiply(a, b) vào utils.py và viết test\"\n"
               "  susu -f task.md\n"
               "  susu -f requirements.txt --repo D:\\projects\\my_app\n"
               "  susu --task tasks/TASK-001\n",
    )
    parser.add_argument(
        "positional_prompt",
        nargs="?",
        help="Mô tả task tự nhiên (ví dụ: susu \"Thêm hàm multiply vào utils.py\")",
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="prompt_file",
        help="Đọc mô tả task từ file (ví dụ: susu -f task.md hoặc susu -f prompt.txt)",
    )
    parser.add_argument(
        "--prompt",
        "--task-desc",
        dest="flag_prompt",
        help="Mô tả task tự nhiên (tương đương với việc truyền chuỗi trực tiếp)",
    )
    parser.add_argument(
        "--task",
        dest="task",
        help="Thư mục task đã có sẵn plan.md và task.json (vd: tasks/TASK-001)",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Đường dẫn tới git repo đích (mặc định: thư mục hiện tại '.')",
    )
    parser.add_argument("--task-id", help="Mã task (tự sinh nếu không truyền khi dùng prompt)")
    parser.add_argument("--base-branch", default="main", help="Branch gốc để tạo nhánh agent/ (mặc định: main)")
    parser.add_argument("--timeout", type=int, default=1800, help="Timeout cho mỗi lần gọi agy (giây, mặc định: 1800)")
    args = parser.parse_args()

    user_prompt = None
    if args.prompt_file:
        p_file = pathlib.Path(args.prompt_file).resolve()
        if not p_file.exists():
            print(f"ERROR: Không tìm thấy file mô tả task '{p_file}'.")
            return 1
        user_prompt = p_file.read_text(encoding="utf-8").strip()
    else:
        user_prompt = args.flag_prompt or args.positional_prompt

    if not user_prompt and not args.task:
        parser.error(
            "Vui lòng cung cấp mô tả task (ví dụ: susu \"Thêm hàm X vào utils.py\"), "
            "hoặc dùng file với -f <file.md>, hoặc chỉ định thư mục task bằng --task <thư_mục>."
        )

    # Quản lý thư mục lưu trữ tập trung tại ~/.susu để không làm bẩn repo của người dùng
    susu_home = pathlib.Path.home() / ".susu"
    logs_dir = susu_home / "logs"
    tasks_dir = susu_home / "tasks"
    logs_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir.mkdir(parents=True, exist_ok=True)

    repo_path = pathlib.Path(args.repo).resolve()
    if not repo_path.exists():
        print(f"ERROR: Thư mục repo '{repo_path}' không tồn tại.")
        return 1

    # 1. Self-test agy MỘT LẦN khi khởi động
    print("=" * 60)
    print("AGY SELF-TEST STARTED (dò cách gọi phù hợp với máy này)")
    mode = agy_worker.self_test(repo_path, logs_dir)
    print(f"AGY SELF-TEST RESULT: mode={mode}")
    print("=" * 60)

    if mode == "unrecoverable":
        print(
            "ERROR: Không tìm được cách nào lấy output thật từ agy trên máy này. "
            "Kiểm tra `agy --version` hoặc cài winpty (Windows)."
        )
        return 1

    # 2. Xử lý Task: Nếu có prompt, gọi Planner Subagent
    if user_prompt:
        generated_id = args.task_id or f"TASK-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        print(f"\n[SUBAGENT 1: PLANNER] Khởi động Planner Subagent cho {generated_id}...")
        print(f"Yêu cầu: {user_prompt}")
        print(f"Repository: {repo_path}")
        try:
            task_dir = planner.run_planner(
                user_prompt=user_prompt,
                repo_path=repo_path,
                task_id=generated_id,
                tasks_dir=tasks_dir,
                mode=mode,
                logs_dir=logs_dir,
            )
            print(f"[SUBAGENT 1: PLANNER] Đã lập kế hoạch thành công tại: {task_dir}\n")
        except Exception as exc:
            print(f"ERROR khi chạy Planner Subagent: {exc}")
            return 1
    else:
        task_dir = pathlib.Path(args.task).resolve()

    task = load_task(task_dir)
    task_id = task.get("task_id", task_dir.name)

    logger = TaskLogger(task_id, logs_dir)
    logger.section(f"TASK {task_id} CREATED")
    logger.log(f"repo={repo_path}")
    logger.log(f"task_dir={task_dir}")
    logger.log(f"title={task.get('title', '')}")

    try:
        # --- 1. Git branch cô lập ---
        git_manager.ensure_clean_worktree(repo_path, args.base_branch)
        branch = git_manager.create_task_branch(repo_path, task_id, args.base_branch)
        logger.log(f"BRANCH CREATED: {branch}")

        logger.log(f"AGY MODE: {mode}")

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
