# Skill: Testing & Quality Assurance Best Practices

## Mục tiêu
Hướng dẫn viết unit test và integration test đạt chuẩn cao, độ tin cậy tuyệt đối, độc lập và dễ debug.

## 1. Nguyên tắc Test Isolation (Tính độc lập hoàn toàn)
- Mỗi test case phải chạy độc lập: kết quả của test A không được ảnh hưởng đến test B.
- Không phụ thuộc vào thứ tự thực thi của test runner.
- Dọn dẹp dữ liệu (TearDown / Cleanup) sau mỗi bài test để không làm ô nhiễm môi trường chạy tiếp theo.

## 2. Cấu trúc bài test AAA (Arrange - Act - Assert)
Mỗi hàm test cần phân định rõ 3 giai đoạn:
```python
def test_calculate_total_with_discount():
    # 1. Arrange: Chuẩn bị dữ liệu và mock
    cart = ShoppingCart()
    cart.add_item("item-1", price=100)
    
    # 2. Act: Thực thi hàm cần kiểm thử
    total = cart.get_total(discount_percent=10)
    
    # 3. Assert: Kiểm tra kết quả
    assert total == 90
```

## 3. Mocking & Stubbing đúng cách
- Mock tất cả các I/O bên ngoài: HTTP requests, Database thật, Email sender, File storage đám mây.
- Không bao giờ để unit test gọi API thật ra Internet (vừa chậm, vừa có nguy cơ lỗi do mạng).
- Sử dụng `unittest.mock.patch` hoặc pytest fixture `monkeypatch`/`mocker` để thay thế service phụ thuộc.

## 4. Bao phủ các kịch bản quan trọng (Test Coverage)
- **Happy Path:** Dữ liệu chuẩn, kịch bản lý tưởng.
- **Boundary Values (Giá trị biên):** Số âm, số 0, số cực lớn, chuỗi rỗng `""`, chuỗi quá dài.
- **Null / None Values:** Truyền `None` vào các tham số không cho phép `None`.
- **Negative Path & Exceptions:** Kiểm tra xem hệ thống có raise đúng Exception và mã lỗi khi nhập sai không (`pytest.raises` hoặc `assertRaises`).

## 5. Thông điệp Assert rõ ràng
- Khi assert thất bại, thông báo phải chỉ rõ lý do:
  ```python
  assert response.status_code == 200, f"Mong đợi 200 nhưng nhận được {response.status_code}: {response.text}"
  ```
