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
import re
import sys
import unicodedata

import agy_worker
import git_manager
import knowledge_manager
from logger import TaskLogger
import notebooklm_bridge
import planner
import subagent_roles
import test_runner

VI_EN_PHRASES: list[tuple[str, str]] = [
    (r"\bth[eê]m\b|\bt[aạ]o\b|\bvi[eế]t\b|\bx[aâ]y d[uự]ng\b", "add"),
    (r"\bs[uử]a\b|\bfix\b|\bv[aá]\b|\bkh[aắ]c ph[uụ]c\b", "fix"),
    (r"\bx[oó]a\b|\bb[oỏ]\b|\blo[aạ]i b[oỏ]\b", "remove"),
    (r"\bt[oố]i [uư]u( h[oó]a)?\b", "optimize"),
    (r"\bt[aá]i c[aấ]u tr[uú]c\b|\brefactor\b", "refactor"),
    (r"\bc[aậ]p nh[aậ]t\b|\bupdate\b", "update"),
    (r"\bn[aâ]ng c[aấ]p\b|\bupgrade\b", "upgrade"),
    (r"\bki[eể]m th[uử]\b|\bki[eể]m tra\b|\btest\b", "test"),
    (r"\bh[aà]m\b|\bph[uư][oơ]ng th[uứ]c\b", "func"),
    (r"\bch[uứ]c n[aă]ng\b|\bt[ií]nh n[aă]ng\b", "feat"),
    (r"\bgiao di[eệ]n\b", "ui"),
    (r"\bl[oỗ]i\b", "bug"),
    (r"\bthanh to[aá]n\b", "payment"),
    (r"\bx[aá]c th[uự]c\b|\bph[aâ]n quy[eề]n\b", "auth"),
    (r"\bng[uư][oờ]i d[uù]ng\b|\bt[aà]i kho[aả]n\b", "user"),
    (r"\bb[aả]o m[aậ]t\b", "security"),
    (r"\bc[oơ] s[oở] d[uữ] li[eệ]u\b|\bcsdl\b", "db"),
    (r"\bd[uữ] li[eệ]u\b", "data"),
    (r"\bc[aấ]u h[iì]nh\b", "config"),
    (r"\bt[aà]i li[eệ]u\b", "docs"),
    (r"\bt[iì]m ki[eế]m\b", "search"),
    (r"\bb[oộ] nh[oớ] đ[eệ]m\b", "cache"),
    (r"\bb[oộ] nh[oớ]\b|\bram\b|\bmemory\b", "memory"),
    (r"\bđ[oọ]c\b|\bread\b", "read"),
    (r"\bl[uư]u tr[uữ]\b|\bl[uư]u\b|\bstore\b", "store"),
    (r"\bgiao d[iị]ch\b|\btransaction\b", "transaction"),
    (r"\bđ[uư][oờ]ng [oố]ng\b|\bpipeline\b", "pipeline"),
    (r"\bx[uử] l[yý]\b|\btransform\b", "transform"),
    (r"\bl[aà]m s[aạ]ch\b|\bclean\b", "clean"),
    (r"\btr[ií]ch xu[aấ]t\b|\bextract\b", "extract"),
    (r"\bn[aạ]p\b|\bt[aả]i\b|\bload\b", "load"),
    (r"\bkho d[uữ] li[eệ]u\b|\bdwh\b|\bwarehouse\b", "dwh"),
    (r"\bh[oồ] d[uữ] li[eệ]u\b|\blakehouse\b|\bdatalake\b", "lakehouse"),
    (r"\bch[aấ]t l[uư][oợ]ng d[uữ] li[eệ]u\b|\bdata quality\b", "data-quality"),
    (r"\bph[aâ]n v[uù]ng\b|\bpartition\b", "partition"),
    (r"\bch[aạ]y l[aạ]i\b|\bbackfill\b", "backfill"),
    (r"\bchuy[eể]n đ[oổ]i\b|\bconvert\b", "convert"),
]

