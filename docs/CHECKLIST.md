# H4T Xpress — Checklist tiến độ

Cập nhật: 25/10/2026, cuối Giai đoạn 1. Mã màn hình và mã yêu cầu theo [SPEC.md](SPEC.md).

Quy ước:
- `[x]` xong và đã kiểm thử
- `[~]` làm một phần (ghi rõ phần còn thiếu)
- `[ ]` chưa làm

Kiểm thử ở cuối giai đoạn này:
- **Backend:** 63 test pytest chạy trên PostgreSQL thật.
- **Frontend:** 11 test Vitest, ESLint, `tsc` và build.
- **Thủ công:** toàn bộ luồng của Giai đoạn 1 trên trình duyệt, với stack chạy bằng Docker.

---

## 1. Frontend — màn hình

### Xác thực (Tài xế)

| | Màn | Route | Ghi chú |
|---|---|---|---|
| [x] | D-01 Đăng ký tài xế | `/register` | Bố cục frame "Let's Get started". Thêm nhóm "Work information" (Hub, biển số, bằng lái) theo Chức năng 1 của báo cáo. Có trạng thái lỗi giống frame "Sign up - Error" |
| [x] | D-02 Đăng nhập | `/login` | Frame "Welcome Back". Nhập SĐT (`0…` hoặc `+84`) hoặc e-mail. Có khối đăng nhập nhanh demo |
| [x] | D-03 Xác thực OTP | `/verify` | 6 ô nhập, dán mã/tự điền từ SMS, đếm ngược gửi lại, báo số lần thử còn lại, banner mã demo |
| [x] | Quên / đặt lại mật khẩu | `/forgot-password` | Gửi mã rồi đặt mật khẩu mới trên cùng một màn |

### Tài xế (PWA)

| | Màn | Route | Ghi chú |
|---|---|---|---|
| [x] | D-04 Trang chủ | `/driver` | Ca hôm nay, công tắc "Ready for orders", số đơn đang giữ và đã giao |
| [x] | D-05 Đăng ký ca | `/driver/shifts` | 7 ngày tới; trạng thái Available / Registered / Full / Closed / Overlaps; đăng ký và huỷ |
| [x] | D-15 Hồ sơ | `/driver/profile` | Thông tin tài xế, đổi mật khẩu, đăng xuất |
| [ ] | D-06 Lời mời nhận đơn | | Giai đoạn 2 |
| [ ] | D-07 Tuyến hôm nay | | Giai đoạn 2 |
| [ ] | D-08 Chi tiết điểm dừng/đơn | | Giai đoạn 2 |
| [ ] | D-09 Quét mã vận đơn | | Giai đoạn 2 |
| [ ] | D-10 Thông tin gói hàng | | Giai đoạn 2 |
| [ ] | D-11 Báo sự cố | | Giai đoạn 2 |
| [ ] | D-12 Cập nhật ETA | | Giai đoạn 3 |
| [ ] | D-13 Ảnh minh chứng giao hàng | | Giai đoạn 2 |
| [ ] | D-14 Hoàn tất cập nhật | | Giai đoạn 2 |
| [ ] | Cài đặt PWA (manifest, offline shell) | | Giai đoạn 2 |

### Quản trị viên hệ thống

| | Màn | Route | Ghi chú |
|---|---|---|---|
| [x] | A-01 Danh sách người dùng | `/admin` | Tìm kiếm, lọc theo vai trò/Hub/trạng thái, phân trang, khoá/mở (có hộp xác nhận), đặt lại mật khẩu |
| [x] | A-02 Tạo / sửa người dùng | `/admin/users/new`, `/admin/users/:id` | Kiểm tra theo vai trò (Hub bắt buộc, trường riêng của tài xế); mật khẩu tạm chỉ hiện một lần |
| [x] | A-03 Ma trận phân quyền | `/admin/roles` | Bật/tắt theo vai trò × quyền, lưu những vai trò đã đổi, tuỳ chọn buộc đăng nhập lại |
| [ ] | A-04 Hub và khu vực | `/admin/hubs` | Giai đoạn 3 (hiện là trang chờ) |
| [ ] | A-05 Ca làm việc | `/admin/shifts` | Giai đoạn 3 |
| [ ] | A-06 Cấu hình hệ thống | `/admin/settings` | Giai đoạn 3 |
| [ ] | A-07 Nhật ký hệ thống | | Dữ liệu `audit_logs` đã được ghi, chưa có màn xem |

