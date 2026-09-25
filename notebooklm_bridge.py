"""NotebookLM Bridge: Kết nối trực tiếp với Google NotebookLM qua notebooklm-py.

Cho phép:
1. Xác thực Google Account một lần qua `susu --notebooklm-login`.
2. Truy vấn trực tiếp (Live RAG Query) vào Notebook bằng Notebook ID khi Agent lập plan và viết code.
3. Đồng bộ tài liệu từ NotebookLM về thư mục `knowledge/notebooklm/`.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any


def get_storage_path() -> pathlib.Path:
    """Đường dẫn lưu session cookie sau khi login."""
    return pathlib.Path.home() / ".notebooklm" / "profiles" / "default" / "storage_state.json"


def is_authenticated() -> bool:
    """Kiểm tra xem máy đã xác thực Google NotebookLM chưa."""
    storage_file = get_storage_path()
    if storage_file.is_file() and storage_file.stat().st_size > 50:
        return True
    return bool(os.environ.get("NOTEBOOKLM_AUTH_JSON"))


def get_notebooklm_cmd() -> str | None:
    """Tìm đường dẫn thực thi lệnh notebooklm."""
    return shutil.which("notebooklm")


def run_login() -> bool:
    """Mở trình duyệt cho người dùng đăng nhập tài khoản Google vào NotebookLM."""
    cmd = get_notebooklm_cmd()
    if not cmd:
        print("[ERROR] Không tìm thấy lệnh 'notebooklm'. Vui lòng chạy: pip install notebooklm-py")
        return False

    print("\n" + "=" * 65)
    print("🔐 [GOOGLE NOTEBOOKLM AUTHENTICATION]")
    print("Hệ thống sẽ mở trình duyệt để bạn đăng nhập tài khoản Google.")
    print("Sau khi đăng nhập xong, token/cookies sẽ được lưu an toàn tại:")
    print(f"  {get_storage_path()}")
    print("=" * 65 + "\n")

    try:
        ret = subprocess.call([cmd, "login"])
        if ret == 0 and is_authenticated():
            print("\n✅ ĐĂNG NHẬP NOTEBOOKLM THÀNH CÔNG!")
            return True
        else:
            print("\n❌ Đăng nhập chưa hoàn tất hoặc bị huỷ bỏ.")
            return False
    except Exception as e:
        print(f"\n❌ Lỗi khi khởi động notebooklm login: {e}")
        return False


def query_notebook_direct(notebook_id: str, prompt_text: str, timeout_seconds: int = 60) -> str:
    """Truy vấn RAG trực tiếp vào NotebookLM và nhận câu trả lời grounding từ tài liệu của người dùng."""
    if not is_authenticated():
        return ""

    cmd = get_notebooklm_cmd()
    if not cmd:
        return ""

    clean_id = notebook_id.strip()
    # Nếu người dùng dán cả URL (ví dụ: https://notebooklm.google.com/notebook/12345...), trích xuất notebook ID
    if "notebooklm.google.com" in clean_id:
        parts = clean_id.split("/")
        for i, part in enumerate(parts):
            if part == "notebook" and i + 1 < len(parts):
                clean_id = parts[i + 1].split("?")[0]
                break

    try:
        argv = [
            cmd,
            "ask",
            "-n",
            clean_id,
            "-y",
            "--request-timeout",
            str(timeout_seconds),
            prompt_text,
        ]
        res = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds + 10,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception as exc:
        print(f"[WARN] Không thể truy vấn trực tiếp NotebookLM ({clean_id}): {exc}")

    return ""


def list_user_notebooks() -> list[dict[str, Any]]:
    """Liệt kê danh sách các notebook hiện có trong tài khoản của người dùng."""
    if not is_authenticated():
        return []

    cmd = get_notebooklm_cmd()
    if not cmd:
        return []

    try:
        res = subprocess.run(
            [cmd, "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if res.returncode == 0:
            lines = res.stdout.splitlines()
            notebooks = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith("ID") and not line.startswith("-"):
                    notebooks.append({"raw": line})
            return notebooks
    except Exception:
        pass
    return []
