# Implementation Plan — TASK-DEMO-02

## 1. Inspect & Architecture
- **Hiện trạng repository (`D:/AI/test_sandbox`)**:
  - Kho lưu trữ hiện tại chỉ có file [README.md](file:///D:/AI/test_sandbox/README.md) và thư mục quản lý phiên bản `.git`.
  - Chưa tồn tại mã nguồn triển khai [utils.py](file:///D:/AI/test_sandbox/utils.py) cũng như mã nguồn kiểm thử [test_utils.py](file:///D:/AI/test_sandbox/test_utils.py).
  - Môi trường thực thi: Python 3.10.6.
- **Convention & Kiến trúc**:
  - Ngôn ngữ: Python 3.
  - Chuẩn mã nguồn: Tuân thủ quy chuẩn PEP 8 (quy ước đặt tên hàm `snake_case`, định dạng docstrings, khai báo type hints đầy đủ).
  - Cấu trúc module: Đặt trực tiếp tại thư mục gốc repository:
    - [utils.py](file:///D:/AI/test_sandbox/utils.py): Mô-đun chứa các hàm tiện ích dùng chung, bao gồm hàm [`multiply`](file:///D:/AI/test_sandbox/utils.py).
    - [test_utils.py](file:///D:/AI/test_sandbox/test_utils.py): Mô-đun chứa các bài kiểm thử đơn vị cho `utils.py`.
  - Thư viện kiểm thử: Thư viện chuẩn `unittest` tích hợp sẵn trong Python, không yêu cầu cài đặt thêm các thư viện bên ngoài.

## 2. Implementation Steps
- **Bước 1: Tạo module tiện ích [utils.py](file:///D:/AI/test_sandbox/utils.py)**
  - Đường dẫn: `D:/AI/test_sandbox/utils.py`.
  - Triển khai hàm [`multiply(a, b)`](file:///D:/AI/test_sandbox/utils.py):
    ```python
    def multiply(a: int | float, b: int | float) -> int | float:
        """Tính và trả về tích của hai số a và b."""
        return a * b
    ```
  - Đảm bảo hàm xử lý chính xác cả số nguyên (`int`) và số thực (`float`).

- **Bước 2: Tạo module kiểm thử [test_utils.py](file:///D:/AI/test_sandbox/test_utils.py)**
  - Đường dẫn: `D:/AI/test_sandbox/test_utils.py`.
  - Import module `unittest` và hàm [`multiply`](file:///D:/AI/test_sandbox/utils.py) từ `utils`.
  - Khai báo class `TestUtils(unittest.TestCase)` kế thừa từ `unittest.TestCase`.
  - Thêm khối điều kiện thực thi trực tiếp:
    ```python
    if __name__ == '__main__':
        unittest.main()
    ```

## 3. Test Strategy
Các test case cần xây dựng trong lớp `TestUtils` kế thừa từ `unittest.TestCase`:
- `test_multiply_positive_numbers`: Kiểm tra tích hai số nguyên dương (ví dụ: `multiply(2, 3) == 6`).
- `test_multiply_negative_numbers`: Kiểm tra tích giữa hai số âm và số âm với số dương (ví dụ: `multiply(-2, -3) == 6`, `multiply(-2, 3) == -6`).
- `test_multiply_by_zero`: Kiểm tra tích khi có thừa số bằng 0 (ví dụ: `multiply(5, 0) == 0`, `multiply(0, 0) == 0`).
- `test_multiply_floats`: Kiểm tra phép nhân với số thực (ví dụ: `multiply(2.5, 2) == 5.0`, `multiply(0.1, 0.2)` sử dụng `assertAlmostEqual`).
- `test_multiply_identity`: Kiểm tra tính chất đơn vị của phép nhân (ví dụ: `multiply(7, 1) == 7`).

## 4. Verification
Thực thi lệnh kiểm thử từ thư mục gốc của repository (`D:/AI/test_sandbox`):
```bash
python -m unittest test_utils.py
```
Hoặc sử dụng cơ chế test discovery tự động:
```bash
python -m unittest discover -s . -p "test_*.py"
```
Tiêu chí xác nhận hoàn thành:
- Exit code trả về bằng 0.
- 100% test cases đều pass (trạng thái `OK`).