### Quản lý Hub và Nhà quản trị

| | Màn | Ghi chú |
|---|---|---|
| [~] | Khung dashboard (sidebar, thanh trên, đăng xuất) | Menu lọc theo quyền; nội dung các trang là trang chờ |
| [ ] | H-01 … H-08 | Giai đoạn 2 và 3 |
| [ ] | E-01, E-02 Báo cáo và xuất file | Giai đoạn 3 |

### ShopNow (sàn giả lập) và khách hàng

| | Màn | Route | Ghi chú |
|---|---|---|---|
| [x] | S-01 Tạo đơn (ngẫu nhiên / nhập tay) | `/shopnow` | Đi qua đúng service của API đối tác |
| [x] | S-02 Danh sách đơn + log webhook | `/shopnow` | Huỷ đơn trước khi lấy hàng; log webhook hiển thị chữ ký hợp lệ hoặc không |
| [ ] | S-03 Trang tra cứu cho khách | `/track/:waybill` | Giai đoạn 2 (cần webhook thật từ worker) |
| [ ] | S-04 Bảng điều khiển demo | | Giai đoạn 3 |

### Nền tảng giao diện

- [x] Design system theo Figma: Montserrat cho tiêu đề và Inter cho nội dung; màu chính `#1070F8`; ô nhập 52px bo góc 4px; nút 50px bo góc 10px
- [x] Không dùng thư viện icon: chỉ dùng chữ, huy hiệu màu và công tắc
- [x] Bộ component: Button, TextField, PasswordField, SelectField, Alert, Badge, Card, Dialog, Table, Pagination, Switch, Toaster
- [x] Phiên đăng nhập: access token chỉ giữ trong bộ nhớ, tự làm mới phiên khi gặp 401, khôi phục phiên khi tải lại trang
- [x] Chặn route theo quyền: chưa đăng nhập về `/login`; thiếu quyền về trang chủ của vai trò
- [x] Kiểu TypeScript sinh từ OpenAPI (`pnpm gen:api`)
- [ ] Bản đồ Leaflet, realtime WebSocket (Giai đoạn 2)
- [ ] Playwright E2E (Giai đoạn 3)

---

## 2. Backend — API

