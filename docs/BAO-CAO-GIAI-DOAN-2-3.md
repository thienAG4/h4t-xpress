# Báo cáo Giai đoạn 2 và 3 — H4T Xpress

Ngày: 26/10/2026. Nhánh: `phase-3`; nhánh này chứa luôn các commit của `phase-2`. **Chưa push, chưa merge vào `main`**: đang chờ bạn quyết định.

## 1. Tóm tắt

- Cả 3 giai đoạn trong SPEC đã xong và chạy được trên Docker. Còn đúng một việc chưa làm được: **triển khai lên Render/Vercel/Neon**, vì cần tài khoản của bạn. Cấu hình và hướng dẫn đã có sẵn trong [DEPLOY.md](DEPLOY.md).
- Kiểm thử ở cuối: **119 test backend** chạy trên PostgreSQL thật, **18 test Vitest**, **7 luồng E2E Playwright**. Tất cả đều qua. Lint, type (`mypy --strict`, `tsc`) và `alembic check` sạch.
- Quyết định khi hiện thực được ghi ở SPEC §3.8 (Giai đoạn 2, P2-1..P2-14) và §3.9 (Giai đoạn 3, P3-1..P3-17). Các quyết định kiến trúc chính có 6 ADR trong [adr/](adr/README.md).
- Phiên làm việc bị gián đoạn một lần vì hết hạn mức sử dụng; sau đó tiếp tục từ đúng chỗ dừng.

## 2. Giai đoạn 2: điều phối, giao hàng, sự cố, realtime

| Phần | Đã làm |
|---|---|
| Điều phối (BR4–BR8, EX2, EX3) | Lọc tài xế đủ điều kiện, chấm điểm có trọng số, mời từng người với đếm ngược 30 giây, chạy theo vòng, chuyển `ON_HOLD` sau 3 vòng. Lời mời của Hub được ưu tiên hơn lời mời tự động |
| Luồng tài xế | Popup lời mời, tuyến hôm nay, quét mã, bắt đầu giao, giao kèm ảnh (ảnh được thu nhỏ ngay trên trình duyệt), giao thất bại thì hẹn lại hoặc hoàn hàng, sửa ETA tay, báo sự cố |
| Sự cố (UC-03, UC-04) | Báo sự cố kèm ảnh. Hub phân loại, phản hồi, rồi chọn một trong ba hướng: đổi tuyến, đổi tài xế (tài xế B đến lấy hàng tại chỗ) hoặc giữ hàng tại Hub |
| Màn Hub | Dashboard KPI và cảnh báo SLA, bản đồ theo dõi, timeline đơn, đổi tài xế tay, giữ và thả đơn, tổng quan, danh sách và chi tiết sự cố |
| Realtime | Mỗi tab một WebSocket. Token gửi trong tin nhắn đầu, không đặt trên URL. Sự kiện làm mới đúng các màn liên quan |
| Webhook | Outbox nằm trong cùng transaction, ký HMAC-SHA256, thử lại 1 → 5 → 30 phút |
| Trang tra cứu | Khách thấy trạng thái, ETA mới, lý do trễ kèm lời xin lỗi và ảnh lúc giao. Trang chỉ dựng từ webhook hợp lệ |

## 3. Giai đoạn 3: tuyến đường, báo cáo, quản trị, phát hành

| Phần | Đã làm |
|---|---|
| Định tuyến và ETA | Client OSRM (`/route`, `/trip`) có timeout, cache và thời gian nghỉ sau lỗi. ETA = thời lượng đường thật × hệ số giờ cao điểm + thời gian bốc hàng và phục vụ. OSRM lỗi thì dùng ước lượng và hiện chữ "(estimate)". Polyline đường đi được lưu lại; bản đồ tài xế và Hub vẽ đường thật |
| Lập tuyến (H-02, H-08) | Danh sách tuyến hôm nay, nút "Suggest best order" (chỉ đề xuất khi nhanh hơn ít nhất 60 giây), đổi thứ tự bằng Up/Down, bản đồ so sánh tuyến cũ và mới. Lưu xong là tài xế nhận ngay |
| Báo cáo (E-01, E-02) | 8 KPI so với kỳ trước, biểu đồ sản lượng (có tooltip, chú giải, bảng số), lý do thất bại, tỷ lệ đúng hạn theo khu vực, top tài xế và Hub. Xuất Excel và PDF giữ đúng dấu tiếng Việt. Hub Manager chỉ xem được Hub của mình |
| Quản trị (A-04..A-07) | Hub và khu vực, ca làm, tham số hệ thống có kiểm tra giá trị, nhật ký audit có giá trị trước/sau |
| GPS giả lập và BR12 | Tài xế giả lập tự đi theo đường thật và tự giao. Nút "kẹt xe" trên màn S-04: khoảng 3 phút sau, hệ thống tự mở sự cố `DRIVER_IDLE`. ETA trễ 3 lần thì mở `ETA_ANOMALY` |
| Bảng điều khiển demo (S-04) | `/shopnow/demo`: bật/tắt GPS giả lập, tạo kẹt xe, nạp lại dữ liệu. Bản demo công khai tự nạp lại lúc 03:00 |
| PWA | Có manifest, icon và service worker. Đã thử tắt mạng trên Edge: app vẫn mở được |
| OSRM tự chạy | `docker compose --profile osrm up -d` cắt riêng vùng TP.HCM rồi dựng đồ thị, tốn khoảng 300 MB RAM. Đã chạy thử `/route` và `/trip` |
| Triển khai | `render.yaml`, `web/vercel.json`, workflow `e2e.yml`, hướng dẫn [DEPLOY.md](DEPLOY.md) |
| Tài liệu | SPEC §3.9 và danh sách API/job cập nhật, CHECKLIST, README (12 ảnh chụp màn hình, 10 sơ đồ mermaid đã kiểm tra render), [traceability.md](traceability.md), 6 ADR |

