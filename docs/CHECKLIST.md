# H4T Xpress — Checklist tiến độ

Cập nhật: 26/10/2026, cuối Giai đoạn 3. Mã màn hình và mã yêu cầu theo [SPEC.md](SPEC.md); quyết định của Giai đoạn 3 ở SPEC §3.9.

Quy ước:
- `[x]` xong và đã kiểm thử
- `[~]` làm một phần (ghi rõ phần còn thiếu)
- `[ ]` chưa làm

Kiểm thử ở cuối giai đoạn này:
- **Backend:** 119 test pytest chạy trên PostgreSQL thật (99 của Giai đoạn 1–2, 20 mới cho OSRM và lập tuyến, báo cáo và xuất file, GPS giả lập, phát hiện bất thường, cấu hình hệ thống, dọn dữ liệu GPS). `ruff`, `ruff format`, `mypy --strict` và `alembic check` sạch.
- **Frontend:** 18 test Vitest, ESLint, `tsc` và build.
- **E2E (Playwright, trên stack Docker):** 7 luồng: trang công khai và chặn quyền, F3 nhận đơn → quét → giao kèm ảnh → khách thấy "Delivered", F4 + F5 báo sự cố → Hub phân loại, phản hồi, giữ hàng tại Hub → khách thấy lời xin lỗi, báo cáo của Executive, lập tuyến của Hub, cấu hình và audit của Admin.
- **Thủ công, trên stack Docker:** tuyến đường thật từ OSRM trên bản đồ tài xế và Hub, tối ưu và lưu thứ tự tuyến, báo cáo và file PDF/Excel, các trang quản trị, bảng điều khiển demo, tài xế giả lập tự chạy và giao, kịch bản kẹt xe sinh sự cố `DRIVER_IDLE` sau khoảng 3 phút, PWA mở được khi mất mạng (Edge), OSRM tự chạy bằng profile `osrm`.

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
| [x] | D-07 Tuyến hôm nay | `/driver/route` | Bản đồ (Hub, vị trí tài xế, điểm dừng đánh số, đường đi thật từ OSRM), danh sách cần lấy (Quét / Trả đơn), nút "Start delivery", danh sách điểm dừng có mã vận đơn và ETA |
| [x] | D-08 Chi tiết điểm dừng | `/driver/stops/:id` | Frame "Order Details": thẻ khách, gọi khách, chỉ đường, các kiện, công tắc "Mark as undelivered" với ghi chú và ngày giao lại |
| [~] | D-09 Quét mã vận đơn | hộp thoại | Nhập mã tay (bản web không có đầu đọc mã vạch); quét bằng camera chưa làm |
| [x] | D-10 Thông tin gói hàng | `/driver/orders/:id` | Frame "Package Delivered": thông tin gói, phí thu hộ, các bước trạng thái, "Delivery failed" / "Successful" |
| [x] | D-11 Báo sự cố | `/driver/incidents/new` | Frame "Report Issue": lý do, mô tả, ảnh, các kiện bị ảnh hưởng, popup "REPORT!" có nút cập nhật ETA |
| [x] | D-11b Sự cố của tôi | `/driver/incidents` | Trạng thái, phản hồi của Hub, việc tài xế cần làm tiếp |
| [x] | D-12 Cập nhật ETA | `/driver/orders/:id/eta` | Bản đồ, thẻ khách, giờ mới + lý do, màn "Successful" |
| [x] | D-13 Ảnh minh chứng giao hàng | trong D-10 | Thu nhỏ ảnh trong trình duyệt (tối đa 1600 px, JPEG) rồi upload ngay |
| [x] | D-14 Hoàn tất cập nhật | `/driver/orders/:id/done` | Frame "Successful", có biến thể "Attempt recorded" khi giao thất bại |
| [x] | D-15 Hồ sơ | `/driver/profile` | Thông tin tài xế, đổi mật khẩu, đăng xuất |
| [x] | Cài đặt PWA (manifest, offline shell) | `/driver` | Manifest mở vào `/driver`, icon 192/512, `sw.js` giữ app shell; đã thử tắt mạng trên Edge (P3-13) |

### Quản lý Hub

