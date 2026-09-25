# Susu — Multi-Agent AI Software Engineering CLI (v0.5)

Hệ thống Agentic tự động hóa quy trình phát triển phần mềm theo mô hình **Manager - Specialized Subagents** với lớp phòng vệ an toàn nhiều tầng:
**User Prompt / File Task → Tech Lead Manager Agent (Khảo sát, lập plan & tuyển chọn Subagent) → Specialized Subagent (Backend / Frontend / Debugger / Refactor / QA) → Safety Guards (Protected Paths & Diff Size) → Tester Verifier (kiểm thử & tự sửa lỗi) → Human Review (giữ code trên branch để bạn tự kiểm tra)**

---

## 🚀 Tính năng nổi bật

1. **Tech Lead / Manager Agent (Điều phối thông minh):**
   - Không chỉ lập kế hoạch thông thường, **Manager Agent** (chạy bằng model suy luận đỉnh cao `claude-opus-4-6-thinking`) đóng vai trò như một Tech Lead thực thụ:
     - Khảo sát toàn diện kiến trúc dự án, convention, ngôn ngữ và bộ test.
     - Phân loại tính chất task (`backend`, `frontend`, `bugfix`, `refactor`, `testing`, `general`).
     - **Tự động tuyển chọn Subagent chuyên trách (Specialized Worker Role)** và model tối ưu cho từng việc cụ thể.
     - Gửi chỉ đạo trọng tâm (Manager Focus Directive) trực tiếp cho Subagent thực thi.

2. **Kho Subagent chuyên trách (Specialized Worker Roles):**
   - **`data_engineer`**: **Chuyên gia Kỹ thuật Dữ liệu (Data Engineering)**, ETL/ELT pipelines, tối ưu hoá xử lý dữ liệu lớn (Big Data / Streaming / Batch), Data Quality, Idempotency, Schema Contracts, Out-of-core & Columnar storage.
   - **`backend_specialist`**: Chuyên gia Backend, API RESTful, Database, Type Hints, Thread-safety & Async I/O.
   - **`frontend_specialist`**: Chuyên gia Giao diện người dùng, UI/UX, Semantic HTML, Modern CSS, Responsive & Micro-interactions.
   - **`senior_debugger`**: Chuyên gia điều tra lỗi sâu (Root Cause Analysis), vá lỗi an toàn, bảo mật & chống regression (Ưu tiên model: `claude-sonnet-4-6`).
   - **`refactor_architect`**: Chuyên gia tái cấu trúc Clean Code, SOLID, Design Patterns, đảm bảo 100% backward compatibility.
   - **`test_engineer`**: Kỹ sư QA kiểm thử chuyên sâu, viết test case biên (Edge cases), Isolation, Mocking & Fixtures.
   - **`general_coder`**: Lập trình viên đa năng cho các tác vụ tổng hợp hoặc CRUD thông dụng.

3. **Hệ thống 3 Tầng Tri thức (Càng làm càng thông minh):**
   - **Tầng 1 — Project Memory (Tích lũy kinh nghiệm tự động):** Sau mỗi task hoàn thành thành công, hệ thống tự động đúc kết các bài học kiến trúc, convention và gotchas vào `~/.susu/memory/<repo_name>.md`. Khi chạy task mới, Manager và Subagent tự động nạp lại kinh nghiệm này, không bao giờ lặp lại lỗi cũ.
   - **Tầng 2 — Thư viện Kỹ năng chuyên sâu (Skills Library):** Tích hợp sẵn cẩm nang kỹ thuật thực chiến trong `skills/`:
     - **Chuyên sâu Data Engineering:**
       - `etl-pipeline-design`: Chuẩn hoá ETL/ELT, Idempotency (UPSERT/Partition overwrite), Medallion Architecture (Bronze-Silver-Gold), Atomic file writes, Retry logic.
       - `data-quality-validation`: Schema Contracts, Pandera, Pydantic, Validation gates (null, duplicate, range checks), Dead Letter Queue (DLQ / Quarantine).
       - `bigdata-memory-optimization`: Xử lý Out-of-Core, Chunking & Streaming, Polars LazyFrame, DuckDB, Columnar Parquet/Arrow, Snappy/ZSTD compression.
       - `sql-analytics-dbt`: Dimensional Modeling (Star/Snowflake Schema, SCD 1 & 2), dbt patterns (staging, intermediate, marts), Window Functions, EXPLAIN query plan.
     - **Kỹ thuật Phần mềm & Toàn diện:**
       - `api-design`: Chuẩn hóa RESTful API, status codes, DTO validation, phân trang.
       - `db-optimization`: Eager loading chống N+1 query, Indexing, Transaction boundaries, connection pool.
       - `testing-best-practices`: Chiến lược AAA, Mocking/Fixtures, isolation, kiểm thử giá trị biên.
       - `frontend-ui`: Semantic HTML5, CSS tokens, responsive layout, micro-interactions, a11y.
       - `clean-code-refactor`: SOLID principles, bảo tồn 100% backward compatibility, minimal invasive.
     Manager tự động tuyển chọn và nạp kỹ năng tương ứng cho Subagent khi nhận task.
   - **Tầng 3 — Quét tài liệu kiến trúc dự án / NotebookLM export (Project Docs):** Tự động phát hiện và hấp thụ tài liệu kiến trúc có sẵn trong repo (`ARCHITECTURE.md`, `SCHEMA.md`, `docs/*.md`, `knowledge/*.md`) để hiểu sâu nghiệp vụ cốt lõi.

