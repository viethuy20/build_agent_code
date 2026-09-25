# Skill: Clean Code & Refactoring Best Practices

## Mục tiêu
Tái cấu trúc mã nguồn an toàn, nâng cao tính dễ đọc, dễ mở rộng và bảo đảm 100% không gây lỗi hồi quy (zero regressions).

## 1. Nguyên tắc can thiệp tối thiểu (Minimal Invasive Changes)
- Chỉ sửa đổi chính xác những gì cần thiết để đạt mục tiêu.
- Tránh việc "tiện tay" format lại cả file hoặc viết lại toàn bộ module khi không được yêu cầu.
- Giữ nguyên các comment, docstring và convention kiến trúc sẵn có của repo.

## 2. Bảo tồn Public Interfaces (Backward Compatibility)
- Tuyệt đối không thay đổi chữ ký (signature) của các hàm/class công khai (Public APIs) mà các module khác đang gọi.
- Nếu cần thêm tham số mới, hãy đặt giá trị mặc định (`default value = None`).
- Nếu cần deprecate một hàm, tạo hàm mới và cho hàm cũ gọi lại hàm mới kèm cảnh báo `DeprecationWarning`.

## 3. Áp dụng các nguyên tắc SOLID
- **Single Responsibility (SRP):** Mỗi hàm hoặc class chỉ nên có một lý do duy nhất để thay đổi. Nếu một hàm vượt quá 50 dòng và làm nhiều việc, hãy tách nhỏ thành các hàm trợ năng (helper functions).
- **Open/Closed:** Mở rộng tính năng bằng cách thêm class/hàm mới thay vì liên tục sửa logic bên trong hàm cũ.
- **Dependency Inversion:** Phụ thuộc vào interface/abstraction thay vì phụ thuộc vào concrete class cụ thể.

## 4. Tự tài liệu hóa (Self-Documenting Code)
- Đặt tên hàm là động từ mô tả chính xác hành động: `validate_user_token()`, `calculate_final_price()`.
- Đặt tên biến là danh từ rõ nghĩa: `active_users_count` thay vì `n` hay `temp`.
- Sử dụng Type Hints đầy đủ trong Python:
  ```python
  def find_orders_by_customer(customer_id: str, limit: int = 20) -> list[Order]:
      ...
  ```

## 5. Xác minh hồi quy (Regression Verification)
- Chạy toàn bộ test suite cũ trước và sau khi refactor.
- Bất kỳ sự sụt giảm test coverage nào cũng là dấu hiệu của việc refactor chưa an toàn.
