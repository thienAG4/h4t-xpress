# Ma trận truy vết: yêu cầu → code → test

Mở rộng SPEC §9 tới tên file và tên test. Mã yêu cầu giữ nguyên từ báo cáo gốc. Đường dẫn backend tính từ `api/app/modules/`, frontend từ `web/src/features/`, test backend trong `api/tests/`, E2E trong `web/e2e/`.

Cập nhật: 26/10/2026, cuối Giai đoạn 3.

## Chức năng

| Yêu cầu | Mô tả | Backend | Màn hình | Test backend | E2E |
|---|---|---|---|---|---|
| FR-S-01..03 | Tiếp nhận, kiểm tra, huỷ đơn từ sàn | `partner/router.py`, `partner/service.py` | S-01 `shopnow/pages/ShopNowPage.tsx` | `test_partner.py` (7 test), `test_sim.py::test_random_orders_go_through_the_partner_service` | `delivery.e2e.ts` (tạo đơn qua ShopNow) |
| FR-D-01 / UC-01 | Đăng ký ca làm | `drivers/service.py` | D-05 `driver/pages/ShiftsPage.tsx` | `test_drivers.py::test_register_overlap_and_cancel`, `::test_full_shift_and_closed_dates_are_rejected` | |
| FR-D-02 | Bật/tắt nhận đơn | `drivers/service.py` | D-04 `driver/pages/DriverHomePage.tsx` | `test_drivers.py::test_going_online_needs_a_shift_today` | `helpers.ts::setOnline` |
| FR-D-03 | Nhận và trả lời lời mời | `dispatch/service.py` | D-06 `delivery/components/OfferModal.tsx` | `test_dispatch.py::test_unanswered_offer_moves_to_next_driver_then_first_accept_wins` | `delivery.e2e.ts`, `incident.e2e.ts` |
| FR-D-04 | Quét mã vận đơn | `delivery/service.py::scan` | D-09 hộp thoại trong `delivery/pages/RoutePage.tsx` | `test_delivery.py::test_scan_start_and_deliver_with_proof` | `helpers.ts::pickUpFirstParcel` |
| FR-D-05 / UC-05 | Cập nhật trạng thái giao | `delivery/service.py` | D-07, D-08, D-10, D-14 | `test_delivery.py` (6 test), `test_state_machine.py` (5 test) | `delivery.e2e.ts` |
| FR-D-06 | Báo sự cố | `incidents/service.py::report` | D-11 `incidents/pages/ReportIncidentPage.tsx` | `test_incidents.py::test_report_needs_description_and_evidence` | `incident.e2e.ts` |
| FR-H-01 / UC-04 | Điều phối lại đơn | `orders/hub_service.py`, `incidents/service.py::resolve` | H-07 `components/CandidatePicker.tsx` | `test_hub.py::test_reassign_takes_the_order_back_and_offers_it`, `test_incidents.py::test_reassign_hands_parcels_over_to_another_driver` | |
| FR-H-02 / UC-02 | Theo dõi tiến độ | `orders/`, `realtime/`, `tracking/service.py` | H-01 `hub/pages/HubDashboardPage.tsx`, H-03 `hub/pages/TrackingPage.tsx` | `test_hub.py` (9 test), `test_realtime.py` | |
| FR-H-03 / UC-03 | Điều chỉnh tuyến đường | `routing/planning.py`, `routing/osrm.py` | H-02 `hub/pages/RoutePlanningPage.tsx`, H-08 `incidents/components/ReroutePanel.tsx` | `test_routing.py::test_hub_plans_and_reorders_a_route`, `test_incidents.py::test_reroute_changes_the_stop_order` | `back-office.e2e.ts` (lập tuyến) |
| FR-R-01..05 | Báo cáo | `reports/queries.py` | E-01 `reports/pages/ReportsPage.tsx` | `test_reports.py::test_executive_sees_every_hub_and_numbers_match`, `::test_period_and_granularity`, `::test_hub_manager_is_limited_to_their_hub` | `back-office.e2e.ts` (báo cáo) |
| FR-R-06 | Xuất Excel/PDF | `reports/export.py` | E-02 nút trong `ReportsPage.tsx` | `test_reports.py::test_exports_open_as_excel_and_pdf` | |
| FR-A-01 | Quản lý tài khoản | `users/service.py` | A-01, A-02 `admin/pages/UsersPage.tsx`, `UserFormPage.tsx` | `test_users.py` (7 test) | |
| FR-A-02 | Phân quyền | `rbac/service.py` | A-03 `admin/pages/RolesPage.tsx` | `test_rbac.py` (5 test) | `public.e2e.ts` (tài xế không vào được `/hub`) |
| FR-A-03 | Đăng nhập, OTP, quên mật khẩu | `auth/service.py` | D-01..D-03 `auth/pages/` | `test_auth.py` (14 test) | `helpers.ts::demoLogin` |
| FR-A-04 | Giám sát hệ thống, cấu hình | `admin/service.py`, `audit/` | A-04..A-07 `admin/pages/HubsPage.tsx`, `ShiftsPage.tsx`, `SettingsPage.tsx`, `AuditPage.tsx` | `test_admin_config.py` (3 test) | `back-office.e2e.ts` (cấu hình, audit) |
| FR-J-01 | Tự lọc và gán tài xế | `dispatch/service.py` | | `test_dispatch.py` (4 test), `test_worker.py::test_due_dispatch_job_makes_an_offer` | |
| FR-J-02 | Tính ETA tự động | `tracking/service.py::estimate_driver_etas`, `routing/osrm.py` | D-07, D-12, H-03 | `test_routing.py::test_eta_uses_road_durations_when_available`, `::test_eta_falls_back_to_an_estimate_without_osrm` | |
| FR-J-03 | Đồng bộ dữ liệu với sàn | `partner/webhooks.py` (outbox) | S-02, S-03 `shopnow/pages/TrackPage.tsx` | `test_webhooks.py` (5 test) | `delivery.e2e.ts`, `incident.e2e.ts` (khách thấy cập nhật) |

