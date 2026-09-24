"""
Git isolation cho mỗi task.

Nguyên tắc:
- Không bao giờ để agent làm việc trực tiếp trên main/master.
- Mỗi task chạy trên branch riêng: agent/<TASK_ID>
- Chỉ commit khi test PASS (do orchestrator.py quyết định, không phải ở đây).
"""

from __future__ import annotations

import fnmatch
import pathlib
import subprocess


class GitError(RuntimeError):
    pass


class GitSecurityError(GitError):
    """Lỗi khi phát hiện Agent can thiệp vào đường dẫn cấm."""
    pass


class DiffSizeLimitError(GitError):
    """Lỗi khi thay đổi của Agent vượt quá giới hạn an toàn."""
    pass


DEFAULT_PROTECTED_PATTERNS = [
    ".env*",
    "*.pem",
    "*.key",
    "*secret*",
    "*credential*",
    ".git/*",
]


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


def reset_hard(repo_path: pathlib.Path) -> None:
    """Khôi phục working tree về trạng thái sạch của commit gần nhất."""
    _run_git(["reset", "--hard", "HEAD"], repo_path)
    _run_git(["clean", "-fd"], repo_path)


def check_protected_paths(
    repo_path: pathlib.Path,
    custom_patterns: list[str] | None = None,
) -> list[str]:
    """Kiểm tra xem Agent có sửa đổi hoặc tạo mới file nhạy cảm trong protected_paths không.

    Nếu vi phạm, ném GitSecurityError.
    """
    patterns = list(DEFAULT_PROTECTED_PATTERNS)
    if custom_patterns:
        patterns.extend(custom_patterns)

    status_res = _run_git(["status", "--porcelain"], repo_path)
    if status_res.returncode != 0:
        raise GitError(f"git status thất bại: {status_res.stderr}")

    violated_files: list[str] = []
    for line in status_res.stdout.splitlines():
        line = line.strip()
        if not line or len(line) < 3:
            continue
        # Format porcelain: "XY path" hoặc "R  orig -> new"
        file_path_part = line[3:].strip()
        if " -> " in file_path_part:
            file_path_part = file_path_part.split(" -> ")[1].strip()

        # Chuẩn hóa đường dẫn tương đối
        norm_path = file_path_part.replace("\\", "/")
        file_name = pathlib.Path(norm_path).name

        for pattern in patterns:
            if fnmatch.fnmatch(norm_path, pattern) or fnmatch.fnmatch(file_name, pattern):
                violated_files.append(file_path_part)
                break

    if violated_files:
        raise GitSecurityError(
            f"BẢO MẬT: Agent đã thay đổi hoặc tạo mới file nằm trong danh sách cấm bảo vệ: "
            f"{', '.join(violated_files)}. Tiến trình đã bị chặn đứng."
        )

    return violated_files


def check_diff_size(
    repo_path: pathlib.Path,
    max_lines: int = 1000,
    max_files: int = 30,
) -> tuple[int, int]:
    """Kiểm tra quy mô thay đổi (số file, số dòng).

    Nếu vượt quá ngưỡng, ném DiffSizeLimitError.
    Trả về (files_count, total_lines_changed).
    """
    status_res = _run_git(["status", "--porcelain"], repo_path)
    lines_status = [l for l in status_res.stdout.splitlines() if l.strip()]
    files_count = len(lines_status)

    if files_count > max_files:
        raise DiffSizeLimitError(
            f"DIFF GUARD: Số lượng file thay đổi ({files_count}) vượt quá ngưỡng cho phép ({max_files}). "
            "Nghi ngờ Agent đi lạc hướng."
        )

    # Đếm số dòng thay đổi qua diff --numstat
    numstat_res = _run_git(["diff", "--numstat"], repo_path)
    total_lines = 0
    for line in numstat_res.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                added = int(parts[0]) if parts[0] != "-" else 0
                deleted = int(parts[1]) if parts[1] != "-" else 0
                total_lines += added + deleted
            except ValueError:
                pass

    # Nếu có untracked files, đếm số dòng trong các file đó
    for line in lines_status:
        if line.startswith("??"):
            untracked_file = repo_path / line[3:].strip()
            if untracked_file.is_file():
                try:
                    total_lines += len(untracked_file.read_text(encoding="utf-8", errors="ignore").splitlines())
                except Exception:
                    pass

    if total_lines > max_lines:
        raise DiffSizeLimitError(
            f"DIFF GUARD: Tổng số dòng thay đổi ({total_lines}) vượt quá ngưỡng cho phép ({max_lines}). "
            "Nghi ngờ Agent đi lạc hướng."
        )

    return files_count, total_lines


def rollback_task(repo_path: pathlib.Path, task_id: str, base_branch: str = "main") -> str:
    """Huỷ bỏ branch agent/<task_id> và khôi phục về base_branch."""
    branch_name = f"agent/{task_id}"

    # Kiểm tra xem branch có tồn tại không
    branch_check = _run_git(["branch", "--list", branch_name], repo_path)
    if not branch_check.stdout.strip():
        raise GitError(f"Không tìm thấy branch '{branch_name}' trong repository {repo_path}.")

    # Kiểm tra branch hiện tại
    current_res = _run_git(["branch", "--show-current"], repo_path)
    current_branch = current_res.stdout.strip()

    if current_branch == branch_name:
        # Nếu đang đứng trên branch task, chuyển về base_branch
        checkout = _run_git(["checkout", base_branch], repo_path)
        if checkout.returncode != 0:
            raise GitError(f"Không thể chuyển về '{base_branch}': {checkout.stderr}")

    # Xóa branch task
    delete_res = _run_git(["branch", "-D", branch_name], repo_path)
    if delete_res.returncode != 0:
        raise GitError(f"Không thể xóa branch '{branch_name}': {delete_res.stderr}")

    return f"Đã rollback thành công: Xóa branch '{branch_name}' và chuyển về '{base_branch}'."