| | Màn | Route | Ghi chú |
|---|---|---|---|
| [x] | H-01 Dashboard | `/hub` | 5 thẻ KPI, vòng trạng thái (CSS conic-gradient, không dùng thư viện biểu đồ), cột "Needs attention" (đơn rủi ro SLA, sự cố mở), bảng đơn có lọc |
| [x] | H-02 Lập kế hoạch tuyến | `/hub/routes` | Tuyến hôm nay theo tài xế, quãng đường và thời gian còn lại, nguồn ETA; "Suggest best order" (OSRM `/trip`), đổi thứ tự Up/Down, bản đồ tuyến hiện tại (đỏ, nét đứt) và bản nháp (xanh); lưu là gửi xuống tài xế |
| [x] | H-03 Theo dõi giao hàng | `/hub/tracking[/:orderId]` | Cột tài xế (lọc Taking orders / With orders / All), bản đồ sống với vị trí cập nhật realtime và đường đi thật, timeline đơn, thao tác: chọn/đổi tài xế, giữ đơn, thả đơn, xác nhận hoàn hàng, ảnh các lần giao |
| [x] | H-04 Tổng quan sự cố | `/hub/incidents` | KPI theo trạng thái, theo mức ưu tiên, theo loại 30 ngày, sự cố mới nhất |
| [x] | H-05 Danh sách sự cố | `/hub/incidents/list` | Tab trạng thái, lọc ưu tiên, thẻ sự cố theo frame "View All Incidents" |
| [x] | H-06 Chi tiết sự cố | `/hub/incidents/:id` | Frame "Issue Report": 3 bước Phân loại → Phản hồi → Giải pháp, lịch sử quyết định |
| [x] | H-07 Đổi tài xế | trong H-06 và H-03 | Bản đồ ứng viên + danh sách xếp hạng, popup "SUCCESS!" |
| [x] | H-08 Đổi tuyến | trong H-06 | Dùng chung bộ sửa thứ tự với H-02: nút "Suggest best order", Up/Down, bản đồ tuyến cũ (đỏ, nét đứt) và mới (xanh) |

### Quản trị viên hệ thống và Nhà quản trị

| | Màn | Route | Ghi chú |
|---|---|---|---|
| [x] | A-01 Danh sách người dùng | `/admin` | Tìm kiếm, lọc, phân trang, khoá/mở, đặt lại mật khẩu |
| [x] | A-02 Tạo / sửa người dùng | `/admin/users/new`, `/admin/users/:id` | Mật khẩu tạm chỉ hiện một lần |
| [x] | A-03 Ma trận phân quyền | `/admin/roles` | Bật/tắt theo vai trò × quyền |
| [x] | A-04 Hub và khu vực | `/admin/hubs` | Thêm/sửa Hub (mã, tên, địa chỉ, toạ độ, khu vực, trạng thái) và khu vực; tắt Hub thay cho xoá |
| [x] | A-05 Ca làm | `/admin/shifts` | Lọc theo Hub; sửa giờ, sức chứa, bật/tắt từng ca; giờ sai báo lỗi |
| [x] | A-06 Tham số hệ thống | `/admin/settings` | Nhóm theo nghiệp vụ (Dispatch, ETA, SLA, Delivery, Shifts, Anomaly, Demo simulator); mỗi khoá có mô tả, luật kiểm tra và thời điểm lưu |
| [x] | A-07 Nhật ký audit | `/admin/audit` | Lọc theo nhóm hành động, phân trang, xem giá trị trước/sau của từng thay đổi |
| [x] | E-01 Báo cáo | `/reports` | Bộ lọc một hàng (7/30/90 ngày, khoảng ngày, chọn Hub); 8 thẻ KPI so với kỳ trước ("better/worse"); biểu đồ cột sản lượng có tooltip, chú giải và bảng số liệu; lý do thất bại, đúng hạn theo khu vực; top tài xế và Hub kèm thay đổi thứ hạng |
| [x] | E-02 Xuất file | `/reports` | Excel (mỗi khối một sheet) và PDF (KPI, bảng, biểu đồ, tiếng Việt có dấu); Hub Manager chỉ xem Hub của mình và không có quyền xuất |

### ShopNow (sàn giả lập) và khách hàng

| | Màn | Route | Ghi chú |
|---|---|---|---|
| [x] | S-01 Tạo đơn (ngẫu nhiên / nhập tay) | `/shopnow` | Đi qua đúng service của API đối tác |
| [x] | S-02 Danh sách đơn + log webhook | `/shopnow` | Mã vận đơn dẫn sang trang tra cứu |
| [x] | S-03 Trang tra cứu cho khách | `/track[/:waybill]` | Chỉ dựng từ webhook ShopNow đã nhận (chữ ký hợp lệ): trạng thái, ETA, lý do trễ + lời xin lỗi, tài xế, ảnh lúc giao; tên khách được che bớt |
| [x] | S-04 Bảng điều khiển demo | `/shopnow/demo` | Bật/tắt GPS giả lập, danh sách tài xế giả lập, nút "Start a traffic jam", nạp lại dữ liệu (System Admin) |

### Nền tảng giao diện

