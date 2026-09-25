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
# TẦNG 3: QUÉT VÀ NẠP TÀI LIỆU KIẾN TRÚC DỰ ÁN (PROJECT DOCS / NOTEBOOKLM)
# ==============================================================================

DOC_PATTERNS = [
    "ARCHITECTURE.md", "architecture.md",
    "DESIGN.md", "design.md",
    "SCHEMA.md", "schema.md",
    "RULES.md", "rules.md",
    "CONVENTIONS.md", "conventions.md",
    "CONTRIBUTING.md", "contributing.md",
]


def scan_project_docs(repo_path: pathlib.Path, max_total_chars: int = 8000) -> str:
    """Quét các tài liệu kiến trúc, hướng dẫn thiết kế hoặc export từ NotebookLM trong dự án."""
    found_docs: list[tuple[str, str]] = []

    # 1. Quét các file kiến trúc ở thư mục gốc
    for doc_name in DOC_PATTERNS:
        doc_file = repo_path / doc_name
        if doc_file.is_file():
            try:
                text = doc_file.read_text(encoding="utf-8", errors="ignore").strip()
                if text:
                    found_docs.append((doc_name, text))
            except Exception:
                pass

    # 2. Quét thư mục docs/ hoặc .susu/docs/ hoặc knowledge/
    candidate_folders = [repo_path / "docs", repo_path / ".susu" / "docs", repo_path / "knowledge"]
    for folder in candidate_folders:
        if folder.is_dir():
            for f in folder.glob("*.md"):
                if f.is_file() and len(found_docs) < 5:
                    try:
                        text = f.read_text(encoding="utf-8", errors="ignore").strip()
                        rel_path = str(f.relative_to(repo_path))
                        found_docs.append((rel_path, text))
                    except Exception:
                        pass

    if not found_docs:
        return ""

    combined_text = "# TÀI LIỆU KIẾN TRÚC DỰ ÁN (PROJECT DOCS & KNOWLEDGE):\n\n"
    total_len = 0
    for rel_path, content in found_docs:
        header = f"## File: {rel_path}\n"
        # Cắt bớt nếu file quá dài để không làm tràn context
        excerpt = content[:2500] + ("\n...(cắt bớt để tối ưu context)" if len(content) > 2500 else "")
        block = f"{header}{excerpt}\n\n"
        if total_len + len(block) > max_total_chars:
            break
        combined_text += block
        total_len += len(block)

    return combined_text.strip()
