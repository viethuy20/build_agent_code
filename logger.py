"""
Simple per-task file logger.

Ghi log dạng:
[HH:MM:SS] MESSAGE

Vừa in ra console, vừa append vào logs/<task_id>.log
"""

from __future__ import annotations

import datetime
import pathlib


class TaskLogger:
    def __init__(self, task_id: str, logs_dir: pathlib.Path):
        self.task_id = task_id
        logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = logs_dir / f"{task_id}.log"
        # Mở ở chế độ append, không xoá lịch sử chạy trước (dễ debug lại)
        self._fh = open(self.log_path, "a", encoding="utf-8")

    def _timestamp(self) -> str:
        return datetime.datetime.now().strftime("%H:%M:%S")

    def log(self, message: str) -> None:
        line = f"[{self._timestamp()}] {message}"
        print(line)
        self._fh.write(line + "\n")
        self._fh.flush()

    def section(self, title: str) -> None:
        self.log("-" * 50)
        self.log(title)
        self.log("-" * 50)

    def close(self) -> None:
        self._fh.close()
