# H4T Xpress — Checklist tiến độ

Cập nhật: 25/10/2026, cuối Giai đoạn 2. Mã màn hình và mã yêu cầu theo [SPEC.md](SPEC.md).

Quy ước:
- `[x]` xong và đã kiểm thử
- `[~]` làm một phần (ghi rõ phần còn thiếu)
- `[ ]` chưa làm

Kiểm thử ở cuối giai đoạn này:
- **Backend:** 99 test pytest chạy trên PostgreSQL thật (63 của Giai đoạn 1, 36 mới cho điều phối, giao hàng, sự cố, Hub, webhook, worker, realtime). `ruff` và `mypy --strict` sạch.
- **Frontend:** 17 test Vitest, ESLint, `tsc` và build.
- **Thủ công, trên stack Docker:** tài xế nhận/từ chối/để hết hạn lời mời, quét mã, bắt đầu giao, cập nhật ETA, giao kèm ảnh, báo sự cố. Hub phân loại, phản hồi, đổi tài xế (lần 1 hết hạn, lần 2 nhận), giữ đơn và thả đơn. Khách tra cứu đơn đã giao trên trang ShopNow.

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
| [x] | D-04 Trang chủ | `/driver` | Ca hôm nay, công tắc "Ready for orders", thẻ tuyến hiện tại (cần lấy, đã quét, điểm dừng, điểm kế tiếp), số đơn |
| [x] | D-05 Đăng ký ca | `/driver/shifts` | 7 ngày tới; trạng thái Available / Registered / Full / Closed / Overlaps; đăng ký và huỷ |
| [x] | D-06 Lời mời nhận đơn | popup toàn màn | Đếm ngược theo giây, thanh tiến độ, điểm lấy (Hub hoặc bàn giao), địa chỉ giao, khoảng cách, tiền thu hộ, nhãn Express, lời mời cứu hộ từ Hub; từ chối có lý do |
| [x] | D-07 Tuyến hôm nay | `/driver/route` | Bản đồ (Hub, vị trí tài xế, điểm dừng đánh số, đường nối), danh sách cần lấy (Quét / Trả đơn), nút "Start delivery", danh sách điểm dừng có ETA |
| [x] | D-08 Chi tiết điểm dừng | `/driver/stops/:id` | Frame "Order Details": thẻ khách, gọi khách, chỉ đường, các kiện, công tắc "Mark as undelivered" với ghi chú và ngày giao lại |
| [~] | D-09 Quét mã vận đơn | hộp thoại | Nhập mã tay (bản web không có đầu đọc mã vạch); camera để Giai đoạn 3 |
| [x] | D-10 Thông tin gói hàng | `/driver/orders/:id` | Frame "Package Delivered": thông tin gói, phí thu hộ, các bước trạng thái, "Delivery failed" / "Successful" |
| [x] | D-11 Báo sự cố | `/driver/incidents/new` | Frame "Report Issue": lý do, mô tả, ảnh, các kiện bị ảnh hưởng, popup "REPORT!" có nút cập nhật ETA |
| [x] | D-11b Sự cố của tôi | `/driver/incidents` | Trạng thái, phản hồi của Hub, việc tài xế cần làm tiếp |
| [x] | D-12 Cập nhật ETA | `/driver/orders/:id/eta` | Bản đồ, thẻ khách, giờ mới + lý do, màn "Successful" |
| [x] | D-13 Ảnh minh chứng giao hàng | trong D-10 | Thu nhỏ ảnh trong trình duyệt (tối đa 1600 px, JPEG) rồi upload ngay |
| [x] | D-14 Hoàn tất cập nhật | `/driver/orders/:id/done` | Frame "Successful", có biến thể "Attempt recorded" khi giao thất bại |
| [x] | D-15 Hồ sơ | `/driver/profile` | Thông tin tài xế, đổi mật khẩu, đăng xuất |
| [ ] | Cài đặt PWA (manifest, offline shell) | | Giai đoạn 3 |

### Quản lý Hub

| | Màn | Route | Ghi chú |
|---|---|---|---|
| [x] | H-01 Dashboard | `/hub` | 5 thẻ KPI, vòng trạng thái (CSS conic-gradient, không dùng thư viện biểu đồ), cột "Needs attention" (đơn rủi ro SLA, sự cố mở), bảng đơn có lọc |
| [ ] | H-02 Lập kế hoạch tuyến | `/hub/routes` | Giai đoạn 3 |
| [x] | H-03 Theo dõi giao hàng | `/hub/tracking[/:orderId]` | Cột tài xế (lọc Online / Có đơn / Tất cả), bản đồ sống, timeline đơn, thao tác: chọn/đổi tài xế, giữ đơn, thả đơn, xác nhận hoàn hàng, ảnh các lần giao |
| [x] | H-04 Tổng quan sự cố | `/hub/incidents` | KPI theo trạng thái, theo mức ưu tiên, theo loại 30 ngày, sự cố mới nhất |
| [x] | H-05 Danh sách sự cố | `/hub/incidents/list` | Tab trạng thái, lọc ưu tiên, thẻ sự cố theo frame "View All Incidents" |
| [x] | H-06 Chi tiết sự cố | `/hub/incidents/:id` | Frame "Issue Report": 3 bước Phân loại → Phản hồi → Giải pháp, lịch sử quyết định |
| [x] | H-07 Đổi tài xế | trong H-06 và H-03 | Bản đồ ứng viên + danh sách xếp hạng, popup "SUCCESS!" |
| [x] | H-08 Đổi tuyến | trong H-06 | Đổi thứ tự điểm dừng bằng nút Up/Down, bản đồ so sánh tuyến cũ (đỏ, nét đứt) và mới (xanh) |