## 4. Kiểm thử

| Loại | Kết quả | Ghi chú |
|---|---|---|
| Backend (pytest + PostgreSQL thật) | 119/119 qua | Giai đoạn 2 kết thúc ở 99 test; Giai đoạn 3 thêm 20 test: OSRM, lập tuyến, báo cáo, xuất file, GPS giả lập, bất thường, cấu hình, dọn GPS |
| Chất lượng code backend | Sạch | `ruff`, `ruff format --check`, `mypy --strict`, `alembic check` |
| Frontend (Vitest) | 18/18 qua | Kèm `eslint`, `tsc`, build |
| E2E (Playwright, Edge, stack Docker) | 7/7 qua (~30 giây) | Trang công khai, chặn quyền, F3 giao hàng, F4 + F5 sự cố, báo cáo, lập tuyến, cấu hình và audit |
| Kiểm tra tay trên trình duyệt | Đạt | Tất cả màn mới, PDF (xem bằng ảnh render), kịch bản kẹt xe ra `INC-000185 DRIVER_IDLE`, PWA khi mất mạng, WebSocket kết nối lại thì màn được làm mới |

## 5. Lỗi phát hiện trong lúc làm và đã sửa

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| Bấm Accept nhưng app không chuyển sang màn tuyến; popup SUCCESS của sự cố lúc hiện lúc không | Callback của `mutate` bị mất khi component unmount | Dùng `mutateAsync`; component cha nhận callback |
| Bản đồ không hiện | DNS của VNPT không phân giải `tile.openstreetmap.org`; CARTO nay đòi API key | Chuyển sang `tile.openstreetmap.de` |
| Tài xế B từ chối thì sự cố không còn đơn; engine tự động "giành" mất đơn của sự cố | Engine và Hub cùng mời một đơn | Đơn có sự cố đang mở do Hub điều phối; sweeper bỏ qua những đơn này |
| Hub không chọn được tài xế đang có lời mời tự động | Ràng buộc "mỗi tài xế một lời mời chờ" | Lời mời của Hub thu hồi lời mời tự động; hai lời mời thủ công cùng lúc thì báo `DRIVER_BUSY` |
| Test worker lúc qua lúc trượt | So giờ của DB với giờ Python (Docker bị lệch giờ) | Test chỉ so với giờ Python |
| Thống kê sự cố bị lỗi enum | `coalesce(priority, 'UNSET')` | Gom nhóm trong Python |
| Build Docker web lỗi | Lockfile không khớp sau khi đổi version sang `^` | Chạy `pnpm install` trước khi build |
| Trang bị cuộn ngang trên màn hẹp | Lưới co giãn theo nội dung | `grid-cols-1` và `min-w-0` |
| E2E không tìm thấy hộp thoại; chữ đang gõ bị mất | Hộp thoại chưa có tên truy cập; component bị dựng lại khi trạng thái đổi | Thêm `aria-labelledby`; key theo id sự cố |
| Nhóm tham số hệ thống xếp theo bảng chữ cái | Sắp xếp mặc định | Sắp theo thứ tự nghiệp vụ |
| Cột tên trong PDF bị căn phải | Mọi cột đều căn phải | Thêm tham số `text_columns` |
| OSRM chậm làm trễ lời mời | GPS giả lập chạy chung vòng lặp với worker | Tách GPS giả lập ra task riêng |
| OSRM local bị kill khi dựng bản đồ cả nước | Cần hơn 8 GB RAM | Cắt riêng vùng TP.HCM trước khi dựng |
| Manifest PWA bị trả về là `octet-stream` | nginx không biết đuôi `.webmanifest` | Khai báo MIME type riêng cho file này |
| Mở `/api/docs` có thể ghi đè app shell đã cache | Service worker cache mọi lần điều hướng | Bỏ qua mọi đường dẫn `/api/` |
| WebSocket kết nối lại nhưng màn không cập nhật | Sự kiện phát ra lúc mất kết nối bị mất luôn (SPEC §5.5 yêu cầu làm mới) | Khi nhận `ready` sau lần kết nối lại thì làm mới mọi query |

