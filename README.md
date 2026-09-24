# Susu — Multi-Agent AI Software Engineering CLI (v0.4)

Hệ thống Agentic tự động hóa hoàn toàn quy trình phát triển phần mềm với lớp phòng vệ an toàn nhiều tầng:
**User Prompt / File Task → Planner Subagent (khảo sát & lập plan) → Coder Subagent (thực thi) → Safety Guards (Protected Paths & Diff Size) → Tester Verifier (kiểm thử & tự sửa lỗi) → Auto Git Commit**

---

## 🚀 Tính năng nổi bật

1. **Lệnh CLI toàn cục `susu` (Đã cài đặt sẵn trên máy):**
   - Đã được đóng gói và cài đặt vào hệ thống Windows. Đứng ở bất kỳ project nào, bạn chỉ cần mở terminal và gọi lệnh `susu`.
   - Tự động nhận diện thư mục hiện tại làm repository đích (`--repo .`).
   - Tự động khởi tạo `git init` và commit ban đầu nếu thư mục project mới chưa có Git.
   - Toàn bộ lịch sử task, kế hoạch và log được lưu trữ tập trung tại `~/.susu/` (`C:\Users\tranv\.susu/`), giữ cho repo dự án của bạn luôn sạch sẽ 100%.

2. **Chế độ Full-Auto & Phân loại rủi ro (Risk Classification):**
   - **Subagent 1 (Planner):** Tự động đọc repository đích, phân tích convention và test framework (`unittest`, `pytest`...), sau đó tự sinh `task.json` + `plan.md`.
   - **Phân loại rủi ro:** Planner tự động đánh giá mức độ rủi ro của task (`LOW`, `MEDIUM`, `HIGH`). Nếu task có rủi ro cao (đụng đến schema DB, auth, credentials, bảo mật), hệ thống sẽ cảnh báo chi tiết trước khi triển khai.
   - **Subagent 2 (Coder):** Tiếp nhận kế hoạch và trực tiếp viết code trên branch Git riêng biệt (`agent/<task_id>`).
   - **Tester Verifier (Nguyên tắc "Không tin Agent tự báo cáo"):** Tự động chạy lại bộ test độc lập. Nếu test fail do code sai, tự động gom log lỗi và yêu cầu Coder sửa lại (Self-Correction feedback loop, tối đa 2 lần thử).

3. **Lớp phòng vệ an toàn đa tầng (Safety Guards):**
   - **Protected Paths Guard:** Chặn cứng và huỷ ngay lập tức nếu Agent cố tình sửa hoặc tạo mới các file nhạy cảm (`.env*`, `*.pem`, `*.key`, `*secret*`, `*credential*`, `.git/*`).
   - **Diff Size Guard:** Chặn đứng Agent nếu số dòng sửa đổi hoặc số file thay đổi vượt quá ngưỡng an toàn (mặc định tối đa 1000 dòng, 30 file), chống tình trạng Agent đi lạc hướng hoặc viết lại cả project.
   - Khi vi phạm bất kỳ lớp bảo vệ nào, hệ thống tự động `reset hard` về trạng thái sạch, tuyệt đối không commit code rác.

4. **Lệnh Rollback tức thì (`susu --rollback <task_id>`):**
   - Cho phép người dùng huỷ bỏ nhanh chóng branch của một task và khôi phục working tree về branch gốc chỉ với 1 câu lệnh.

5. **Cấu hình linh hoạt theo từng dự án (`.susu.json` / `.susu.yaml`):**
   - Hỗ trợ file `.susu.json` đặt tại thư mục gốc của project để cấu hình lệnh test riêng, base branch riêng, danh sách protected paths bổ sung và ngưỡng diff.

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

### Cách 3: Huỷ bỏ nhanh một task (Rollback)
Nếu muốn huỷ branch của task và quay về nhánh chính:
```powershell
susu --rollback TASK-20260924-200612
```

### Cách 4: Chỉ định đường dẫn repo từ xa
```powershell
susu -f task.md --repo D:\projects\my_app
```

### Cách 5: Chạy từ task đã có sẵn plan
```powershell
susu --task tasks/TASK-001
```

### Các tùy chọn bổ sung:
- `--rollback <task_id>`: Huỷ bỏ branch của một task và khôi phục về branch gốc.
- `--force`, `-y`, `--yes`: Bỏ qua cảnh báo xác nhận khi gặp task rủi ro cao (HIGH RISK).
- `--base-branch <branch>`: Chọn branch gốc để phân nhánh (mặc định: `main`).
- `--timeout <giây>`: Thời gian chờ tối đa cho mỗi lần Agent chạy (mặc định: 1800 giây = 30 phút).
- `--task-id <id>`: Chỉ định mã task theo ý muốn (mặc định tự sinh dạng `TASK-YYYYMMDD-HHMMSS`).

---

## ⚙️ Cấu hình dự án (`.susu.json`)

Bạn có thể tạo file `.susu.json` trong thư mục gốc của repo để tuỳ biến:

```json
{
  "base_branch": "main",
  "test_commands": [
    "python -m unittest discover tests"
  ],
  "protected_paths": [
    ".env*",
    "secrets/*",
    "infra/*"
  ],
  "max_diff_lines": 1000,
  "max_files_changed": 30,
  "timeout": 1800
}
```

---

## 📊 Kết quả đầu ra

- **Mã nguồn:** Tự động commit trên branch `agent/<task_id>` của repo đích sau khi toàn bộ test PASS.
- **Kế hoạch & Dữ liệu task:** Được lưu tại `~/.susu/tasks/<task_id>/`:
  - `task.json`: Dữ liệu có cấu trúc mô tả yêu cầu, tiêu chí nghiệm thu, lệnh test và đánh giá rủi ro.
  - `plan.md`: Bản kế hoạch chi tiết từng bước do Planner Subagent lập ra.
- **Nhật ký:** Được lưu tại `~/.susu/logs/<task_id>.log` (kèm file log chi tiết cho từng attempt và raw log của CLI).

---

## 📂 Cấu trúc mã nguồn

```
agent_code/
├── setup.py         # Cấu hình cài đặt CLI console script 'susu'
├── pyproject.toml   # Chuẩn packaging hiện đại PEP 517/621
├── main.py          # Orchestrator / Supervisor điều phối toàn bộ workflow
├── planner.py       # Subagent 1: Khảo sát repo, đánh giá rủi ro, sinh plan.md và task.json
├── agy_worker.py    # Subagent 2: Gọi Antigravity CLI headless để code
├── test_runner.py   # Verifier: Tự chạy lại test, kiểm thử khách quan
├── git_manager.py   # Quản lý branch cô lập, Protected Paths, Diff Guard, Rollback
├── logger.py        # Ghi log thời gian thực theo từng task
├── tasks/           # Nơi lưu trữ các task mẫu
└── logs/            # Nơi lưu trữ log thực thi cục bộ
```
