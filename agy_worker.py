"""
Gọi Antigravity CLI (agy) headless.

Bản sửa lần 2 — giải quyết 3 vấn đề đã phát hiện ở bản trước:

1. Cross-platform: KHÔNG hardcode `script -qec` (chỉ có trên Linux/macOS).
   Tự "self-test" trên máy hiện tại để chọn đúng cách gọi (direct / pty /
   winpty / bó tay), rồi dùng lại cách đó cho toàn bộ lần chạy.

2. Truyền prompt an toàn: KHÔNG còn nhúng nội dung prompt vào một chuỗi
   shell rồi thực thi (nguồn gây lỗi escape ký tự trước đây). Có 2 trường hợp:
   - Mode "direct"/"winpty": prompt được truyền như một phần tử riêng trong
     list argument của subprocess — Python chuyển giao nguyên vẹn cho
     process con, không qua shell parser nào.
   - Mode "pty" (cần `script -qec`, vốn chỉ nhận MỘT chuỗi lệnh): prompt
     được truyền qua **environment variable**, không nhúng trực tiếp vào
     chuỗi lệnh. Bash mở rộng biến trong dấu nháy kép ("$VAR") mà không
     diễn giải lại các ký tự đặc biệt bên trong giá trị, nên nội dung
     JSON/markdown chứa dấu " hay $ vẫn an toàn.

3. Streaming: dùng Popen + đọc stdout/stderr theo dòng trong thread riêng,
   ghi log real-time thay vì block toàn bộ tới khi xong. Có thêm
   "heartbeat timeout" — nếu không có dòng log mới trong N giây, coi là
   treo và kill sớm, không cần đợi hết timeout tổng.

Lưu ý: hành vi chính xác của `agy` (bug stdout rỗng, nhận prompt qua
argument hay stdin) có báo cáo MÂU THUẪN nhau giữa các version/cộng đồng.
Code này không giả định cứng một hành vi — self_test() tự dò trên máy bạn.
"""

from __future__ import annotations

import dataclasses
import os
import pathlib
import platform
import queue
import re
import shutil
import subprocess
import threading
import time

MAX_SAFE_PROMPT_CHARS = 6000  # dưới giới hạn 8191 ký tự của Windows CMD, để có margin


class AgyNotAvailable(RuntimeError):
    pass


@dataclasses.dataclass
class AgyResult:
    ok: bool
    output: str
    raw_log_path: pathlib.Path
    note: str = ""
    is_infra_error: bool = False
    """True nếu lỗi do agy/hạ tầng (crash, timeout, stdout rỗng không phục
    hồi được) — KHÁC với lỗi do code implement sai. main.py dùng cờ này để
    quyết định có đáng retry hay không (infra error thì retry vô ích)."""


def _check_agy_installed() -> None:
    if shutil.which("agy") is None:
        raise AgyNotAvailable(
            "Không tìm thấy lệnh `agy` trong PATH. Cài Antigravity CLI và "
            "chạy `agy` một lần thủ công để đăng nhập trước khi dùng orchestrator này."
        )


def get_agy_bin() -> str:
    return shutil.which("agy") or "agy"


def _is_windows() -> bool:
    return platform.system().lower() == "windows"


def _strip_pty_artifacts(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"^Script (started|done).*$", "", text, flags=re.MULTILINE)
    return text.strip()