## 6. Cách chạy demo

```bash
docker compose up -d --build
# nạp lại dữ liệu sạch khi cần
docker compose exec -T api python -m app.seed --reset
docker compose restart api
```

Mở http://localhost:8080/login rồi dùng các nút đăng nhập nhanh. Có hai kịch bản trong README:

1. **Sự cố trong hai cửa sổ:** driver1 nhận đơn và báo hỏng xe; Hub chuyển đơn cho driver2; khách thấy lời xin lỗi.
2. **Kẹt xe và báo cáo:** vào `/shopnow/demo` và bấm "Start a traffic jam". Khoảng 3 phút sau Hub thấy sự cố "Driver not moving". Sau đó tối ưu tuyến ở Route planning, rồi Executive xuất PDF.

Chạy lại E2E: `cd web && pnpm e2e` (Edge có sẵn trên Windows). Chụp lại ảnh cho README: `pnpm screenshots`.

## 7. Việc cần bạn làm

1. **Review rồi quyết định push/merge.** Nhánh `phase-3` hơn `main` 8 commit, gồm cả Giai đoạn 2. Mình chưa push và chưa merge.
2. **Triển khai:** tạo tài khoản Neon, Render và Vercel rồi làm theo [DEPLOY.md](DEPLOY.md). Khoảng 20 phút, không cần thẻ.
3. **Sau khi push:** workflow `e2e.yml` chưa chạy trên GitHub lần nào, nên xem kết quả của lần chạy đầu. Nếu muốn ai cũng `docker pull` được thì chuyển package GHCR sang public.
4. **Tuỳ chọn:** chép bản gốc báo cáo, BPMN và ERD của nhóm vào `docs/original/`. Các file này nằm trên Google Drive nên mình không tự thêm.

## 8. Hạn chế đã biết

| Hạn chế | Mức độ |
|---|---|
| Ảnh upload trên Render free sẽ mất khi máy chủ khởi động lại. Chưa có adapter Cloudinary/S3 (P3-16) | Chấp nhận được cho demo nạp lại mỗi ngày |
| Quét mã vận đơn (D-09) mới nhập tay, chưa quét bằng camera | Nhỏ |
| Chưa làm benchmark NFR-01 (10.000 tài xế) | Nhỏ |
| Tooltip của biểu đồ sản lượng luôn nằm ở đầu biểu đồ | Thẩm mỹ |
| Đường nét xanh (bản nháp) trên màn lập tuyến là đường thẳng; lưu xong mới thành đường thật | Thẩm mỹ |
| Khi GPS giả lập đang chạy, tài xế giả lập có thể giao xong một điểm lúc Hub đang sửa tuyến; bản nháp khi đó tự đặt lại | Đúng theo thiết kế |
| Cột tài xế trên màn theo dõi ghi "seen -" cho tài xế giả lập (họ không gửi heartbeat) | Thẩm mỹ |
| README có ảnh chụp màn hình nhưng chưa có GIF/video như SPEC gợi ý | Nhỏ |

## 9. Commit trên nhánh `phase-3` (so với `main`)

| Commit | Nội dung |
|---|---|
| `c3f38d4` | feat(api): Giai đoạn 2: điều phối, giao hàng, sự cố, Hub, realtime, webhook |
| `75fcbba` | feat(web): màn hình Giai đoạn 2 |
| `8d7082b` | docs: luồng README, checklist và quyết định SPEC của Giai đoạn 2 |
| `f874ac2` | feat(api): Giai đoạn 3: OSRM, lập tuyến, báo cáo, GPS giả lập, quản trị |
| `e8f244f` | feat(api): dọn dữ liệu GPS, tách vòng lặp GPS giả lập, profile OSRM local |
| `7275b6e` | feat(web): Giai đoạn 3: lập tuyến, báo cáo, quản trị, bảng demo, PWA, E2E |
| `fc13535` | ci: blueprint Render và workflow E2E |
| (commit cuối) | docs: SPEC §3.9, CHECKLIST, README, DEPLOY, traceability, ADR, ảnh chụp, báo cáo này |
