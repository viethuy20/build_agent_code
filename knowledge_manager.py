"""Knowledge Manager: Quản lý 3 tầng tri thức cho hệ thống Susu.

Tầng 1: Bộ nhớ tích lũy kinh nghiệm theo dự án (Project Memory & Lessons Learned).
Tầng 2: Thư viện Kỹ năng chuyên sâu (Skills Library / Recipes).
Tầng 3: Quét và nạp tài liệu kiến trúc dự án / NotebookLM exports (Project Docs).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import pathlib
import re
from typing import Any

# Thư mục chứa skills dựng sẵn đi kèm mã nguồn Susu
BUILTIN_SKILLS_DIR = pathlib.Path(__file__).parent / "skills"


def get_repo_identifier(repo_path: pathlib.Path) -> str:
    """Tạo định danh duy nhất, an toàn cho repository dựa trên tên thư mục và hash đường dẫn."""
    repo_resolved = repo_path.resolve()
    repo_name = re.sub(r"[^\w-]", "_", repo_resolved.name).lower()
    path_hash = hashlib.md5(str(repo_resolved).encode("utf-8")).hexdigest()[:6]
    return f"{repo_name}_{path_hash}"


# ==============================================================================
# TẦNG 1: BỘ NHỚ KINH NGHIỆM DỰ ÁN (PROJECT MEMORY)
# ==============================================================================

def get_memory_file_path(repo_path: pathlib.Path, susu_home: pathlib.Path) -> pathlib.Path:
    """Tìm hoặc tạo đường dẫn lưu file memory của dự án."""
    # Ưu tiên 1: Nếu repo có thư mục .susu/ thì lưu cục bộ ngay trong repo
    local_susu = repo_path / ".susu"
    if local_susu.is_dir():
        return local_susu / "memory.md"

    # Ưu tiên 2: Lưu tập trung tại ~/.susu/memory/<repo_id>.md
    memory_dir = susu_home / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    repo_id = get_repo_identifier(repo_path)
    return memory_dir / f"{repo_id}.md"


def load_repo_memory(repo_path: pathlib.Path, susu_home: pathlib.Path) -> str:
    """Đọc toàn bộ kinh nghiệm đã tích lũy từ các task trước của repo này."""
    mem_file = get_memory_file_path(repo_path, susu_home)
    if mem_file.is_file():
        try:
            return mem_file.read_text(encoding="utf-8").strip()
        except Exception:
            return ""
    return ""


def record_task_learnings(
    repo_path: pathlib.Path,
    susu_home: pathlib.Path,
    task: dict[str, Any],
    changed_files: str = "",
    attempt: int = 1,
) -> None:
    """Tự động đúc kết kinh nghiệm sau khi task hoàn thành thành công và lưu vào Memory."""
    mem_file = get_memory_file_path(repo_path, susu_home)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    task_id = task.get("task_id", "UNKNOWN")
    title = task.get("title", "")
    role = task.get("assigned_subagent", {}).get("role", "general_coder")
    test_cmds = ", ".join(task.get("test_commands", []))

    # Đọc nội dung hiện tại
    current_content = ""
    if mem_file.is_file():
        try:
            current_content = mem_file.read_text(encoding="utf-8").strip()
        except Exception:
            current_content = ""

    header = f"# Project Memory & Lessons Learned — {repo_path.name}\n\n"
    if not current_content:
        current_content = header

    # Trích xuất danh sách file thay đổi gọn gàng
    files_summary = []
    if changed_files:
        for line in changed_files.splitlines():
            line = line.strip()
            if line and not line.startswith("(") and "|" in line:
                files_summary.append(line.split("|")[0].strip())
    files_str = ", ".join(files_summary[:5]) if files_summary else "N/A"

    new_entry = f"""