def _stream_process(
    argv: list[str],
    cwd: pathlib.Path,
    log_path: pathlib.Path,
    timeout_seconds: int,
    heartbeat_seconds: int | None = None,
    env: dict | None = None,
) -> tuple[int, str]:
    """Chạy argv qua Popen, đọc stdout/stderr theo dòng, ghi log real-time.

    Trả về (exit_code, stdout_gộp). exit_code = -1 nếu bị kill do treo/timeout
    (phân biệt với exit code thật của process, luôn >= 0).
    """
    log_fh = open(log_path, "a", encoding="utf-8")
    output_chunks: list[str] = []
    q: "queue.Queue[tuple[str, str]]" = queue.Queue()

    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,  # tránh treo nếu agy chờ input tương tác
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    def reader(stream, tag: str) -> None:
        for line in iter(stream.readline, ""):
            q.put((tag, line))
        stream.close()

    t_out = threading.Thread(target=reader, args=(proc.stdout, "OUT"), daemon=True)
    t_err = threading.Thread(target=reader, args=(proc.stderr, "ERR"), daemon=True)
    t_out.start()
    t_err.start()

    start = time.time()
    last_activity = start
    killed_reason = None

    while True:
        try:
            tag, line = q.get(timeout=1)
            last_activity = time.time()
            log_fh.write(line)
            log_fh.flush()
            if tag == "OUT":
                output_chunks.append(line)
        except queue.Empty:
            pass

        if proc.poll() is not None and q.empty():
            break

        now = time.time()
        if now - start > timeout_seconds:
            killed_reason = f"Vượt timeout tổng {timeout_seconds}s"
            proc.kill()
            break
        if heartbeat_seconds and (now - last_activity > heartbeat_seconds):
            killed_reason = f"Không có log mới trong {heartbeat_seconds}s -> nghi treo"
            proc.kill()
            break

    proc.wait()
    t_out.join(timeout=2)
    t_err.join(timeout=2)
    while not q.empty():
        try:
            tag, line = q.get_nowait()
            log_fh.write(line)
            if tag == "OUT":
                output_chunks.append(line)
        except queue.Empty:
            break

    log_fh.write(f"\n--- exit_code={proc.returncode} killed_reason={killed_reason} ---\n")
    log_fh.close()

    full_output = "".join(output_chunks)
    if killed_reason:
        return -1, full_output
    return proc.returncode, full_output


def self_test(workdir: pathlib.Path, logs_dir: pathlib.Path) -> str:
    """Dò cách gọi agy nào cho output thật trên máy hiện tại.

    Trả về 1 trong: "direct", "pty", "winpty", "unrecoverable".
    Kết quả nên được cache lại cho toàn bộ lần chạy orchestrator (không cần
    dò lại ở mỗi attempt), vì hành vi này gắn với version agy + OS, không
    đổi giữa các lần gọi liên tiếp.
    """
    _check_agy_installed()
    logs_dir.mkdir(parents=True, exist_ok=True)
    probe_log = logs_dir / "_agy_selftest.log"
    probe_prompt = "Reply with the word PONG only"
    agy_bin = get_agy_bin()

    # 1. Gọi trực tiếp, list argument, không wrapper
    exit_code, output = _stream_process(
        [agy_bin, "--dangerously-skip-permissions", "-p", probe_prompt],
        cwd=workdir,
        log_path=probe_log,
        timeout_seconds=90,
        heartbeat_seconds=60,
    )
    if exit_code == 0 and "pong" in output.lower():
        return "direct"

    # 2. POSIX: thử pty wrapper qua `script -qec`, prompt truyền qua env var
    if not _is_windows() and shutil.which("script"):
        env = os.environ.copy()
        env["AGY_PROMPT"] = probe_prompt
        inner = f'"{agy_bin}" --dangerously-skip-permissions -p "$AGY_PROMPT"'
        exit_code, output = _stream_process(
            ["script", "-qec", inner, "/dev/null"],
            cwd=workdir,
            log_path=probe_log,
            timeout_seconds=90,
            heartbeat_seconds=60,
            env=env,
        )
        cleaned = _strip_pty_artifacts(output)
        if exit_code == 0 and "pong" in cleaned.lower():
            return "pty"

    # 3. Windows: thử winpty nếu có cài (thường đi kèm Git Bash)
    if _is_windows() and shutil.which("winpty"):
        exit_code, output = _stream_process(
            ["winpty", agy_bin, "--dangerously-skip-permissions", "-p", probe_prompt],
            cwd=workdir,
            log_path=probe_log,
            timeout_seconds=90,
            heartbeat_seconds=60,
        )
        if exit_code == 0 and "pong" in output.lower():
            return "winpty"

    return "unrecoverable"


DEFAULT_CODER_MODEL = "gemini-3.8-flash-medium"


