---
name: bigdata-memory-optimization
description: Tối ưu bộ nhớ, Out-of-Core Processing, Streaming/Chunking và định dạng Columnar (Parquet, Arrow, DuckDB, Polars)
---

# Kỹ Năng Tối Ưu Bộ Nhớ & Xử Lý Dữ Liệu Lớn (Big Data Optimization)

Data Engineers thường xuyên phải đối mặt với bài toán dữ liệu lớn hơn dung lượng RAM (Out-of-Memory / OOM). Dưới đây là các kỹ thuật bắt buộc để tối ưu hiệu năng:

## 1. Tránh Nạp Toàn Bộ File Vào RAM (Chunking & Streaming)
- **Tuyệt đối tránh:** `pd.read_csv("100GB_file.csv")` ➔ Dẫn tới tràn RAM và crash container / OS.
- **Giải pháp:**
  - **Python Generators:** Xử lý từng dòng hoặc từng batch nhỏ bằng `yield`.
  - **Pandas Chunking:** Dùng `pd.read_csv("file.csv", chunksize=50_000)` để lặp qua từng chunk.
  - **Polars LazyFrame:** Dùng `pl.scan_parquet()` hoặc `pl.scan_csv()` kết hợp `collect(streaming=True)` để Polars tự động tối ưu query plan và stream dữ liệu mà không tốn RAM.
  - **DuckDB Out-of-Core:** DuckDB có khả năng truy vấn file CSV/Parquet hàng chục GB trực tiếp trên đĩa với RAM hạn chế chỉ vài GB bằng cơ chế buffer manager thông minh.

## 2. Ưu Tiên Định Dạng Lưu Trữ Columnar (Parquet / Arrow)
- CSV/JSON là định dạng hàng (Row-based), chiếm dung lượng lớn và tốn thời gian parse chuỗi.
- Parquet & Apache Arrow mang lại:
  - **Columnar Storage:** Chỉ đọc các cột cần thiết trong câu truy vấn (Projection Pushdown).
  - **Row Group & Statistics:** Bỏ qua hàng triệu dòng không liên quan dựa trên min/max stats (Predicate Pushdown).
  - **Nén mạnh mẽ:** Sử dụng Snappy (nhanh, cân bằng) hoặc ZSTD (nén cao) tiết kiệm 70-90% dung lượng đĩa so với CSV.
  - **Giữ nguyên Schema:** Không bị lỗi format ngày tháng, số thập phân khi đọc lại.

## 3. Quản Lý Kiểu Dữ Liệu & Downcasting
- Tránh để kiểu dữ liệu mặc định quá lớn nếu không cần thiết:
  - Chuyển `float64` ➔ `float32` nếu độ chính xác cho phép.
  - Chuyển `int64` ➔ `int32` hoặc `int16`/`int8` cho các cột ID nhỏ, tuổi tác, mã trạng thái.
  - Chuyển `object` dạng chuỗi có ít giá trị lặp lại sang `category` (Pandas) hoặc `Enum` / `Dictionary-encoded` (Arrow).
- Giảm 50% - 80% RAM sử dụng chỉ bằng việc khai báo schema chuẩn ngay từ bước đọc file.
