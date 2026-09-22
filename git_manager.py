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


def init_if_needed(repo_path: pathlib.Path, base_branch: str = "main") -> bool:
    """Nếu thư mục chưa phải là git repo, tự động khởi tạo git và commit ban đầu."""
    if not (repo_path / ".git").exists():
        init_res = _run_git(["init"], repo_path)
        if init_res.returncode != 0:
            raise GitError(f"git init thất bại: {init_res.stderr}")
        _run_git(["branch", "-M", base_branch], repo_path)
        status = _run_git(["status", "--porcelain"], repo_path)
        if status.stdout.strip():
            _run_git(["add", "-A"], repo_path)
            _run_git(["commit", "-m", "Initial commit trước khi chạy Susu"], repo_path)
        else:
            keep_file = repo_path / ".gitkeep"
            keep_file.touch()
            _run_git(["add", ".gitkeep"], repo_path)
            _run_git(["commit", "-m", "Initial commit"], repo_path)
        return True
    return False


def ensure_clean_worktree(repo_path: pathlib.Path, base_branch: str = "main") -> None:
    """Chặn chạy task nếu working tree đang có thay đổi chưa commit.

    Tự động git init nếu chưa có git.
    """
    init_if_needed(repo_path, base_branch)
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
    """Tóm tắt các file đã thay đổi (cả tracked và untracked), để ghi vào log."""
    stat = _run_git(["status", "--short"], repo_path).stdout.strip()
    diff = _run_git(["diff", "--stat"], repo_path).stdout.strip()
    if stat and diff:
        return f"{stat}\n\n{diff}"
    return stat or diff