### Quản trị viên hệ thống và Nhà quản trị

| | Màn | Route | Ghi chú |
|---|---|---|---|
| [x] | A-01 Danh sách người dùng | `/admin` | Tìm kiếm, lọc, phân trang, khoá/mở, đặt lại mật khẩu |
| [x] | A-02 Tạo / sửa người dùng | `/admin/users/new`, `/admin/users/:id` | Mật khẩu tạm chỉ hiện một lần |
| [x] | A-03 Ma trận phân quyền | `/admin/roles` | Bật/tắt theo vai trò × quyền |
| [ ] | A-04, A-05, A-06, A-07 | | Giai đoạn 3 (hiện là trang chờ) |
| [ ] | E-01, E-02 Báo cáo và xuất file | `/reports` | Giai đoạn 3 |

### ShopNow (sàn giả lập) và khách hàng

| | Màn | Route | Ghi chú |
|---|---|---|---|
| [x] | S-01 Tạo đơn (ngẫu nhiên / nhập tay) | `/shopnow` | Đi qua đúng service của API đối tác |
| [x] | S-02 Danh sách đơn + log webhook | `/shopnow` | Mã vận đơn dẫn sang trang tra cứu |
| [x] | S-03 Trang tra cứu cho khách | `/track[/:waybill]` | Chỉ dựng từ webhook ShopNow đã nhận (chữ ký hợp lệ): trạng thái, ETA, lý do trễ + lời xin lỗi, tài xế, ảnh lúc giao; tên khách được che bớt |
| [ ] | S-04 Bảng điều khiển demo | | Giai đoạn 3 |

### Nền tảng giao diện

- [x] Design system theo Figma: Montserrat cho tiêu đề và Inter cho nội dung; màu chính `#1070F8`; ô nhập 52px bo góc 4px; nút 50px bo góc 10px
- [x] Không dùng thư viện icon, kể cả trên bản đồ: điểm đánh dấu là hình tròn vẽ bằng Leaflet `CircleMarker`
- [x] Bộ component: thêm `TextAreaField`, `KpiCard`, `StatusBadge`, `Timeline`, `DeliverySteps`, `MapView`, `PhotoPicker`, `CandidatePicker`, `ScreenTitle`
- [x] Bản đồ Leaflet + OpenStreetMap (tile của FOSSGIS `tile.openstreetmap.de`, vì DNS một số nhà mạng VN không phân giải `tile.openstreetmap.org`); tắt zoom bằng con lăn để trang cuộn bình thường
- [x] Realtime: một WebSocket mỗi tab, tự kết nối lại; sự kiện từ server làm mới đúng các query liên quan
- [x] Heartbeat 15 giây khi tài xế online, kèm GPS nếu trình duyệt cho phép và vị trí nằm trong 50 km quanh Hub
- [x] Phiên đăng nhập: access token chỉ giữ trong bộ nhớ, tự làm mới phiên khi gặp 401
- [x] Kiểu TypeScript sinh từ OpenAPI (`pnpm gen:api`)
- [ ] Playwright E2E (Giai đoạn 3)

---

## 2. Backend — API

