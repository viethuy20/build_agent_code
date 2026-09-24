# Susu — Multi-Agent AI Software Engineering CLI (v0.3)

Hệ thống Agentic tự động hóa hoàn toàn quy trình phát triển phần mềm:
**User Prompt / File Task → Planner Subagent (khảo sát & lập plan) → Coder Subagent (thực thi) → Tester Verifier (kiểm thử độc lập & tự sửa lỗi) → Auto Git Commit**

---

## 🚀 Tính năng nổi bật

1. **Lệnh CLI toàn cục `susu` (Đã cài đặt sẵn trên máy):**
   - Đã được đóng gói và cài đặt vào hệ thống Windows. Đứng ở bất kỳ project nào, bạn chỉ cần mở terminal và gọi lệnh `susu`.
   - Tự động nhận diện thư mục hiện tại làm repository đích (`--repo .`).
   - Tự động khởi tạo `git init` và commit ban đầu nếu thư mục project mới chưa có Git.
   - Toàn bộ lịch sử task, kế hoạch và log được lưu trữ tập trung tại `~/.susu/` (`C:\Users\tranv\.susu/`), giữ cho repo dự án của bạn luôn sạch sẽ 100%.

2. **Chế độ Full-Auto (Không cần người dùng tự viết hay duyệt plan):**
   - **Subagent 1 (Planner):** Tự động đọc repository đích, phân tích các file hiện có, nhận diện convention và test framework (`unittest`, `pytest`...), sau đó tự sinh `task.json` + `plan.md`.
   - **Subagent 2 (Coder):** Tiếp nhận kế hoạch và trực tiếp viết code trên branch Git riêng biệt (`agent/<task_id>`).
   - **Tester Verifier (Nguyên tắc "Không tin Agent tự báo cáo"):** Tự động chạy lại bộ test độc lập. Nếu test fail do code sai, tự động gom log lỗi và yêu cầu Coder sửa lại (Self-Correction feedback loop, tối đa 2 lần thử).
   - **Git Manager:** Tự động commit code lên branch khi test PASS.

3. **Hỗ trợ Tiếng Việt & Cross-Platform hoàn chỉnh:**
   - **Hỗ trợ cờ `-f / --file`:** Cho phép đọc yêu cầu từ file markdown/text (ví dụ `susu -f task.md`), loại bỏ hoàn toàn hiện tượng PowerShell làm méo font hoặc lỗi ký tự tiếng Việt có dấu.
   - Tự động reconfigure console UTF-8 chống lỗi `UnicodeEncodeError`.
   - Subprocess decode stream với `utf-8` và `errors="replace"` chống văng lỗi `UnicodeDecodeError` trên Windows console tiếng Việt (`cp1258`).
   - Tối ưu cơ chế stream log không bị kill sớm khi LLM xử lý các tài liệu kiến trúc lớn.

4. **An toàn & Cách ly tuyệt đối:**
   - Mọi thay đổi đều được thực hiện trên nhánh cách ly `agent/<task_id>`, tuyệt đối không sửa trực tiếp trên nhánh chính (`main`/`master`).
   - Kiểm tra working tree sạch trước khi chạy để tránh vô tình commit đè code cũ của bạn.

---

## 📦 Cài đặt & Cập nhật

Hệ thống đã được cài đặt vào môi trường Python của bạn. Nếu bạn chỉnh sửa code trong `agent_code` và muốn cập nhật lại:
```bash
cd D:\AI\agent_code
pip install -e .
```

---

## 💡 Hướng dẫn sử dụng

### Cách 1: Đọc yêu cầu từ file (Khuyên dùng — Tránh lỗi tiếng Việt PowerShell)
Tạo file `task.md` (hoặc `prompt.txt`) trong thư mục project của bạn, gõ tiếng Việt có dấu thoải mái trong VSCode, rồi mở terminal tại project đó chạy:
```powershell
susu -f task.md
```

### Cách 2: Gõ trực tiếp yêu cầu trên terminal
```powershell
susu "Them ham format_currency vao utils.py va viet test unittest"
```

### Cách 3: Chỉ định đường dẫn repo từ xa
```powershell
susu -f task.md --repo D:\projects\my_app
# Hoặc
susu "Fix bug auth" --repo D:\projects\my_app
```

### Cách 4: Chạy từ task đã có sẵn plan
```powershell
susu --task tasks/TASK-001
```

### Các tùy chọn bổ sung:
- `--base-branch <branch>`: Chọn branch gốc để phân nhánh (mặc định: `main`).
- `--timeout <giây>`: Thời gian chờ tối đa cho mỗi lần Agent chạy (mặc định: 1800 giây = 30 phút).
- `--task-id <id>`: Chỉ định mã task theo ý muốn (mặc định tự sinh dạng `TASK-YYYYMMDD-HHMMSS`).

---

## 📊 Kết quả đầu ra

- **Mã nguồn:** Tự động commit trên branch `agent/<task_id>` của repo đích sau khi toàn bộ test PASS.
- **Kế hoạch & Dữ liệu task:** Được lưu tại `~/.susu/tasks/<task_id>/`:
  - `task.json`: Dữ liệu có cấu trúc mô tả yêu cầu, tiêu chí nghiệm thu và lệnh test.
  - `plan.md`: Bản kế hoạch chi tiết từng bước do Planner Subagent lập ra.
- **Nhật ký:** Được lưu tại `~/.susu/logs/<task_id>.log` (kèm file log chi tiết cho từng attempt và raw log của CLI).

---

## 📂 Cấu trúc mã nguồn

```
agent_code/
├── setup.py         # Cấu hình cài đặt CLI console script 'susu'
├── pyproject.toml   # Chuẩn packaging hiện đại PEP 517/621
├── main.py          # Orchestrator / Supervisor điều phối toàn bộ workflow
├── planner.py       # Subagent 1: Khảo sát repo, sinh plan.md và task.json
├── agy_worker.py    # Subagent 2: Gọi Antigravity CLI headless để code
├── test_runner.py   # Verifier: Tự chạy lại test, kiểm thử khách quan
├── git_manager.py   # Quản lý branch cô lập, tự động git init, commit
├── logger.py        # Ghi log thời gian thực theo từng task
├── tasks/           # Nơi lưu trữ các task mẫu
└── logs/            # Nơi lưu trữ log thực thi cục bộ
```
