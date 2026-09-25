# Skill: Database Optimization & Data Access Best Practices

## Mục tiêu
Tối ưu hóa tầng truy xuất cơ sở dữ liệu, đảm bảo tốc độ cao, an toàn giao dịch và phòng ngừa lỗi nghẽn I/O.

## 1. Phòng chống vấn đề N+1 Query
- **Nguyên nhân:** Lấy danh sách N bản ghi cha, sau đó trong vòng lặp lại query từng bản ghi con tương ứng $\rightarrow$ tạo ra N+1 câu query.
- **Giải pháp:**
  - Sử dụng Eager Loading: `joinedload`, `selectinload` (trong SQLAlchemy) hoặc `select_related`, `prefetch_related` (trong Django ORM).
  - Gom các ID và query một lần bằng mệnh đề `WHERE id IN (...)`.

## 2. Quản lý Giao dịch (Transaction Boundaries & ACID)
- Đảm bảo các thao tác ghi dữ liệu phụ thuộc lẫn nhau phải nằm trong cùng một Transaction:
  ```python
  async with session.begin():
      await create_order(...)
      await deduct_inventory(...)
  ```
- Nếu một bước thất bại, toàn bộ giao dịch phải được rollback tự động.
- Giữ transaction càng ngắn càng tốt để tránh giữ lock bảng/hàng quá lâu.

## 3. Indexing & Tối ưu hóa truy vấn
- Đảm bảo các cột thường xuyên xuất hiện trong `WHERE`, `ORDER BY`, `JOIN` phải được đánh Index (B-Tree index).
- Đối với trường hợp tìm kiếm kết hợp nhiều cột, tạo Composite Index theo thứ tự từ cột có tính chọn lọc cao (high cardinality) đến thấp.
- Sử dụng `EXPLAIN ANALYZE` để kiểm tra query plan khi nghi ngờ truy vấn bị quét toàn bộ bảng (Seq Scan).

## 4. An toàn kết nối & Connection Pooling
- Sử dụng Connection Pool có cấu hình giới hạn kích thước (`pool_size`, `max_overflow`).
- Đóng session/connection đúng cách (sử dụng Context Manager `with` / `async with`) để tránh rò rỉ kết nối (Connection Leak).
- Tuyệt đối không bao giờ nối chuỗi SQL thô (`raw string formatting`) để chống tấn công SQL Injection. Luôn dùng Parameterized Queries.
