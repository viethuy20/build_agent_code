# Susu — Multi-Agent AI Software Engineering CLI (v0.3)

Flow tự động hoàn toàn:
**User Prompt → Planner Subagent (khảo sát & lập plan) → Coder Subagent (implement) → Tester Verifier (tự chạy test & retry nếu fail) → Auto Git Commit**

---

## Tính năng nổi bật

1. **Lệnh CLI toàn cục `susu`:**
   - Đã đóng gói thành command `susu`. Đứng ở bất kỳ project nào, bạn chỉ cần gõ 1 dòng lệnh.
   - Tự động nhận diện thư mục hiện tại làm repo đích (`--repo .`).
   - Log và lịch sử task được lưu trữ tập trung tại `~/.susu/` (không làm bẩn project của bạn).

2. **Chế độ Full-Auto (Không cần tự viết hay tự đọc plan):**
   - **Subagent 1 (Planner):** Tự động đọc repository đích, xác định convention/test framework, và tự sinh `task.json` + `plan.md`.
   - **Subagent 2 (Coder):** Nhận plan và tự implement code trên branch Git riêng biệt (`agent/<task_id>`).
   - **Tester Verifier:** Tự động chạy test độc lập (`unittest`, `pytest`...). Nếu test fail, tự động gửi log lỗi bắt Coder sửa lại (tối đa 2 lần thử).
   - **Git Manager:** Tự commit lên branch khi test PASS.

3. **Hỗ trợ Cross-Platform hoàn chỉnh (Windows & Linux/macOS):**
   - Cơ chế `self_test()` tự động nhận diện cách tương tác tốt nhất với Antigravity CLI (`direct` / `pty` / `winpty`).
   - Khắc phục triệt để lỗi Unicode UTF-8 console và decode subprocess trên Windows.

4. **An toàn & Cách ly tuyệt đối:**
   - Hoạt động trên branch riêng `agent/<task_id>`, không bao giờ sửa trực tiếp trên `main`.
   - Bắt buộc repo đích phải có working tree sạch trước khi chạy.

---

## Cài đặt (Đã hoàn tất trên máy của bạn)

Nếu cần cài đặt lại hoặc cập nhật code:
```bash
cd D:\AI\agent_code
pip install -e .
```

---

## Hướng dẫn sử dụng siêu nhanh

### Cách 1: Đọc yêu cầu từ file (Khuyên dùng — Tránh lỗi tiếng Việt PowerShell)

Tạo file `task.md` (hoặc `prompt.txt`) trong project, gõ tiếng Việt có dấu thoải mái trong VSCode, rồi chạy:
```powershell
susu -f task.md
```

### Cách 2: Gõ trực tiếp trên terminal
```powershell
susu "Them ham format_currency vao utils.py va viet test"
```
*(Susu sẽ tự động lấy thư mục bạn đang đứng làm repo đích!)*

### Cách 3: Chỉ định repo từ xa
```powershell
susu -f task.md --repo D:\projects\my_app
```

### Cách 4: Dùng task.json và plan.md có sẵn
```powershell
susu --task tasks/TASK-001
```

---

## Kết quả đầu ra

- **Mã nguồn:** Tự động commit trên branch `agent/<task_id>` của repo đích nếu test pass.
- **Kế hoạch & Nhật ký:** Được lưu tập trung tại:
  - `~/.susu/tasks/<task_id>/`
  - `~/.susu/logs/<task_id>.log`

---

## Cấu trúc mã nguồn

```
agent_code/
├── setup.py         # Cấu hình cài đặt CLI console script 'susu'
├── pyproject.toml   # Chuẩn packaging hiện đại
├── main.py          # Orchestrator / Supervisor điều phối toàn bộ flow
├── planner.py       # Subagent 1: Khảo sát repo, sinh plan.md và task.json
├── agy_worker.py    # Subagent 2: Gọi Antigravity CLI headless để code
├── test_runner.py   # Verifier: Tự chạy lại test, kiểm thử khách quan
├── git_manager.py   # Quản lý branch cô lập, diff stat và auto-commit
└── logger.py        # Ghi log thời gian thực theo từng task
```
