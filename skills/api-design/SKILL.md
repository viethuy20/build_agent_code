# Skill: API Design & Architecture Best Practices

## Mục tiêu
Hướng dẫn thiết kế và xây dựng API RESTful chuẩn, an toàn, hiệu năng cao và dễ bảo trì.

## 1. Chuẩn hóa Endpoint & HTTP Methods
- Sử dụng danh từ số nhiều cho tài nguyên: `/api/v1/orders`, `/api/v1/users/{id}/profile`.
- Phân định rõ ràng HTTP Methods:
  - `GET`: Chỉ đọc, an toàn, idempotent, không làm thay đổi trạng thái hệ thống.
  - `POST`: Tạo mới tài nguyên.
  - `PUT`: Thay thế toàn bộ tài nguyên.
  - `PATCH`: Cập nhật một phần thuộc tính tài nguyên.
  - `DELETE`: Xóa tài nguyên.

## 2. Request Validation & DTO (Data Transfer Object)
- Luôn sử dụng Schema/DTO để validate dữ liệu đầu vào (ví dụ Pydantic BaseModel, Joi, Zod).
- Validate chặt chẽ kiểu dữ liệu, độ dài chuỗi, regex email, khoảng giá trị số.
- Trả về mã lỗi `422 Unprocessable Entity` hoặc `400 Bad Request` kèm danh sách chi tiết các trường bị lỗi.

## 3. Response Structure & Status Codes
- Mã HTTP Status chuẩn xác:
  - `200 OK`: Thành công (GET, PATCH, PUT).
  - `201 Created`: Tạo mới thành công (kèm Location header hoặc object đã tạo).
  - `204 No Content`: Thành công nhưng không có body (thường dùng cho DELETE).
  - `401 Unauthorized`: Chưa xác thực danh tính (thiếu/sai token).
  - `403 Forbidden`: Đã xác thực nhưng không có quyền hạn truy cập tài nguyên.
  - `404 Not Found`: Không tìm thấy tài nguyên.
  - `409 Conflict`: Xung đột dữ liệu (ví dụ trùng email, duplicate key).
  - `500 Internal Server Error`: Lỗi logic máy chủ (không để lộ stack trace nhạy cảm ra client).
- Cấu trúc response JSON nhất quán:
  ```json
  {
    "success": true,
    "data": { ... },
    "error": null
  }
  ```

## 4. Phân trang, Tìm kiếm & Lọc (Pagination, Filter, Sort)
- Luôn hỗ trợ phân trang cho các endpoint trả về danh sách: `?page=1&limit=20` hoặc cursor-based `?cursor=xyz`.
- Không bao giờ trả về danh sách vô tận không giới hạn từ database.
- Metadata phân trang cần có: `total_items`, `total_pages`, `current_page`, `has_next`.

## 5. Bảo mật & Xử lý ngoại lệ
- Không bao giờ log hoặc trả về mật khẩu, private key, token trong response body.
- Sử dụng Global Exception Handler để bắt toàn bộ exception chưa xử lý và trả về JSON chuẩn.