STOP_WORDS = {
    "va", "vao", "cho", "cua", "de", "la", "cac", "mot", "nhung", "voi", "trong", "tren", "khi", "duoc", "ra",
    "lam", "theo", "dung", "bang", "nhu", "lai", "rat", "qua", "co", "nay",
    "and", "or", "the", "a", "an", "in", "on", "at", "to", "for", "of", "with", "by", "from",
}


def slugify_text(text: str, max_words: int = 5, max_length: int = 38) -> str:
    """Tạo slug chuẩn tiếng Anh ngắn gọn (kebab-case), an toàn cho Git branch."""
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        text = line.lstrip("#").strip()
        break

    lower_text = text.lower()
    for pattern, repl in VI_EN_PHRASES:
        lower_text = re.sub(pattern, f" {repl} ", lower_text)

    lower_text = lower_text.replace("đ", "d").replace("Đ", "D")
    norm = "".join(c for c in unicodedata.normalize("NFD", lower_text) if unicodedata.category(c) != "Mn")
    ascii_clean = re.sub(r"[^\w\s-]", " ", norm).strip().lower()
    words = [w for w in re.split(r"[\s_]+", ascii_clean) if w and w not in STOP_WORDS]
    slug = "-".join(words[:max_words])
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "task"


def generate_semantic_task_id(user_prompt: str, tasks_dir: pathlib.Path | None = None) -> str:
    """Tạo task_id chuẩn tiếng Anh từ nội dung prompt, ví dụ: TASK-20260925-add-func-format-currency."""
    now_date = datetime.datetime.now().strftime("%Y%m%d")
    now_time = datetime.datetime.now().strftime("%H%M")
    slug = slugify_text(user_prompt)
    candidate = f"TASK-{now_date}-{slug}"
    # Nếu task trùng tên đã tồn tại trong ngày, thêm giờ phút để đảm bảo tính duy nhất
    if tasks_dir and (tasks_dir / candidate).exists():
        return f"TASK-{now_date}-{now_time}-{slug}"
    return candidate

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


