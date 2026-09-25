---
name: sql-analytics-dbt
description: Mô hình hoá dữ liệu (Dimensional Modeling), dbt patterns, CTEs, Window Functions và tối ưu hoá truy vấn SQL phân tích
---

# Kỹ Năng SQL Analytics & dbt Data Modeling (Data Engineering)

Kỹ năng thiết kế kho dữ liệu (Data Warehouse / Lakehouse), mô hình hoá dữ liệu và tối ưu hoá câu lệnh truy vấn phân tích.

## 1. Dimensional Modeling (Kimball Methodology)
- **Fact Tables (Bảng sự kiện / sự việc):**
  - Chứa các metrics đo lường được (số lượng bán, doanh thu, thời gian phản hồi) và các Foreign Keys liên kết tới Dimension.
  - Phân loại: Transaction Fact, Periodic Snapshot Fact, Accumulating Snapshot Fact.
- **Dimension Tables (Bảng chiều không gian / ngữ cảnh):**
  - Chứa thông tin mô tả thực thể: khách hàng, sản phẩm, cửa hàng, thời gian.
  - **SCD (Slowly Changing Dimensions):**
    - **SCD Type 1:** Ghi đè giá trị cũ (không lưu lịch sử).
    - **SCD Type 2:** Lưu lịch sử thay đổi bằng cách thêm dòng mới kèm cột `valid_from`, `valid_to`, `is_current`.

## 2. dbt Best Practices & Layering
- **Staging (`models/staging/`):**
  - Làm sạch thô: đổi tên cột cho nhất quán, ép kiểu dữ liệu chuẩn, lọc dữ liệu rác ban đầu. 1-to-1 với nguồn.
- **Intermediate (`models/intermediate/`):**
  - Các phép JOIN phức tạp, logic nghiệp vụ tái sử dụng nhiều lần giữa các mart.
- **Marts (`models/marts/`):**
  - Các bảng Fact & Dimension hoàn chỉnh phục vụ trực tiếp cho báo cáo và phân tích kinh doanh.
- **Incremental Models:** Dùng `is_incremental()` để chỉ xử lý dữ liệu mới phát sinh, tránh quét toàn bộ bảng lịch sử hàng tỷ dòng.

## 3. Tối Ưu Truy Vấn SQL Phân Tích
- **Không bao giờ dùng `SELECT *`:** Luôn chỉ định danh sách cột cụ thể để tận dụng tối đa Columnar storage.
- **Tận dụng Partition Pruning:** Luôn đặt điều kiện lọc trên cột phân vùng (vd: `WHERE event_date >= '2026-09-01'`) để database không phải full scan toàn bộ đĩa.
- **Sử dụng Window Functions:** Thay thế các phép self-join nặng nề bằng `ROW_NUMBER()`, `RANK()`, `LEAD()`, `LAG()`, `SUM(...) OVER (PARTITION BY ... ORDER BY ...)`.
- **Dùng Common Table Expressions (CTEs):** Tách bạch logic từng bước để code dễ đọc, dễ kiểm thử và dễ tối ưu query plan.
- **Kiểm tra EXPLAIN Query Plan:** Đọc chi tiết chi phí (cost), scan type (Index scan vs Sequential scan), shuffle/hash join để phát hiện nghẽn cổ chai.
