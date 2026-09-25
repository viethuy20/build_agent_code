# Skill: Modern Frontend & UI/UX Best Practices

## Mục tiêu
Xây dựng giao diện web hiện đại, giàu tính thẩm mỹ, hiệu ứng mượt mà và tối ưu trải nghiệm người dùng.

## 1. Hệ thống Design Tokens & CSS Variables
- Định nghĩa bảng màu hài hòa, typography và spacing nhất quán:
  ```css
  :root {
    --bg-primary: #0f172a;
    --bg-surface: #1e293b;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --accent: #38bdf8;
    --accent-hover: #0ea5e9;
    --border: #334155;
    --radius-md: 8px;
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
  }
  ```
- Tránh dùng màu sắc thô sơ mặc định (plain red, plain blue). Sử dụng gam màu tinh chỉnh hiện đại.

## 2. Semantic HTML & Khả năng tiếp cận (Accessibility - a11y)
- Sử dụng các thẻ ngữ nghĩa: `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`, `<footer>`.
- Các nút bấm phải là `<button>` thực thụ, có thuộc tính `aria-label` cho các icon button không có chữ.
- Form inputs phải có `<label>` liên kết qua thuộc tính `for` / `id`.

## 3. Responsive & Mobile-First Layout
- Sử dụng Flexbox và CSS Grid cho bố cục linh hoạt thay vì fix cứng width bằng pixel.
- Sử dụng media queries mượt mà cho mobile (`max-width: 768px`) và tablet/desktop.
- Đảm bảo touch target tối thiểu 44x44px trên thiết bị di động.

## 4. Micro-interactions & Trạng thái tương tác
- Cung cấp đầy đủ các trạng thái cho mọi thành phần tương tác:
  - Default state
  - Hover state (transition 150-200ms)
  - Active / Focus state (outline rõ ràng cho bàn phím)
  - Disabled state (mờ nhạt, `cursor: not-allowed`)
  - Loading state (spinner, skeleton loading)
- Thêm hiệu ứng hover tinh tế để giao diện có cảm giác sống động (dynamic, alive).