| | Nhóm | Endpoint | Yêu cầu |
|---|---|---|---|
| [x] | Health | `GET /health`, `GET /api/v1/health` | |
| [x] | Đăng ký + OTP | `POST /auth/register/driver`, `/auth/otp/verify`, `/auth/otp/resend` | FR-A-03, D11 |
| [x] | Phiên đăng nhập | `POST /auth/login`, `/auth/demo-login`, `/auth/refresh`, `/auth/logout` | Xoay vòng refresh token, phát hiện token bị dùng lại, giới hạn tần suất |
| [x] | Mật khẩu | `POST /auth/password/forgot`, `/auth/password/reset`, `POST /me/password` | Không để lộ tài khoản có tồn tại hay không |
| [x] | Hồ sơ | `GET/PATCH /me` | |
| [x] | Hub | `GET /hubs` | Công khai cho form đăng ký |
| [x] | Tài xế | `GET /driver/today`, `GET /driver/shifts`, `GET/POST/DELETE /driver/shift-registrations`, `PUT /driver/availability` | UC-01, FR-D-01, FR-D-02, BR4 |
| [x] | Quản lý người dùng | `GET/POST /admin/users`, `GET/PATCH /admin/users/{id}`, `lock`, `unlock`, `reset-password`, `revoke-sessions` | FR-A-01 |
| [x] | Phân quyền | `GET /admin/roles`, `GET /admin/permissions`, `PUT /admin/roles/{id}/permissions` | FR-A-02, chặn tự khoá quyền |
| [x] | API đối tác | `POST /partner/v1/orders`, `GET /partner/v1/orders/{waybill}`, `POST .../cancel` | FR-S-01..03, BR2, chống trùng |
| [x] | ShopNow | `/sim/shopnow/orders[/random]`, `.../cancel`, `/sim/shopnow/webhooks` (nhận + xem) | Chữ ký HMAC-SHA256 |
| [~] | Webhook outbox | Đã ghi vào `webhook_deliveries` khi huỷ đơn | Worker gửi đi: Giai đoạn 2 |
| [x] | Máy trạng thái đơn | `orders/state_machine.py` | BR3; đã dùng cho luồng huỷ đơn |
| [ ] | Điều phối (BR4–BR8), lời mời, timeout | | Giai đoạn 2 |
| [ ] | Sự cố, đổi tuyến, đổi tài xế | | Giai đoạn 2 |
| [ ] | ETA, OSRM, tuyến | | Giai đoạn 3 |
| [ ] | Báo cáo + xuất Excel/PDF | | Giai đoạn 3 |
| [ ] | WebSocket, job nền | | Giai đoạn 2 |

Nền tảng backend:
- [x] Một dạng lỗi chung `{error: {code, message, details}}` với mã lỗi nghiệp vụ cố định
- [x] Argon2id, JWT HS256 (access token 15 phút), refresh token chỉ lưu dạng hash trong cookie httpOnly
- [x] Kiểm tra quyền theo mã quyền (`require_permission`); Hub Manager chỉ thấy Hub của mình
- [x] Ghi audit log cho thao tác quản trị
- [x] Bảo vệ tài khoản demo (không khoá, không đổi e-mail/vai trò/mật khẩu)
- [x] Từ chối khởi động ở production nếu `JWT_SECRET` ngắn hơn 32 ký tự

---

## 3. Database

- [x] 35 bảng theo SPEC §6.2, migration Alembic đầu tiên; `alembic check` không thấy model lệch migration
- [x] Ràng buộc: CHECK cho enum, index có điều kiện (mỗi đơn 1 tài xế giữ, mỗi đơn/tài xế 1 lời mời chờ), unique trì hoãn cho thứ tự điểm dừng
- [x] Seed tất định khoảng 36.000 dòng: 90 ngày lịch sử, 3 Hub, 35 tài khoản, 41 đơn chờ điều phối hôm nay
- [x] Dữ liệu nhất quán: trạng thái cuối của đơn khớp lịch sử sự kiện (có test kiểm tra)

## 4. DevOps

- [x] Dockerfile multi-stage cho `api` (214 MB) và `web` (55 MB), cả hai chạy bằng user không phải root
- [x] `docker compose up` chạy cả hệ thống; tự migrate và tự seed khi DB trống
- [x] `docker-compose.dev.yml`: tự tải lại khi sửa code (đã thử trên Windows)
- [x] GitHub Actions: kiểm tra code, type, test (có Postgres), `alembic check`, build image, đẩy lên GHCR khi merge `main`
- [ ] Triển khai Vercel + Render + Neon (Giai đoạn 3)
- [ ] Profile OSRM chạy local (Giai đoạn 3)

## 5. Tài liệu

- [x] `docs/SPEC.md` (đặc tả)
- [x] `docs/CHECKLIST.md` (tài liệu này)
- [x] README: cách chạy, cây thư mục, các luồng mermaid, quy ước code
- [ ] `docs/traceability.md`, `docs/adr/`, `docs/original/` (Giai đoạn 3)