## Quy tắc nghiệp vụ và ngoại lệ

| Yêu cầu | Nội dung | Code | Test |
|---|---|---|---|
| BR3 | Thứ tự trạng thái đơn | `orders/state_machine.py` | `test_state_machine.py` |
| BR4 | Lọc tài xế đủ điều kiện | `dispatch/service.py::rank_candidates` (bước lọc SQL) | `test_dispatch.py::test_only_eligible_drivers_are_ranked_nearest_first` |
| BR5 | Chấm điểm có trọng số | `dispatch/service.py::rank_candidates` (bước chấm điểm) | như trên |
| BR6–BR7 | Mời lần lượt, hết giờ coi như từ chối | `dispatch/service.py::expire_offer` | `test_dispatch.py::test_unanswered_offer_moves_to_next_driver_then_first_accept_wins` |
| BR8 | Người nhận đầu tiên được đơn | `dispatch/service.py::accept_offer` | như trên |
| BR8–BR9 (QT2) | Quét mã rồi mới giao | `delivery/service.py` | `test_delivery.py::test_scan_start_and_deliver_with_proof` |
| BR10–BR11 | ETA và thông báo khách | `tracking/service.py`, `partner/webhooks.py` | `test_webhooks.py::test_tracking_page_shows_delay_apology_then_delivery` |
| BR12 | Phát hiện bất thường | `tracking/anomaly.py` | `test_simulation.py::test_idle_driver_raises_one_incident`, `::test_eta_slipping_three_times_raises_eta_anomaly` |
| BR13–BR15 | Phân loại, phản hồi, giải pháp sự cố | `incidents/service.py` | `test_incidents.py` (5 test) |
| BR16–BR17 | Ảnh minh chứng, giao thất bại | `delivery/service.py::deliver`, `::fail` | `test_delivery.py::test_failed_attempt_with_date_is_rescheduled_then_released`, `::test_failed_attempt_without_date_returns_to_hub` |
| EX2 | Không có tài xế | `dispatch/service.py::run_dispatch` | `test_dispatch.py::test_no_driver_available_retries_later` |
| EX3 | Hết vòng mời → `ON_HOLD` | `dispatch/service.py` | `test_dispatch.py::test_order_goes_on_hold_after_every_round_is_declined` |
| EX4 | Trả đơn trước khi lấy hàng | `delivery/service.py::release` | `test_delivery.py::test_driver_gives_order_back_only_before_pickup` |
| EX5, EX6 | Tài xế đứng yên, ETA trễ dần | `tracking/anomaly.py` | `test_simulation.py` |
| EX7 | Webhook lỗi thì thử lại | `partner/webhooks.py` | `test_webhooks.py::test_failed_delivery_is_retried_with_backoff_then_given_up` |

## Phi chức năng

| Yêu cầu | Cách đáp ứng | Kiểm chứng |
|---|---|---|
| NFR-01 Tìm tài xế < 5 giây | Lọc bằng SQL có index, chấm điểm haversine trong bộ nhớ, không gọi OSRM khi chấm điểm | Test điều phối; benchmark 10.000 tài xế **chưa làm** |
| NFR-02 Mật khẩu, HTTPS | Argon2id; HTTPS do Vercel/Render cung cấp | `test_auth.py` |
| NFR-04 Chịu lỗi | ETA dự phòng khi OSRM lỗi; webhook qua outbox; job lỗi thử lại | `test_routing.py::test_failure_returns_nothing_and_cools_down`, `test_worker.py::test_failing_job_is_retried_then_marked_failed` |
| Realtime | WebSocket, token ở tin nhắn đầu | `test_realtime.py` |

Một số tên file frontend ở trên là tên trang chính của nhóm chức năng; các component phụ nằm cùng thư mục `components/` của feature đó.
