---
name: data-quality-validation
description: Kiểm định chất lượng dữ liệu, Schema Contracts, Dead Letter Queue (DLQ) và bẫy lỗi bản ghi xấu
---

# Kỹ Năng Kiểm Định Chất Lượng Dữ Liệu (Data Quality & Validation)

Trong kỹ thuật dữ liệu, "Garbage In, Garbage Out". Dữ liệu sai lệch lọt vào kho dữ liệu hạ nguồn (downstream) sẽ gây hậu quả nghiêm trọng hơn nhiều so với việc pipeline bị hoãn.

## 1. Schema Enforcement & Data Contracts
- Định nghĩa Schema hợp đồng rõ ràng (sử dụng Pydantic, Pandera, PySpark StructType, hoặc Great Expectations).
- Mọi trường dữ liệu đều phải có kiểu dữ liệu rõ ràng (int64, float64, string, timestamp with timezone).
- Không tự ý ép kiểu lỏng lẻo (`coerce=True`) làm mất mát dữ liệu hoặc chuyển chuỗi sai thành `NaN`/`Null` mà không ghi nhận log.

## 2. Các Kiểm Tra Chất Lượng Cốt Lõi (Validation Gates)
1. **Completeness (Độ đầy đủ):**
   - Các trường khóa chính (Primary Key), Timestamp, User ID bắt buộc `NOT NULL`.
   - Ngưỡng cho phép missing values ở các trường thông tin phụ (vd: < 5%).
2. **Uniqueness (Tính duy nhất):**
   - Khóa chính hoặc tổ hợp Composite Key không được phép trùng lặp.
   - Luôn kiểm tra `count(distinct key) == count(key)`.
3. **Validity & Range Checks (Tính hợp lệ và Giới hạn):**
   - Số tiền giao dịch: `amount >= 0`.
   - Ngày giao dịch: `created_at <= CURRENT_TIMESTAMP()` và `created_at >= '2000-01-01'`.
   - Email, số điện thoại, status code phải thỏa mãn Regex hoặc nằm trong danh mục (Enum / Allowed Values).
4. **Referential Integrity (Tính toàn vẹn tham chiếu):**
   - Mọi `user_id` trong Fact Table phải tồn tại trong `dim_users`.

## 3. Chiến Lược Cách Ly Bản Ghi Xấu (Dead Letter Queue - DLQ / Quarantine)
- **Tuyệt đối không bỏ qua lỗi âm thầm (`except: pass`).**
- Thay vì làm crash toàn bộ batch pipeline chứa hàng triệu dòng hợp lệ chỉ vì 10 dòng bị lỗi, hãy phân luồng:
  - Bản ghi hợp lệ (Valid records) ➔ Nạp tiếp vào pipeline chính.
  - Bản ghi vi phạm (Invalid records) ➔ Ghi vào bảng `dlq_rejected_records` hoặc thư mục `quarantine/` kèm metadata: `_error_reason`, `_failed_rule`, `_raw_payload`, `_timestamp`.
- Đặt cảnh báo (Alert) nếu tỷ lệ bản ghi xấu vượt quá ngưỡng an toàn (ví dụ: > 1%).