### [{now_str}] Task: {task_id} — {title}
- **Subagent:** `{role}` (Hoàn thành ở attempt {attempt})
- **Files chính tác động:** `{files_str}`
- **Lệnh test đã verify:** `{test_cmds}`
- **Ghi chú kiến trúc:** Tuân thủ convention hiện có trong repo, test suite độc lập.
"""

    updated_content = current_content + "\n" + new_entry.strip() + "\n"
    try:
        mem_file.write_text(updated_content, encoding="utf-8")
    except Exception as e:
        print(f"[WARN] Không thể lưu Project Memory: {e}")


# ==============================================================================
# TẦNG 2: THƯ VIỆN KỸ NĂNG CHUYÊN SÂU (SKILLS LIBRARY)
# ==============================================================================

def list_available_skills(custom_skills_dir: pathlib.Path | None = None) -> list[str]:
    """Liệt kê danh sách tất cả các Skill khả dụng."""
    skills = set()
    dirs_to_check = [BUILTIN_SKILLS_DIR]
    if custom_skills_dir and custom_skills_dir.is_dir():
        dirs_to_check.append(custom_skills_dir)

    for base_dir in dirs_to_check:
        if base_dir.is_dir():
            for child in base_dir.iterdir():
                if child.is_dir() and (child / "SKILL.md").is_file():
                    skills.add(child.name)
    return sorted(list(skills))


def load_skill_content(skill_name: str, custom_skills_dir: pathlib.Path | None = None) -> str:
    """Tải nội dung cẩm nang của một Skill cụ thể."""
    dirs_to_check = []
    if custom_skills_dir and custom_skills_dir.is_dir():
        dirs_to_check.append(custom_skills_dir)
    dirs_to_check.append(BUILTIN_SKILLS_DIR)

    for base_dir in dirs_to_check:
        skill_file = base_dir / skill_name / "SKILL.md"
        if skill_file.is_file():
            try:
                return skill_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass
    return ""


def load_selected_skills(skill_names: list[str], custom_skills_dir: pathlib.Path | None = None) -> str:
    """Tập hợp nội dung của các skills được chọn để truyền cho Subagent."""
    contents = []
    for s_name in skill_names:
        clean_name = s_name.strip()
        c = load_skill_content(clean_name, custom_skills_dir)
        if c:
            contents.append(f"<!-- SKILL: {clean_name} -->\n{c}")
    return "\n\n---\n\n".join(contents)


# ==============================================================================
# TẦNG 3: QUÉT VÀ NẠP TÀI LIỆU KIẾN TRÚC DỰ ÁN (PROJECT DOCS / NOTEBOOKLM / SCHEMAS)
# ==============================================================================

DOC_PATTERNS = [
    "ARCHITECTURE.md", "architecture.md",
    "DESIGN.md", "design.md",
    "SCHEMA.md", "schema.md",
    "RULES.md", "rules.md",
    "CONVENTIONS.md", "conventions.md",
    "CONTRIBUTING.md", "contributing.md",
    "DATA_PIPELINE.md", "data_pipeline.md", "PIPELINE.md", "pipeline.md",
    "DATA_DICTIONARY.md", "data_dictionary.md", "ERD.md", "erd.md",
    "dbt_project.yml", "dbt_project.yaml",
]

ALLOWED_EXTENSIONS = {".md", ".txt", ".sql", ".yml", ".yaml", ".json"}


def scan_project_docs(
    repo_path: pathlib.Path,
    extra_dirs: list[pathlib.Path | str] | None = None,
    susu_home: pathlib.Path | None = None,
    max_total_chars: int = 12000,
) -> tuple[str, list[str]]:
    """Quét và nạp tài liệu kiến trúc, data schemas, data contracts và NotebookLM exports.

    Hỗ trợ 4 nguồn tri thức:
    1. Các file kiến trúc chuẩn ở thư mục gốc repo (ARCHITECTURE.md, SCHEMA.md, PIPELINE.md...).
    2. Các thư mục tri thức trong repo (knowledge/, notebooklm/, docs/, schemas/, contracts/).
    3. Thư mục tri thức dùng chung toàn cục (~/.susu/knowledge/).
    4. Các thư mục cấu hình tuỳ chỉnh truyền từ CLI flag --knowledge-dir hoặc .susu.json.

    Trả về:
        (combined_text_for_prompt, list_of_loaded_document_names)
    """
    found_docs: list[tuple[str, str, str]] = []  # (display_path, category, content)
    loaded_names: list[str] = []

    # 1. Quét file tài liệu chuẩn ở root repo
    for doc_name in DOC_PATTERNS:
        doc_file = repo_path / doc_name
        if doc_file.is_file():
            try:
                text = doc_file.read_text(encoding="utf-8", errors="ignore").strip()
                if text:
                    cat = "Data Schema / Config" if doc_name.endswith((".sql", ".yml", ".yaml")) else "Architecture & Rules"
                    found_docs.append((doc_name, cat, text))
                    loaded_names.append(doc_name)
            except Exception:
                pass

    # 2. Các thư mục tri thức chuẩn trong repo
    repo_candidate_folders = [
        repo_path / "notebooklm",
        repo_path / "knowledge",
        repo_path / "schemas",
        repo_path / "contracts",
        repo_path / "docs",
        repo_path / ".susu" / "knowledge",
        repo_path / ".susu" / "docs",
    ]

    # 3. Thư mục tri thức toàn cục của người dùng
    if susu_home and (susu_home / "knowledge").is_dir():
        repo_candidate_folders.append(susu_home / "knowledge")

    # 4. Thư mục bổ sung từ config hoặc CLI
    if extra_dirs:
        for extra in extra_dirs:
            p = pathlib.Path(extra).resolve()
            if p.is_dir() and p not in repo_candidate_folders:
                repo_candidate_folders.append(p)

    for folder in repo_candidate_folders:
        if not folder.is_dir():
            continue
        try:
            # Quét đệ quy tìm các file tài liệu/schema
            for item in folder.rglob("*"):
                if not item.is_file():
                    continue
                if item.suffix.lower() not in ALLOWED_EXTENSIONS:
                    continue
                if item.name.startswith("."):
                    continue

                try:
                    rel_name = str(item.relative_to(repo_path))
                except ValueError:
                    rel_name = f"{folder.name}/{item.name}"

                if rel_name in loaded_names:
                    continue

                # Phân loại tài liệu
                lower_path = str(item).lower()
                if "notebooklm" in lower_path:
                    category = "NotebookLM Knowledge / Research Notes"
                elif "schema" in lower_path or item.suffix in (".sql", ".yml", ".yaml", ".json"):
                    category = "Data Schema / Contracts"
                elif "pipeline" in lower_path or "etl" in lower_path:
                    category = "Data Pipeline Specification"
                else:
                    category = "Project Documentation"

                try:
                    text = item.read_text(encoding="utf-8", errors="ignore").strip()
                    if text:
                        found_docs.append((rel_name, category, text))
                        loaded_names.append(rel_name)
                except Exception:
                    pass

                if len(loaded_names) >= 15:
                    break
        except Exception:
            pass

    if not found_docs:
        return "", []

    combined_text = "# 📖 KHO TRI THỨC DỰ ÁN, SCHEMAS & NOTEBOOKLM (PROJECT KNOWLEDGE):\n\n"
    total_len = 0
    for rel_path, category, content in found_docs:
        header = f"### [{category}] File: `{rel_path}`\n"
        excerpt = content[:2500] + ("\n...(nội dung đã được cắt bớt để tối ưu context)" if len(content) > 2500 else "")
        block = f"{header}{excerpt}\n\n"
        if total_len + len(block) > max_total_chars:
            break
        combined_text += block
        total_len += len(block)

    return combined_text.strip(), loaded_names
