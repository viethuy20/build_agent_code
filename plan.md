# Implementation Plan — TASK-001

## 1. Inspect repository
Kiểm tra xem file `utils.py` đã tồn tại chưa, xem convention đặt tên hàm/test đang dùng.

## 2. Implement hàm add
Thêm hàm `add(a, b)` vào `utils.py`, có type hint và docstring ngắn gọn.

## 3. Viết unit test
Thêm test trong `test_utils.py` (hoặc file test tương ứng convention của repo), kiểm tra:
- `add(2, 3) == 5`
- `add(-1, 1) == 0`
- `add(1.5, 2.5) == 4.0`

## 4. Chạy thử pytest cục bộ
Chạy `pytest -q` để tự kiểm tra trước khi dừng (orchestrator sẽ chạy lại độc lập để verify).