- [x] Design system theo Figma: Montserrat cho tiêu đề và Inter cho nội dung; màu chính `#1070F8`; ô nhập 52px bo góc 4px; nút 50px bo góc 10px
- [x] Không dùng thư viện icon, kể cả trên bản đồ: điểm đánh dấu là hình tròn vẽ bằng Leaflet `CircleMarker`
- [x] Bộ component: thêm `TextAreaField`, `KpiCard`, `StatusBadge`, `Timeline`, `DeliverySteps`, `MapView`, `PhotoPicker`, `CandidatePicker`, `ScreenTitle`
- [x] Bản đồ Leaflet + OpenStreetMap (tile của FOSSGIS `tile.openstreetmap.de`, vì DNS một số nhà mạng VN không phân giải `tile.openstreetmap.org`); tắt zoom bằng con lăn để trang cuộn bình thường
- [x] Realtime: một WebSocket mỗi tab, tự kết nối lại; sự kiện từ server làm mới đúng các query liên quan
- [x] Heartbeat 15 giây khi tài xế online, kèm GPS nếu trình duyệt cho phép và vị trí nằm trong 50 km quanh Hub
- [x] Phiên đăng nhập: access token chỉ giữ trong bộ nhớ, tự làm mới phiên khi gặp 401
- [x] Kiểu TypeScript sinh từ OpenAPI (`pnpm gen:api`)
- [x] Tách code theo trang (`React.lazy`); bản đồ tải riêng khi cần
- [x] Hộp thoại có tên truy cập (`aria-labelledby`), lưới trang không tràn ngang trên màn hẹp
- [x] Playwright E2E: 7 luồng (`pnpm e2e`) và script chụp ảnh README (`pnpm screenshots`)

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
| [x] | ETA | Thời lượng đường thật từ OSRM × hệ số giờ cao điểm + thời gian bốc hàng và phục vụ; OSRM lỗi thì dùng ước lượng dự phòng và cờ "estimate" | §3.3, NFR-04, P3-1, P3-2 |
| [x] | Lập tuyến | `GET /hub/routes`, `GET /hub/routes/{id}`, `POST .../optimize`, `PUT .../stops/order` | UC-03 (H-02, H-08), P3-4 |
| [x] | Phát hiện bất thường (BR12) | `anomaly.scan` mỗi phút: `DRIVER_IDLE`, `ETA_ANOMALY` | BR12, EX5, EX6, P3-9 |
| [x] | Báo cáo + xuất Excel/PDF | `GET /reports`, `GET /reports/export?format=xlsx\|pdf` | FR-R-01..06, P3-5..P3-7 |
| [x] | Quản trị cấu hình | `/admin/areas`, `/admin/hubs`, `/admin/shifts`, `/admin/settings`, `/admin/audit-logs` | FR-A-04, P3-11 |
| [x] | Bảng điều khiển demo | `GET /sim/demo`, `PUT /sim/demo/gps`, `POST /sim/demo/traffic-jam`, `POST /sim/demo/reset` | §7.2, P3-10 |
| [x] | GPS giả lập | Task riêng mỗi 3 giây, đi theo đường OSRM, giao bằng ảnh mẫu | §7.2, P3-8 |
| [x] | Dọn dữ liệu GPS | Mỗi giờ xoá điểm cũ hơn 7 ngày | §12, P3-12 |

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
- [x] Seed Giai đoạn 3: tuyến và điểm dừng hôm nay cho tài xế thứ 2–4 của mỗi Hub, webhook ShopNow lịch sử, tham số `sim.*` và `anomaly.idle_minutes` = 3 (demo)
- [x] `routes.polyline` lưu đường đi OSRM; không cần migration mới (cột đã có từ Giai đoạn 0)

## 4. DevOps

- [x] Dockerfile multi-stage cho `api` và `web`, chạy bằng user không phải root
- [x] `docker compose up` chạy cả hệ thống; tự migrate, tự seed khi DB trống, worker chạy cùng API
- [x] Nginx proxy cả `/api` và `/ws`
- [x] GitHub Actions: kiểm tra code, type, test (có Postgres), `alembic check`, build image, đẩy lên GHCR khi merge `main`
- [~] Triển khai Vercel + Render + Neon: đã có `render.yaml`, `web/vercel.json` và hướng dẫn [DEPLOY.md](DEPLOY.md); **cần chủ repo tạo tài khoản và bấm deploy**
- [x] Profile OSRM chạy local (`docker compose --profile osrm up -d`): cắt vùng TP.HCM, đã chạy thử `/route` và `/trip`
- [x] Workflow `e2e.yml` (Playwright trên docker compose, chạy khi mở PR); **chưa chạy trên GitHub** vì chưa push
- [x] Nginx: MIME type cho manifest, không cache `sw.js` và `index.html`
- [x] Image `api` có font DejaVu cho PDF tiếng Việt

## 5. Tài liệu

- [x] `docs/SPEC.md` cập nhật theo các quyết định của Giai đoạn 2 (§3.8) và Giai đoạn 3 (§3.9), danh sách API và job
- [x] `docs/CHECKLIST.md` (tài liệu này)
- [x] README: trạng thái, ảnh chụp màn hình, cây thư mục, luồng điều phối, sự cố, webhook, ETA/OSRM, GPS giả lập, kịch bản demo
- [x] `docs/DEPLOY.md`, `docs/traceability.md`, `docs/adr/` (các quyết định kiến trúc chính)
- [x] `docs/BAO-CAO-GIAI-DOAN-2-3.md`: báo cáo tổng hợp Giai đoạn 2 và 3
- [ ] `docs/original/` (bản gốc báo cáo, BPMN, ERD của nhóm): cần chủ repo chép vào vì file nằm trên Google Drive
