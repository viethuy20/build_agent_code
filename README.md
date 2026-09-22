# DE Agent Orchestrator — MVP v0.1

Flow: **Codex (plan) → Orchestrator (Python) → Antigravity CLI `agy` (implement) → Orchestrator tự verify test → commit/stop**

## Vì sao dùng Antigravity CLI (`agy`) thay vì Gemini CLI

Gemini CLI đã ngừng phục vụ tài khoản cá nhân (Google AI Pro/Ultra/Free) từ
18/6/2026, thay thế bằng Antigravity CLI. Dùng `agy` để tận dụng quota
Google Pro sẵn có, không phát sinh phí API riêng.

## Yêu cầu trước khi chạy

1. Cài Antigravity CLI, đăng nhập một lần thủ công:
   ```bash
   agy
   # đăng nhập bằng Google account Pro của bạn, sau đó thoát (Ctrl+C hoặc /exit)
   ```
2. Kiểm tra `agy --version` để biết đang dùng bản nào — `agy` từng có bug
   trả về stdout rỗng khi chạy dưới subprocess (xem phần "Lưu ý về bug agy"
   bên dưới). `agy_worker.py` đã có lớp phòng thủ cho bug này, nhưng nếu
   bạn thấy task liên tục FAILED với lý do "stdout rỗng", hãy thử cập nhật
   `agy` lên bản mới nhất trước.
3. Repo đích phải là git repo **sạch** (không có uncommitted changes) —
   orchestrator sẽ từ chối chạy nếu không.
4. Python 3.10+, không cần cài thêm thư viện ngoài (chỉ dùng standard library).
5. Lệnh `script` phải có sẵn (mặc định có trên Linux/macOS). **Chưa hỗ trợ
   Windows** — chạy qua WSL nếu bạn dùng Windows.

## Chạy thử với task mẫu

```bash
cd de-agent
python orchestrator/main.py --task tasks/TASK-001 --repo /path/to/target/repo
```

Kết quả:
- Log chi tiết: `logs/TASK-001.log`
- Log thô của agy (để debug): `logs/TASK-001.agy.raw.log`
- Nếu PASS: code được commit trên branch `agent/TASK-001` của repo đích.
- Nếu FAIL: branch vẫn giữ nguyên thay đổi (nếu có) để bạn xem xét bằng
  tay, **không tự động retry**.

## Quy trình dùng thật với Codex

1. Trong Antigravity, đưa task cho Codex Agent với prompt kiểu:
   > Analyze this task and repository. Do not implement the task. Create
   > the implementation plan and save it to `tasks/TASK-XXX/plan.md`. Also
   > create/update `tasks/TASK-XXX/task.json` with the structured task
   > information (title, description, requirements, acceptance_criteria,
   > test_commands).
2. Bạn review `plan.md` — đây là bước human-in-the-loop duy nhất.
3. Chạy orchestrator như trên.

## Nguyên tắc cốt lõi

1. **Codex lập kế hoạch, agy thực thi.** Không lẫn lộn vai trò.
2. **Orchestrator kiểm chứng, không tin agent tự báo cáo.** `test_runner.py`
   luôn tự chạy lại `test_commands`, dù agy có nói "tests passed" hay không.
3. **Agent không có quyền tự do chạm production.** `agy` chạy với
   `--dangerously-skip-permissions` để tự động approve tool call — vì vậy:
   - **KHÔNG** để credential thật (AWS, DB production, API key thật) trong
     environment variables khi chạy orchestrator này.
   - `--add-dir` luôn giới hạn agy vào đúng thư mục repo đích, không cho
     truy cập ngoài phạm vi đó.
   - Nên trỏ `--repo` vào một clone riêng để thử nghiệm, không phải repo
     đang có kết nối trực tiếp tới production, cho tới khi bạn tin tưởng
     hệ thống.

## Lưu ý về bug agy (silent empty stdout)

`agy --print`/`-p` có bug đã xác nhận trên nhiều bản: khi stdout không phải
TTY thật (tức mọi trường hợp subprocess/pipe), agy chạy xong, tốn round-trip
với model, exit code = 0, nhưng không in gì ra stdout — không thể phân biệt
"model trả lời rỗng" với "câu trả lời bị nuốt mất".

`agy_worker.py` xử lý bằng 2 lớp:
1. Bọc lệnh trong pseudo-TTY (`script -qec`) để agy tưởng đang chạy trong
   terminal thật.
2. Nếu vẫn rỗng, thử phục hồi từ transcript agy tự lưu trong
   `~/.gemini/antigravity-cli/conversations/` (best-effort).

Nếu cả hai đều thất bại, task được đánh dấu **FAILED** rõ ràng thay vì âm
thầm coi như thành công — bạn sẽ thấy lý do cụ thể trong log.

## Chưa có ở MVP này (theo đúng roadmap đã chốt)

❌ Redis, PostgreSQL, Docker, Kubernetes
❌ Dashboard, multi-agent, test agent riêng, skill router
❌ Auto-retry khi test fail (Phase 4)
❌ Codex CLI tự động hoàn toàn (Phase 2) — hiện vẫn cần bạn copy plan qua
Antigravity thủ công (dù đã bớt thao tác copy-paste nhờ Codex ghi thẳng
ra file)

## Cấu trúc thư mục

```
de-agent/
├── orchestrator/
│   ├── main.py          # entry point, ghép toàn bộ flow
│   ├── agy_worker.py     # gọi Antigravity CLI headless + xử lý bug stdout
│   ├── git_manager.py    # tạo branch, commit, kiểm tra working tree
│   ├── test_runner.py    # tự chạy lại test, không tin agent báo cáo
│   └── logger.py         # ghi log theo task
├── tasks/
│   └── TASK-001/
│       ├── task.json      # dữ liệu có cấu trúc cho máy đọc
│       └── plan.md        # kế hoạch cho agent đọc (Codex tạo ra)
├── logs/                 # log runtime, tự sinh khi chạy
└── worktrees/            # dành cho Phase 3 (multiple agents), chưa dùng
```