def run_agy(
    prompt: str,
    workdir: pathlib.Path,
    logs_dir: pathlib.Path,
    task_id: str,
    mode: str,
    attempt: int = 1,
    timeout_seconds: int = 1800,
    heartbeat_seconds: int | None = None,
    model: str = DEFAULT_CODER_MODEL,
) -> AgyResult:
    """Chạy agy headless với prompt đã ghép sẵn và model chỉ định.

    mode: kết quả từ self_test(), quyết định cách gọi.
    attempt: 1 hoặc 2 (dùng để đặt tên file log riêng cho từng lần thử).
    model: model AI được dùng (mặc định: gemini-3.8-flash-medium).
    """
    workdir = workdir.resolve()
    raw_log_path = logs_dir / f"{task_id}.attempt{attempt}.agy.log"
    prompt_debug_path = logs_dir / f"{task_id}.attempt{attempt}.prompt.txt"
    prompt_debug_path.write_text(prompt, encoding="utf-8")  # chỉ để debug, không dùng để build lệnh

    if len(prompt) > MAX_SAFE_PROMPT_CHARS:
        raw_log_path.write_text(
            f"[WARN] Prompt dài {len(prompt)} ký tự, vượt ngưỡng an toàn "
            f"{MAX_SAFE_PROMPT_CHARS} — có nguy cơ chạm giới hạn argument "
            "của OS trên một số hệ thống.\n\n",
            encoding="utf-8",
        )

    if mode == "unrecoverable":
        return AgyResult(
            ok=False,
            output="",
            raw_log_path=raw_log_path,
            is_infra_error=True,
            note=(
                "self_test() không tìm được cách nào lấy output thật từ agy "
                "trên máy này. Kiểm tra `agy --version` (thử cập nhật bản mới "
                "hơn), hoặc cài `winpty` nếu đang dùng Windows."
            ),
        )

    add_dir = str(workdir)
    timeout_flag = f"{timeout_seconds}s"
    agy_bin = get_agy_bin()
    model_flags = ["--model", model] if model else []

    if mode == "direct":
        argv = [
            agy_bin, "--dangerously-skip-permissions",
            *model_flags,
            "--add-dir", add_dir,
            "--print-timeout", timeout_flag,
            "-p", prompt,
        ]
        exit_code, output = _stream_process(
            argv, cwd=workdir, log_path=raw_log_path,
            timeout_seconds=timeout_seconds, heartbeat_seconds=heartbeat_seconds,
        )

    elif mode == "winpty":
        argv = [
            "winpty", agy_bin, "--dangerously-skip-permissions",
            *model_flags,
            "--add-dir", add_dir,
            "--print-timeout", timeout_flag,
            "-p", prompt,
        ]
        exit_code, output = _stream_process(
            argv, cwd=workdir, log_path=raw_log_path,
            timeout_seconds=timeout_seconds, heartbeat_seconds=heartbeat_seconds,
        )

    elif mode == "pty":
        # Prompt truyền qua env var, KHÔNG nhúng trực tiếp vào chuỗi lệnh,
        # để tránh vấn đề escape ký tự đặc biệt (dấu ", $, \ trong JSON/markdown).
        env = os.environ.copy()
        env["AGY_PROMPT"] = prompt
        model_str = f'--model "{model}" ' if model else ""
        inner = (
            f'"{agy_bin}" --dangerously-skip-permissions {model_str}'
            f'--add-dir "{add_dir}" '
            f'--print-timeout "{timeout_flag}" '
            f'-p "$AGY_PROMPT"'
        )
        argv = ["script", "-qec", inner, "/dev/null"]
        exit_code, output = _stream_process(
            argv, cwd=workdir, log_path=raw_log_path,
            timeout_seconds=timeout_seconds, heartbeat_seconds=heartbeat_seconds,
            env=env,
        )
        output = _strip_pty_artifacts(output)

    else:
        raise ValueError(f"mode không hợp lệ: {mode}")

    if exit_code == -1:
        return AgyResult(
            ok=False, output=output, raw_log_path=raw_log_path, is_infra_error=True,
            note=f"agy bị kill do treo hoặc vượt timeout. Xem {raw_log_path}",
        )

    if exit_code != 0:
        return AgyResult(
            ok=False, output=output, raw_log_path=raw_log_path, is_infra_error=True,
            note=f"agy thoát với exit code {exit_code}. Xem {raw_log_path}",
        )

    if not output.strip():
        return AgyResult(
            ok=False, output="", raw_log_path=raw_log_path, is_infra_error=True,
            note=(
                "agy trả về output rỗng dù exit code 0 — khớp với bug stdout "
                f"rỗng đã biết. mode='{mode}' đã pass self-test nhưng lần này "
                "vẫn rỗng (có thể do auth timeout). Xem " + str(raw_log_path)
            ),
        )

    return AgyResult(ok=True, output=output, raw_log_path=raw_log_path)