def load_project_config(repo_path: pathlib.Path) -> dict:
    """Nạp cấu hình riêng của project từ .susu.json hoặc .susu.yaml (nếu có)."""
    json_cfg = repo_path / ".susu.json"
    if json_cfg.is_file():
        try:
            return json.loads(json_cfg.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] Không đọc được file .susu.json: {e}")
    yaml_cfg = repo_path / ".susu.yaml"
    if yaml_cfg.is_file():
        try:
            import yaml
            return yaml.safe_load(yaml_cfg.read_text(encoding="utf-8")) or {}
        except ImportError:
            # Fallback đọc key: value đơn giản nếu chưa cài pyyaml
            cfg = {}
            for line in yaml_cfg.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and ":" in line:
                    k, v = line.split(":", 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
            return cfg
        except Exception as e:
            print(f"[WARN] Không đọc được file .susu.yaml: {e}")
    return {}


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


def build_initial_prompt(
    task: dict,
    skills_content: str = "",
    project_memory: str = "",
    project_docs: str = "",
) -> str:
    assigned = task.get("assigned_subagent", {})
    role_name = assigned.get("role", "general_coder")
    role_def = subagent_roles.get_role_definition(role_name)
    role_title = role_def.get("title", "Software Engineer Subagent")
    guidelines = "\n".join(f"- {g}" for g in role_def.get("guidelines", []))
    manager_focus = assigned.get("focus_instructions", "")

    requirements = "\n".join(f"- {r}" for r in task.get("requirements", []))
    acceptance = "\n".join(f"- {a}" for a in task.get("acceptance_criteria", []))
    focus_section = f"\n- CHỈ ĐẠO TRỌNG TÂM TỪ MANAGER: {manager_focus}" if manager_focus else ""

    memory_section = f"\n# 🧠 KINH NGHIỆM ĐÃ TÍCH LŨY CỦA DỰ ÁN (PROJECT MEMORY):\n{project_memory}\n" if project_memory else ""
    skills_section = f"\n# 📚 CẨM NANG KỸ NĂNG CHUYÊN SÂU ĐƯỢC TRANG BỊ:\n{skills_content}\n" if skills_content else ""
    docs_section = f"\n{project_docs}\n" if project_docs else ""

    return f"""Bạn là {role_title} được Tech Lead / Manager Agent chỉ định thực hiện task này.
Không cần hỏi lại người dùng — hãy tự đọc repository hiện tại và triển khai
chính xác theo kế hoạch và tiêu chuẩn kỹ thuật dưới đây.

# VAI TRÒ & NGUYÊN TẮC CHUYÊN MÔN CỦA BẠN ({role_title}):
{guidelines}{focus_section}
{memory_section}{skills_section}{docs_section}
# Task: {task.get('title', task.get('task_id'))}

## Mô tả
{task.get('description', '')}

## Yêu cầu
{requirements}

## Tiêu chí nghiệm thu
{acceptance}

## Kế hoạch implementation (do Tech Lead Manager phê duyệt)
{task['_plan_md']}

## Việc bạn cần làm
1. Đọc code hiện có trong repository để hiểu convention đang dùng.
2. Tuân thủ nghiêm ngặt nguyên tắc chuyên môn của vai trò {role_title} và các Skill được nạp.
3. Implement đúng theo kế hoạch ở trên, không tự ý mở rộng phạm vi.
4. Sau khi implement xong, DỪNG LẠI. Không cần tự chạy test hay tự commit
   — phần đó do hệ thống bên ngoài đảm nhiệm.
5. Không được: chạm vào credential thật, gọi API production, xoá dữ liệu,
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
    parser.add_argument(
        "--rollback",
        dest="rollback_task_id",
        help="Huỷ bỏ nhanh branch của một task và khôi phục về branch gốc (ví dụ: susu --rollback TASK-001)",
    )
    parser.add_argument(
        "--force",
        "-y",
        "--yes",
        dest="force",
        action="store_true",
        help="Bỏ qua cảnh báo xác nhận khi gặp task rủi ro cao (HIGH RISK)",
    )
    parser.add_argument(
        "--auto-commit",
        dest="auto_commit",
        action="store_true",
        help="Tự động commit khi test PASS (mặc định: tắt để bạn tự review code)",
    )
    parser.add_argument(
        "--coder-model",
        default=None,
        help="Model cho Coder Subagent (mặc định: gemini-3.8-flash-medium)",
    )
    parser.add_argument(
        "--planner-models",
        default=None,
        help="Danh sách model fallback cho Planner, phân cách bằng dấu phẩy (mặc định: claude-opus-4-6-thinking,claude-sonnet-4-6,gemini-3.8-flash-medium)",
    )
    parser.add_argument("--task-id", help="Mã task (tự sinh nếu không truyền khi dùng prompt)")
    parser.add_argument("--base-branch", default=None, help="Branch gốc để tạo nhánh agent/ (mặc định: main)")
    parser.add_argument("--timeout", type=int, default=None, help="Timeout cho mỗi lần gọi agy (giây, mặc định: 1800)")
    parser.add_argument(
        "--knowledge-dir",
        "-k",
        dest="knowledge_dir",
        default=None,
        help="Đường dẫn thư mục kho tri thức, schema, hoặc NotebookLM export (ví dụ: ./knowledge hoặc D:\\notes\\notebooklm)",
    )
    parser.add_argument(
        "--notebooklm-login",
        action="store_true",
        help="Mở trình duyệt để đăng nhập tài khoản Google vào NotebookLM (1 lần duy nhất)",
    )
    parser.add_argument(
        "--notebook-id",
        dest="notebook_id",
        default=None,
        help="Notebook ID hoặc URL từ Google NotebookLM để truy vấn RAG trực tiếp vào tri thức",
    )
    args = parser.parse_args()

    # 0.1 Xử lý đăng nhập Google NotebookLM nếu được yêu cầu
    if args.notebooklm_login:
        success = notebooklm_bridge.run_login()
        return 0 if success else 1

    repo_path = pathlib.Path(args.repo).resolve()
    if not repo_path.exists():
        print(f"ERROR: Thư mục repo '{repo_path}' không tồn tại.")
        return 1

    # Nạp cấu hình riêng của project từ .susu.json hoặc .susu.yaml (nếu có)
    project_config = load_project_config(repo_path)
    base_branch = args.base_branch or project_config.get("base_branch", "main")
    task_timeout = args.timeout or project_config.get("timeout", 1800)
    auto_commit = args.auto_commit or project_config.get("auto_commit", False)

    coder_model = (
        args.coder_model
        or project_config.get("coder_model")
        or agy_worker.DEFAULT_CODER_MODEL
    )
    if args.planner_models:
        planner_models = [m.strip() for m in args.planner_models.split(",") if m.strip()]
    elif "planner_models" in project_config:
        planner_models = project_config["planner_models"]
    else:
        planner_models = planner.DEFAULT_PLANNER_MODELS

    # Thu thập các thư mục tri thức bổ sung (CLI flag hoặc .susu.json)
    extra_knowledge_dirs: list[pathlib.Path | str] = []
    if args.knowledge_dir:
        extra_knowledge_dirs.append(args.knowledge_dir)
    cfg_kdirs = project_config.get("knowledge_dirs") or project_config.get("knowledge_dir")
    if cfg_kdirs:
        if isinstance(cfg_kdirs, list):
            extra_knowledge_dirs.extend(cfg_kdirs)
        elif isinstance(cfg_kdirs, str):
            extra_knowledge_dirs.append(cfg_kdirs)

    # Nhận diện Google NotebookLM ID (qua cờ CLI hoặc .susu.json)
    notebook_id = (
        args.notebook_id
        or project_config.get("notebook_id")
        or (project_config.get("notebooklm", {}).get("notebook_id") if isinstance(project_config.get("notebooklm"), dict) else None)
    )

    # 0. Xử lý lệnh Rollback nếu được gọi
    if args.rollback_task_id:
        try:
            msg = git_manager.rollback_task(repo_path, args.rollback_task_id, base_branch)
            print(f"[ROLLBACK] {msg}")
            return 0
        except Exception as exc:
            print(f"ERROR: {exc}")
            return 1

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
        generated_id = args.task_id or generate_semantic_task_id(user_prompt, tasks_dir)
        print("\n" + "=" * 60)
        print(f"[BƯỚC 1: TECH LEAD MANAGER — LẬP KẾ HOẠCH & TUYỂN CHỌN SUBAGENT]")
        print(f"  • Task ID: {generated_id}")
        print(f"  • Branch dự kiến: agent/{generated_id}")
        print(f"  • Yêu cầu: {user_prompt}")
        print(f"  • Repository: {repo_path}")
        print(f"  • Chuỗi Model Manager ưu tiên: {' -> '.join(planner_models)}")
        print("=" * 60)
        try:
            task_dir = planner.run_planner(
                user_prompt=user_prompt,
                repo_path=repo_path,
                task_id=generated_id,
                tasks_dir=tasks_dir,
                mode=mode,
                logs_dir=logs_dir,
                timeout_seconds=600,
                models=planner_models,
                extra_knowledge_dirs=extra_knowledge_dirs,
                notebook_id=notebook_id,
            )
            print(f"\n[BƯỚC 1 HOÀN TẤT] Bản kế hoạch và phân công đã lưu tại: {task_dir}")
        except Exception as exc:
            print(f"ERROR khi chạy Tech Lead Manager: {exc}")
            return 1
    else:
        task_dir = pathlib.Path(args.task).resolve()

    task = load_task(task_dir)
    task_id = task.get("task_id", task_dir.name)
    planned_by = task.get("planned_by_model", planner_models[0] if planner_models else "N/A")

    # 3. Phân loại và tuyển chọn Subagent từ Tech Lead Manager
    assigned = task.get("assigned_subagent", {})
    role_name = assigned.get("role", "general_coder")
    role_def = subagent_roles.get_role_definition(role_name)
    role_title = role_def.get("title", "General Coder")
    role_desc = role_def.get("description", "")
    recommended_model = assigned.get("recommended_model") or role_def.get("default_model", agy_worker.DEFAULT_CODER_MODEL)

    # Độ ưu tiên Model: Cờ dòng lệnh --coder-model > .susu.json coder_model > Đề xuất của Manager > Mặc định hệ thống
    if args.coder_model:
        active_coder_model = args.coder_model
    elif "coder_model" in project_config:
        active_coder_model = project_config["coder_model"]
    else:
        active_coder_model = recommended_model

    # Nạp 3 Tầng Tri thức: Skills, Project Memory và Kho Tri thức / NotebookLM / Schemas
    relevant_skills = task.get("relevant_skills", [])
    skills_content = knowledge_manager.load_selected_skills(relevant_skills)
    project_memory = knowledge_manager.load_repo_memory(repo_path, susu_home)
    project_docs, loaded_docs = knowledge_manager.scan_project_docs(
        repo_path=repo_path,
        extra_dirs=extra_knowledge_dirs,
        susu_home=susu_home,
        notebook_id=notebook_id,
        user_prompt=user_prompt or task.get("title", ""),
    )

    print("\n" + "=" * 60)
    print(f"[BƯỚC 2: MANAGER PHÂN CÔNG SUBAGENT THỰC THI]")
    print(f"  • Lập kế hoạch bởi: Tech Lead Manager (Model: [{planned_by}])")
    print(f"  • Subagent được giao việc: {role_title} ({role_name})")
    print(f"  • Chuyên môn: {role_desc}")
    print(f"  • Model Subagent đảm nhiệm: [{active_coder_model}]")
    if relevant_skills:
        print(f"  • Kỹ năng được trang bị (Skills): {', '.join(relevant_skills)}")
    if project_memory:
        print("  • Tích lũy kinh nghiệm: Đã kết nối với Project Memory")
    if loaded_docs:
        print(f"  • Kho tri thức & NotebookLM: Đã nạp {len(loaded_docs)} tài liệu ({', '.join(loaded_docs[:3])}{'...' if len(loaded_docs) > 3 else ''})")
    if assigned.get("reason"):
        print(f"  • Lý do Manager chọn: {assigned['reason']}")
    if assigned.get("focus_instructions"):
        print(f"  • Chỉ đạo trọng tâm: {assigned['focus_instructions']}")
    print("=" * 60 + "\n")

    # 4. Phân loại và cảnh báo mức độ rủi ro (Risk Classification)
    risk_level = task.get("risk_level", "LOW").upper()
    risk_reasons = task.get("risk_reasons", [])
    if risk_level == "HIGH":
        print("\n" + "!" * 60)
        print("⚠️  CẢNH BÁO AN TOÀN: Task này được xếp loại RỦI RO CAO (HIGH RISK)!")
        if risk_reasons:
            print("Lý do cảnh báo:")
            for r in risk_reasons:
                print(f"  • {r}")
        print("!" * 60 + "\n")
        if not args.force and sys.stdin.isatty():
            try:
                ans = input("Bạn có muốn tiếp tục cho Agent triển khai không? [y/N]: ").strip().lower()
                if ans not in ("y", "yes"):
                    print("Đã huỷ bỏ triển khai task theo yêu cầu người dùng.")
                    return 0
            except (EOFError, KeyboardInterrupt):
                print("\nĐã huỷ bỏ triển khai task.")
                return 0

    logger = TaskLogger(task_id, logs_dir)
    logger.section(f"TASK {task_id} CREATED")
    logger.log(f"repo={repo_path}")
    logger.log(f"task_dir={task_dir}")
    logger.log(f"title={task.get('title', '')}")
    logger.log(f"risk_level={risk_level}")
    logger.log(f"planner_model={planned_by}")
    logger.log(f"subagent_role={role_title} ({role_name})")
    logger.log(f"subagent_model={active_coder_model}")
    if relevant_skills:
        logger.log(f"equipped_skills={', '.join(relevant_skills)}")
    if loaded_docs:
        logger.log(f"loaded_knowledge={', '.join(loaded_docs)}")

    try:
        # --- 1. Git branch cô lập ---
        git_manager.ensure_clean_worktree(repo_path, base_branch)
        branch = git_manager.create_task_branch(repo_path, task_id, base_branch)
        logger.log(f"BRANCH CREATED: {branch}")

        logger.log(f"AGY MODE: {mode}")

        initial_prompt = build_initial_prompt(
            task=task,
            skills_content=skills_content,
            project_memory=project_memory,
            project_docs=project_docs,
        )
        current_prompt = initial_prompt
        commit_hash = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            logger.section(f"ATTEMPT {attempt}/{MAX_ATTEMPTS}")
            print(f"🚀 [SUBAGENT ĐANG CODE] {role_title} | Model: [{active_coder_model}] | Lần thử: {attempt}/{MAX_ATTEMPTS}")
            logger.log(f"SUBAGENT STARTED: {role_title} (model={active_coder_model})")

            agy_result = agy_worker.run_agy(
                prompt=current_prompt,
                workdir=repo_path,
                logs_dir=logs_dir,
                task_id=task_id,
                mode=mode,
                attempt=attempt,
                timeout_seconds=task_timeout,
                model=active_coder_model,
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

            # --- 2.5. Kiểm tra an toàn: Protected Paths & Diff Size Guard ---
            try:
                git_manager.check_protected_paths(repo_path, project_config.get("protected_paths"))
                max_lines = project_config.get("max_diff_lines", 1000)
                max_files = project_config.get("max_files_changed", 30)
                files_cnt, lines_cnt = git_manager.check_diff_size(repo_path, max_lines, max_files)
                logger.log(f"SAFETY CHECK PASSED: {files_cnt} files, {lines_cnt} lines changed.")
            except (git_manager.GitSecurityError, git_manager.DiffSizeLimitError) as sec_exc:
                logger.log(f"SECURITY/GUARD ALERT: {sec_exc}")
                logger.log("Tự động khôi phục working tree về trạng thái sạch (reset hard)...")
                git_manager.reset_hard(repo_path)
                logger.section(f"TASK {task_id} FAILED (Bị chặn bởi Safety Guard)")
                return 1

            # --- 3. Orchestrator tự verify, không tin agy tự báo cáo ---
            logger.log("TEST STARTED")
            test_commands = project_config.get("test_commands") or task.get("test_commands", [])
            test_result = test_runner.run_tests(test_commands, repo_path)

            if test_result.passed:
                logger.log("TEST PASSED")

                # Tự động đúc kết và cập nhật kinh nghiệm vào Project Memory
                try:
                    knowledge_manager.record_task_learnings(repo_path, susu_home, task, changed_files, attempt)
                    logger.log("PROJECT MEMORY UPDATED")
                    print("🧠 [KNOWLEDGE UPDATED] Đã đúc kết bài học và cập nhật vào Project Memory!")
                except Exception as mem_exc:
                    logger.log(f"WARN: Không thể cập nhật memory: {mem_exc}")

                if auto_commit:
                    commit_message = f"[agent] {task_id} (attempt {attempt}): {task.get('title', '')}"
                    commit_hash = git_manager.commit_all(repo_path, commit_message)
                    logger.log(f"COMMIT CREATED: {commit_hash}")
                    logger.section(f"TASK {task_id} COMPLETED (attempt {attempt})")
                else:
                    logger.log("CHẾ ĐỘ REVIEW: Không tự động commit để bạn tự kiểm tra code.")
                    logger.log(f"Code đã sẵn sàng trên branch '{branch}'.")
                    logger.log("Bạn có thể kiểm tra qua: git diff / git status")
                    logger.log(f"Nếu đồng ý, commit bằng: git add -A && git commit -m '[agent] {task_id}: {task.get('title', '')}'")
                    logger.log(f"Nếu muốn huỷ bỏ: susu --rollback {task_id}")
                    logger.section(f"TASK {task_id} READY FOR REVIEW")
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
