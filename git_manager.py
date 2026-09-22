"""
Git isolation cho mỗi task.

Nguyên tắc:
- Không bao giờ để agent làm việc trực tiếp trên main/master.
- Mỗi task chạy trên branch riêng: agent/<TASK_ID>
- Chỉ commit khi test PASS (do orchestrator.py quyết định, không phải ở đây).
"""

from __future__ import annotations

import subprocess
import pathlib


class GitError(RuntimeError):
    pass


def _run_git(args: list[str], cwd: pathlib.Path) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result


def ensure_clean_worktree(repo_path: pathlib.Path) -> None:
    """Chặn chạy task nếu working tree đang có thay đổi chưa commit.

    Tránh trường hợp agent vô tình commit luôn cả thay đổi cũ của bạn.
    """
    result = _run_git(["status", "--porcelain"], repo_path)
    if result.returncode != 0:
        raise GitError(f"git status thất bại: {result.stderr}")
    if result.stdout.strip():
        raise GitError(
            "Working tree đang có thay đổi chưa commit. "
            "Hãy commit hoặc stash trước khi chạy orchestrator."
        )


def create_task_branch(repo_path: pathlib.Path, task_id: str, base_branch: str = "main") -> str:
    """Tạo (hoặc reset lại) branch agent/<task_id> từ base_branch.

    Trả về tên branch đã tạo.
    """
    branch_name = f"agent/{task_id}"

    # Đảm bảo đang đứng trên base_branch mới nhất trước khi tạo nhánh con
    checkout_base = _run_git(["checkout", base_branch], repo_path)
    if checkout_base.returncode != 0:
        raise GitError(f"Không checkout được {base_branch}: {checkout_base.stderr}")

    # Nếu branch đã tồn tại từ lần chạy trước (task fail rồi retry thủ công),
    # xoá đi tạo lại cho sạch, tránh conflict với code cũ còn sót.
    _run_git(["branch", "-D", branch_name], repo_path)  # bỏ qua lỗi nếu chưa tồn tại

    create = _run_git(["checkout", "-b", branch_name], repo_path)
    if create.returncode != 0:
        raise GitError(f"Không tạo được branch {branch_name}: {create.stderr}")

    return branch_name


def has_uncommitted_changes(repo_path: pathlib.Path) -> bool:
    result = _run_git(["status", "--porcelain"], repo_path)
    return bool(result.stdout.strip())


def commit_all(repo_path: pathlib.Path, message: str) -> str:
    """git add -A && git commit -m message. Trả về commit hash."""
    add = _run_git(["add", "-A"], repo_path)
    if add.returncode != 0:
        raise GitError(f"git add thất bại: {add.stderr}")

    commit = _run_git(["commit", "-m", message], repo_path)
    if commit.returncode != 0:
        raise GitError(f"git commit thất bại: {commit.stderr}")

    rev = _run_git(["rev-parse", "HEAD"], repo_path)
    return rev.stdout.strip()


def diff_stat(repo_path: pathlib.Path) -> str:
    """Tóm tắt các file đã thay đổi, để ghi vào log."""
    result = _run_git(["diff", "--stat"], repo_path)
    return result.stdout.strip()