4. **Chiến lược Model & Cơ chế Fallback thông minh:**
   - **Tech Lead Manager:** Ưu tiên dùng model suy luận mạnh nhất **`claude-opus-4-6-thinking`**. Nếu hết quota/hạn mức hoặc gặp lỗi, hệ thống tự động fallback sang **`claude-sonnet-4-6`**, và phương án dự phòng cuối cùng là **`gemini-3.8-flash-medium`**.
   - **Specialized Subagent:** Mặc định sử dụng **`gemini-3.8-flash-medium`** (hoặc `claude-sonnet-4-6` khi gặp task fix bug/kiến trúc khó do Manager chỉ định).
   - Cho phép ghi đè linh hoạt bằng cờ CLI (`--coder-model`, `--planner-models`) hoặc cấu hình trong `.susu.json`.

5. **Chế độ Review mặc định — Giữ toàn quyền kiểm soát code:**
   - Mặc định hệ thống **KHÔNG tự động commit hay push** code sau khi test pass.
   - Toàn bộ code thay đổi được giữ nguyên vẹn trên nhánh `agent/<task_id>`. Bạn có thể thoải mái xem lại thay đổi bằng `git diff` / `git status`, sau đó tự quyết định commit hoặc rollback (`susu --rollback <task_id>`).
   - Nếu bạn muốn tự động commit, chỉ cần thêm cờ `--auto-commit` khi chạy lệnh hoặc cấu hình `"auto_commit": true` trong `.susu.json`.

6. **Lớp phòng vệ an toàn đa tầng (Safety Guards):**
   - **Protected Paths Guard:** Chặn cứng và huỷ ngay lập tức nếu Agent cố tình sửa hoặc tạo mới các file nhạy cảm (`.env*`, `*.pem`, `*.key`, `*secret*`, `*credential*`, `.git/*`).
   - **Diff Size Guard:** Chặn đứng Agent nếu số dòng sửa đổi hoặc số file thay đổi vượt quá ngưỡng an toàn (mặc định tối đa 1000 dòng, 30 file), chống tình trạng Agent đi lạc hướng hoặc viết lại cả project.
   - Khi vi phạm bất kỳ lớp bảo vệ nào, hệ thống tự động `reset hard` về trạng thái sạch, tuyệt đối không commit code rác.

7. **Lệnh Rollback tức thì (`susu --rollback <task_id>`):**
   - Cho phép người dùng huỷ bỏ nhanh chóng branch của một task và khôi phục working tree về branch gốc chỉ với 1 câu lệnh.

8. **Lệnh CLI toàn cục `susu` (Đã cài đặt sẵn trên máy):**
   - Đứng ở bất kỳ project nào, bạn chỉ cần mở terminal và gọi lệnh `susu`.
   - Tự động nhận diện thư mục hiện tại làm repository đích (`--repo .`).
   - Tự động khởi tạo `git init` và commit ban đầu nếu thư mục project mới chưa có Git.
   - Toàn bộ lịch sử task, kế hoạch và log được lưu trữ tập trung tại `~/.susu/` (`C:\Users\tranv\.susu/`), giữ cho repo dự án của bạn luôn sạch sẽ 100%.

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
- `--auto-commit`: Tự động commit code khi test PASS (mặc định tắt để bạn tự review code).
- `--coder-model <model>`: Chỉ định model cho Coder Subagent (mặc định: `gemini-3.8-flash-medium`).
- `--planner-models <models>`: Danh sách model ưu tiên cho Planner, phân cách bằng dấu phẩy (mặc định: `claude-opus-4-6-thinking,claude-sonnet-4-6,gemini-3.8-flash-medium`).
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
  "auto_commit": false,
  "coder_model": "gemini-3.8-flash-medium",
  "planner_models": [
    "claude-opus-4-6-thinking",
    "claude-sonnet-4-6",
    "gemini-3.8-flash-medium"
  ],
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

- **Mã nguồn:** Giữ nguyên các thay đổi trên branch `agent/<task_id>` của repo đích sau khi toàn bộ test PASS để bạn tự review (`git diff` / `git status`). Nếu muốn tự động commit, chỉ cần thêm cờ `--auto-commit`.
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
