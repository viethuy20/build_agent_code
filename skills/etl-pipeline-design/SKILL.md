---
name: etl-pipeline-design
description: Thiết kế và triển khai pipelines ETL/ELT chuẩn công nghiệp (Idempotency, Medallion Architecture, Atomic Writes, Retry logic)
---

# Kỹ Năng Thiết Kế ETL / ELT Pipeline (Data Engineering)

Khi triển khai các pipeline xử lý dữ liệu (batch hoặc streaming), hãy luôn tuân thủ các nguyên tắc kỹ thuật sau:

## 1. Nguyên Tắc Cốt Lõi: Idempotency (Tính Bất Biến Lặp Lại)
- Một pipeline hoặc task chạy lại $N$ lần với cùng input PHẢI cho ra kết quả giống hệt như chạy 1 lần duy nhất, không nhân đôi (duplicate) bản ghi.
- **Chiến lược đạt Idempotency:**
  - **Partition Overwrite:** Khi ghi dữ liệu theo ngày `dt=YYYY-MM-DD`, xoá hoặc ghi đè (overwrite) toàn bộ partition đó, không dùng append không kiểm soát.
  - **Staging & UPSERT / MERGE:** Nạp dữ liệu vào bảng tạm (staging table) -> thực hiện câu lệnh `MERGE INTO target USING staging ON target.id = staging.id WHEN MATCHED THEN UPDATE ... WHEN NOT MATCHED THEN INSERT ...`.
  - **Deterministic Task IDs / Watermarks:** Sử dụng execution_date làm mốc lọc dữ liệu thay vì `NOW()` / `CURRENT_DATE()`.

## 2. Medallion Architecture (Bronze -> Silver -> Gold)
- **Bronze (Raw / Ingestion):**
  - Lưu trữ nguyên bản dữ liệu nguồn thô (JSON, CSV, CDC events).
  - Bổ sung metadata: `_ingested_at`, `_source_file`, `_batch_id`.
- **Silver (Cleaned / Conformed):**
  - Parse kiểu dữ liệu, chuẩn hoá ngày giờ (UTC ISO-8601).
  - Loại bỏ trùng lặp (deduplication) và validate schema.
  - Tách các bản ghi lỗi sang Dead Letter Queue (DLQ).
- **Gold (Business / Aggregated):**
  - Xây dựng Dimensional Model (Fact & Dimension tables).
  - Tính toán các chỉ số kinh doanh (KPIs, aggregates, analytics views) phục vụ BI/Dashboard.

## 3. Atomic Writes & State Checkpointing
- **Atomic File Writing:** Khi xuất file Parquet/CSV, luôn ghi vào thư mục tạm `_tmp/task_id/part-0.parquet`, chỉ sau khi ghi thành công toàn bộ mới rename/move sang thư mục chính thức (`data/output/`). Tránh việc downstream đọc phải file đang ghi dở.
- **State Checkpointing:** Với streaming hoặc long-running batch, lưu offset/cursor/watermark sau mỗi checkpoint thành công.

## 4. Xử Lý Lỗi & Retry với Exponential Backoff
- Mạng và API nguồn dữ liệu có thể chập chờn (transient failure).
- Luôn bọc các lệnh gọi mạng với retry logic + exponential backoff + jitter (vd: retry sau 1s, 2s, 4s, 8s).
- Không để pipeline crash chỉ vì 1 vài bản ghi xấu; áp dụng mô hình Dead Letter Queue / Quarantine Table.
