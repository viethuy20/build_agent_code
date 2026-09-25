# 🧠 Kho Tri Thức Dự Án & Tích Hợp Google NotebookLM (Layer 3 Knowledge)

Thư mục này là **Tầng 3 (Layer 3 - Project Knowledge Hub)** của hệ thống Susu.
Khi chạy task, **Tech Lead Manager** và **Subagent (Data Engineer / Coder)** sẽ tự động quét, hấp thụ và tuân thủ các kiến thức, quy tắc nghiệp vụ trong thư mục này.

---

## 📌 Cách Kết Nối Với Google NotebookLM

1. Trong **Google NotebookLM**, mở Notebook dự án của bạn (chứa tài liệu kiến trúc, database schema, data dictionary, business logic rules).
2. Tạo hoặc chọn tài liệu tổng hợp:
   - **Briefing Doc** (Bản tóm tắt dự án)
   - **Study Guide** / **FAQ**
   - **Data Dictionary** / **Pipeline Rules**
3. Sao chép nội dung hoặc export ra file Markdown/Text.
4. Thả file vào thư mục `knowledge/notebooklm/` hoặc trực tiếp vào `knowledge/` (ví dụ: `knowledge/notebooklm/data_warehouse_architecture.md`).
5. **Susu CLI** sẽ tự động nhận diện nhãn `[NotebookLM Knowledge]` và nạp trực tiếp vào ngữ cảnh của Agent khi lập kế hoạch và viết code.

---

## 📂 Các Nguồn Tri Thức Tự Động Quét

Susu tự động quét các định dạng: `.md`, `.sql`, `.yml`, `.yaml`, `.json`, `.txt` tại:
- `knowledge/` & `knowledge/notebooklm/`
- `schemas/` & `contracts/` (DDL tạo bảng, Data Contracts, dbt schema)
- `docs/`
- Thư mục toàn cục của bạn: `~/.susu/knowledge/`
- Hoặc chỉ định thư mục bất kỳ bằng cờ: `susu "task" --knowledge-dir D:\notes\notebooklm`