| | Nhóm | Endpoint | Yêu cầu |
|---|---|---|---|
| [x] | Health | `GET /health`, `GET /api/v1/health` | |
| [x] | Xác thực, hồ sơ, Hub | như Giai đoạn 1 | FR-A-03, D11 |
| [x] | Tài xế: ca và trạng thái | `GET /driver/today`, `/driver/shifts`, `/driver/shift-registrations`, `PUT /driver/availability` | UC-01, FR-D-01, FR-D-02 |
| [x] | Tài xế: hiện diện | `POST /driver/heartbeat` | BR4 (độ mới vị trí) |
| [x] | Tài xế: lời mời | `GET /driver/offers/current`, `POST /driver/offers/{id}/accept`, `/decline` | FR-D-03, BR7, BR8 |
| [x] | Tài xế: tuyến và đơn | `GET /driver/route`, `POST /driver/route/start`, `GET /driver/orders/{id}`, `POST .../scan`, `.../deliver`, `.../fail`, `PUT .../eta`, `POST .../release` | UC-05, BR8, BR9, BR16, BR17, EX4 |
| [x] | Tài xế: sự cố | `POST/GET /driver/incidents`, `GET /driver/incidents/{id}` | FR-D-06, UC-03 bước 1 |
| [x] | File | `POST /files`, `GET /files/{id}` | JPEG/PNG/WebP, tối đa 5 MB |
| [x] | Hub: giám sát | `GET /hub/dashboard`, `/hub/orders`, `/hub/orders/{id}`, `/hub/drivers`, `/hub/drivers/{id}/route` | UC-02, FR-H-02 |
| [x] | Hub: thao tác đơn | `GET /hub/orders/{id}/candidates`, `POST .../reassign`, `.../hold`, `.../release-hold`, `.../returned` | FR-H-01 |
| [x] | Hub: sự cố | `GET /hub/incidents/summary`, `/hub/incidents`, `/hub/incidents/{id}`, `POST .../classify`, `.../respond`, `GET .../candidates`, `POST .../resolve` | UC-03, UC-04, BR13–BR15 |
| [x] | Quản lý người dùng, phân quyền | như Giai đoạn 1 | FR-A-01, FR-A-02 |
| [x] | API đối tác | `POST /partner/v1/orders`, `GET .../{waybill}`, `POST .../cancel` | FR-S-01..03, BR2 |
| [x] | ShopNow | `/sim/shopnow/...`, `GET /sim/track/{waybill}` | S-01..S-03 |
| [x] | WebSocket | `GET /ws` (token gửi trong tin nhắn đầu, không nằm trên URL) | §5.5 |
| [x] | Webhook outbox | Gửi kèm chữ ký HMAC-SHA256, thử lại 1 → 5 → 30 phút, tối đa 6 lần, sau đó FAILED | §3.7, BR10, EX7 |
| [x] | Job nền | Worker trong cùng process: `dispatch.run`, `dispatch.offer_timeout`, `order.reschedule_release`; sweeper 5 giây; job lỗi thử lại tối đa 5 lần; nhận lại job bị bỏ dở | §5.6 |
| [~] | ETA | Ước lượng dự phòng (haversine × 1.4, 25 km/h, hệ số giờ cao điểm) và cờ "estimate"; OSRM để Giai đoạn 3 | §3.3 |
| [ ] | Phát hiện bất thường (BR12) | | Giai đoạn 3 |
| [ ] | Báo cáo + xuất Excel/PDF | | Giai đoạn 3 |

Quy tắc điều phối và giao hàng đã có test:
- [x] BR4 lọc tài xế: đúng Hub, đang online, app còn gửi heartbeat, có ca hôm nay, không có lời mời khác, chưa quá số đơn tối đa
- [x] BR5 chấm điểm: khoảng cách 0.4, tải 0.25, hiệu suất 30 ngày 0.2, độ khớp ca 0.15
- [x] BR6–BR7 mời lần lượt, hết 30 giây coi như từ chối; hết người trong vòng thì chờ 60 giây rồi sang vòng mới
- [x] EX2 không có ai: thử lại sau, không tính vòng. EX3 sau 3 vòng: ON_HOLD và báo đối tác
- [x] BR8 người nhận đầu tiên được đơn; nhận muộn trả `OFFER_CLOSED`
- [x] Lời mời của Hub được ưu tiên: thu hồi lời mời tự động đang chờ của tài xế đó, trả đơn kia về hàng điều phối
- [x] Đơn thuộc sự cố đang mở do Hub điều phối; tự động bỏ qua. Tài xế thay thế từ chối thì sự cố quay về "In review" để Hub chọn người khác
- [x] Đổi tài xế khi hàng đang trên xe: đơn quay về chờ với thông tin bàn giao; tài xế mới đến lấy tại vị trí tài xế cũ

---

## 3. Database

- [x] 35 bảng theo SPEC §6.2; migration thứ hai `rescue_offers` thêm `dispatch_offers.bundle_order_ids` và `incident_id`
- [x] Ràng buộc: CHECK cho enum, index có điều kiện (mỗi đơn 1 tài xế giữ, mỗi tài xế 1 lời mời chờ), unique trì hoãn cho thứ tự điểm dừng
- [x] Seed tất định khoảng 36.000 dòng; driver1 và driver2 luôn có ca cả ngày để chạy kịch bản demo bất kỳ ngày nào
- [x] Thiết lập demo: lời mời 30 giây, chờ vòng 60 giây, chấp nhận vị trí cũ tới 12 giờ, không ép giờ ca

## 4. DevOps

- [x] Dockerfile multi-stage cho `api` và `web`, chạy bằng user không phải root
- [x] `docker compose up` chạy cả hệ thống; tự migrate, tự seed khi DB trống, worker chạy cùng API
- [x] Nginx proxy cả `/api` và `/ws`
- [x] GitHub Actions: kiểm tra code, type, test (có Postgres), `alembic check`, build image, đẩy lên GHCR khi merge `main`
- [ ] Triển khai Vercel + Render + Neon (Giai đoạn 3)
- [ ] Profile OSRM chạy local (Giai đoạn 3)

## 5. Tài liệu

- [x] `docs/SPEC.md` cập nhật theo các quyết định của Giai đoạn 2 (mục 11)
- [x] `docs/CHECKLIST.md` (tài liệu này)
- [x] README: cây thư mục, luồng điều phối, luồng sự cố, luồng webhook
- [ ] `docs/traceability.md`, `docs/adr/`, `docs/original/` (Giai đoạn 3)
