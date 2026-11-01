## Quick

Hệ thống thanh toán là ba thứ ghép lại: **máy trạng thái cho mỗi lần thử thanh toán**, **gọi cổng thanh toán ([[psp|PSP]]) một cách idempotent**, và **[[double-entry-ledger|sổ cái kép]] làm nguồn sự thật về tiền**, cộng [[reconciliation|đối soát]] hằng ngày với báo cáo bên ngoài. **Quy tắc quan trọng nhất: timeout không phải thất bại.** Không biết kết quả thì ghi `UNKNOWN`, tra lại bằng cùng khoá, và để đối soát chốt; không bao giờ cho người dùng trả lại bằng một lần gọi mới.

## Interview

Tôi hỏi trước: phương thức nào (thẻ có authorize/capture, ví và QR trả qua webhook), một hay nhiều PSP, có giữ tiền hộ người bán (marketplace) không, bao nhiêu giao dịch mỗi giây lúc đỉnh, bao nhiêu loại tiền.

**Mô hình**: `payment` gắn với đơn, mỗi lần gọi PSP là một `payment_attempt` có id riêng, id đó làm [[idempotency-key|idempotency key]] gửi PSP. Ghi attempt `PENDING` và commit **trước** khi gọi, để process chết giữa chừng vẫn biết mình đã gọi gì.

**Gọi PSP**: lỗi mạng hay timeout thì retry với cùng khoá; hết retry thì `UNKNOWN`, job tra trạng thái theo id attempt gửi kèm làm mã tham chiếu. Kết quả cuối đến qua [[webhook|webhook]]: kiểm chữ ký HMAC trên body thô, lưu `event_id` với unique constraint, trả 2xx ngay rồi xử lý. Webhook không theo thứ tự, nên chỉ chuyển trạng thái có điều kiện, không lùi.

**Sổ cái**: mỗi sự kiện tiền là một [[journal-entry|bút toán]] gồm nhiều dòng, tổng nợ bằng tổng có cho từng loại tiền. Không sửa, không xoá; sai thì ghi bút toán đảo. Số dư suy ra từ các dòng. Lab PostgreSQL 17.6: constraint trigger hoãn tới commit chặn bút toán lệch, unique theo nguồn làm lần ghi thứ hai không ghi gì.

**Đối soát**: mỗi ngày so file [[settlement|settlement]] của PSP với sổ cái theo mã tham chiếu, và tổng tiền về ngân hàng với tổng settlement. Lệch đi vào hàng chờ có người xử lý. Đây cũng là nơi `UNKNOWN` được chốt.

**Bẫy**: gọi PSP trong transaction database, coi timeout là thất bại, failover sang PSP khác khi timeout, một cột số dư cập nhật cho tài khoản nóng, tiền kiểu `double`, tin redirect của trình duyệt.

## Deep

- **Dòng tiền thật**:
  - Thẻ: [[payment-authorization|authorize]] (ngân hàng phát hành giữ tiền), capture (xác nhận thu), rồi clearing và settlement: tiền về tài khoản của merchant sau vài ngày làm việc, đã trừ phí. Authorize/capture và thời hạn authorization ở bài Thiết kế đơn hàng & tồn kho.
  - Ví, QR chuyển khoản: người dùng chủ động trả trong app khác, kết quả về qua webhook có khi sau vài phút; không có authorize.
  - Marketplace: platform thu hộ rồi trả cho người bán ([[payout|payout]]) sau khi trừ hoa hồng; tiền chưa trả là nợ của platform, phải hiện trên sổ.
- **[[state-machine|Máy trạng thái]] của attempt**: `CREATED → PENDING → (REQUIRES_ACTION) → AUTHORIZED → CAPTURED`, cộng `FAILED` và `UNKNOWN`. `REQUIRES_ACTION` là [[three-d-secure|3-D Secure]] hay ví chờ người dùng xác nhận. Mọi chuyển trạng thái là [[conditional-update|cập nhật có điều kiện]] `UPDATE ... WHERE status IN (...)` và xử lý nhánh 0 dòng (cách viết ở bài Thiết kế đơn hàng & tồn kho). Trạng thái cuối không lùi: `payment.succeeded` đến sau khi đã `CAPTURED` thì bỏ qua.
- **Ghi trước, gọi sau**:
  - Thứ tự: insert attempt `PENDING` + commit, gọi PSP **ngoài** transaction, rồi cập nhật kết quả trong transaction mới.
  - Gọi PSP trong transaction thì giữ kết nối và khoá suốt 1–3 giây chờ PSP; process chết sau khi PSP đã trừ tiền thì rollback xoá luôn dấu vết.
  - Gửi id attempt kèm làm mã tham chiếu của merchant (metadata, `merchant_reference`). Job phục hồi quét attempt `PENDING` hay `UNKNOWN` quá vài phút và tra PSP theo mã đó: lúc timeout client chưa có id giao dịch của PSP, và PSP thường không cho tra theo idempotency key.
- **Idempotency với PSP**:
  - Retry phải dùng **đúng khoá cũ và đúng tham số cũ**. Stripe (API v1) lưu kết quả lần đầu kể từ khi endpoint bắt đầu chạy, kể cả lỗi 500, báo lỗi nếu cùng khoá mà tham số khác, và có thể xoá khoá sau 24 giờ: retry sau đó tạo **giao dịch mới**. Vì vậy quá 24 giờ chỉ được tra theo mã tham chiếu, không được gửi lại.
  - Phân loại lỗi: mất kết nối hay timeout trước khi có response thì retry cùng khoá (trong 24 giờ, gửi lại chính là cách lấy kết quả đã lưu); request đầu còn đang chạy thì Stripe trả 409, chờ rồi thử lại; đã nhận 5xx thì retry chỉ nhận lại đúng 5xx đó, nên chuyển `UNKNOWN` và tra trạng thái.
  - Khoá phía client (checkout gửi Payment) và khoá phía PSP là hai tầng khác nhau; chi tiết tầng đầu ở bài Idempotency.
- **Timeout là `UNKNOWN`**:
  - Người dùng thấy "đang xử lý", không thấy nút "thử lại". Đơn đang có attempt `UNKNOWN` thì không mở attempt mới bằng phương thức khác, hoặc mở nhưng chấp nhận hoàn tự động nếu cả hai cùng thành công.
  - Không failover sang PSP thứ hai khi timeout: PSP đầu có thể đã trừ tiền. Chỉ chuyển khi lỗi chắc chắn chưa xử lý (không kết nối được, PSP trả mã từ chối cho phép thử lại).
- **Webhook**:
  - Kiểm chữ ký HMAC-SHA256 trên **body thô** (framework parse lại JSON là chữ ký lệch), so sánh thời gian hằng, và chặn timestamp quá cũ (thư viện Stripe mặc định 5 phút) để chống phát lại.
  - Ghi vào bảng inbox với `event_id` unique rồi trả 2xx ngay; xử lý bất đồng bộ. Stripe retry tới 3 ngày nếu không nhận 2xx và không bảo đảm thứ tự event.
  - Payload có thể cũ so với thực tế: khi cần chắc, gọi API lấy trạng thái mới nhất của đối tượng.
  - Không tin redirect của trình duyệt về trang "thành công"; nó chỉ để hiển thị.
- **Sổ cái kép**:
  - Bảng `account` (loại: tài sản, nợ phải trả, doanh thu, chi phí), `journal` (một sự kiện), `ledger_entry` (dòng: tài khoản, loại tiền, số tiền có dấu; quy ước nợ dương, có âm). Tổng các dòng của một journal theo từng loại tiền bằng 0.
  - Ví dụ marketplace, khách trả 100.000 VND, hoa hồng 2.200, phí PSP 1.500:
    - Capture: nợ `psp_receivable` 100.000; có `merchant_payable` 97.800; có `commission_revenue` 2.200.
    - PSP settle: nợ `bank` 98.500; nợ `psp_fee_expense` 1.500; có `psp_receivable` 100.000.
    - Payout: nợ `merchant_payable` 97.800; có `bank` 97.800.
    - Hoàn 30.000 do người bán chịu: nợ `merchant_payable` 30.000; có `psp_receivable` 30.000 (PSP trừ vào lần settle sau).
  - Capture diễn ra liên tục và settle trễ vài ngày nên tổng `psp_receivable` hiếm khi bằng 0. Nhưng phần thuộc các giao dịch của một kỳ settle phải về 0 sau kỳ đó; khác 0 là tiền chưa về hoặc về thiếu. Sổ kép tự chỉ ra chỗ lệch, sổ đơn (một cột số dư) thì không.
  - Lab PostgreSQL 17.6: `CONSTRAINT TRIGGER ... DEFERRABLE INITIALLY DEFERRED` kiểm `sum(amount) = 0` theo journal. Chèn hai dòng lệch (100.000 và -97.800): cả hai `INSERT` chạy được, `COMMIT` báo `journal 1 not balanced`. Kiểm ở commit vì giữa transaction bút toán luôn lệch tạm thời.
  - Ghi idempotent: `journal` có `UNIQUE (source, source_id, kind)`, `INSERT ... ON CONFLICT DO NOTHING RETURNING id`; lab ghi cùng capture hai lần: lần hai trả 0 dòng, sổ vẫn 3 dòng, tổng 0.
  - Không `UPDATE`, không `DELETE` (thu hồi quyền ở database). Sai thì ghi journal đảo và journal đúng, để lịch sử giải thích được mọi con số.
  - Tiền là số nguyên theo [[minor-unit|đơn vị nhỏ nhất]] kèm mã tiền (VND 0 chữ số thập phân; bài BigDecimal & tiền tệ). Đổi tiền đi qua tài khoản FX: mỗi loại tiền tự cân.
- **Tài khoản nóng**: mọi giao dịch của một merchant lớn đều ghi vào `merchant_payable` của nó. Lab PostgreSQL 17.6 (bản x86 chạy qua Rosetta trên M4), 32 kết nối, mỗi journal 3 dòng; số tuyệt đối chỉ để so tương đối, đừng so với lab ở bài khác:
  - Chỉ chèn dòng, không cột số dư: khoảng 30.700 journal/s.
  - Thêm `UPDATE` một dòng số dư của merchant: khoảng 6.100/s, vì mọi transaction xếp hàng trên khoá của dòng đó ([[hot-row|dòng nóng]]).
  - Chia số dư thành 16 dòng con, cộng vào dòng ngẫu nhiên: khoảng 25.400/s; số dư là tổng 16 dòng.
  - Chỉ tài khoản chỉ nhận tiền mới chia được dễ. Ví người dùng cần chặn số dư âm khi trừ thì phải khoá và kiểm một chỗ; tài khoản này ít khi nóng. Dòng nóng chi tiết ở bài Thiết kế đơn hàng & tồn kho.
- **Đối soát**:
  - Ba nguồn: sổ cái, báo cáo settlement của PSP (thường T+1, từng giao dịch, phí, số tiền ròng), sao kê ngân hàng (tổng tiền về).
  - Khớp theo mã tham chiếu PSP (lưu khi gọi). Các loại lệch: có ở PSP mà sổ là `FAILED`/`UNKNOWN` (khách đã bị trừ tiền: ghi nhận thành công hoặc hoàn theo chính sách); có ở sổ mà không có ở PSP (sổ ghi sai, hoặc chưa tới kỳ); lệch số tiền (phí, tỉ giá, hoàn một phần); lệch ngày do mốc chốt sổ khác múi giờ.
  - Lệch tự xử lý theo luật đã duyệt; còn lại vào hàng chờ có tuổi, có người chịu trách nhiệm. Theo dõi số lệch chưa đóng và tổng tiền lệch như một SLO.
- **Hoàn tiền và tranh chấp**:
  - Refund là thao tác riêng có khoá riêng; tổng đã hoàn không vượt số đã capture, chặn bằng `UPDATE ... SET refunded = refunded + :x WHERE refunded + :x <= captured`.
  - [[chargeback|Chargeback]] (chủ thẻ khiếu nại với ngân hàng) đến sau hàng tuần tới vài tháng: ghi bút toán giữ tiền tranh chấp; số dư người bán có thể âm, nên payout giữ lại một phần dự phòng.
- **Payout**: chạy theo lô mỗi kỳ, idempotent theo `(merchant, kỳ)`; số tiền tính từ sổ cái tại một mốc, không từ cột số dư đang thay đổi.
- **Dữ liệu thẻ**: không để số thẻ đi qua server của mình. Dùng trang hay field do PSP host, nhận lại token ([[card-tokenization|tokenization]]); phạm vi [[pci-dss|PCI DSS]] thu nhỏ đáng kể, nhưng không về 0: trang chứa field của PSP vẫn phải kiểm soát script chạy trên đó (PCI DSS 4.0.1). Chi tiết thuộc track Security. Kiểm tra gian lận và rủi ro trước khi gọi PSP là một hệ riêng, không nằm trong bài này.
- **Nhiều PSP**: định tuyến theo phương thức, phí, tỉ lệ thành công; mỗi attempt gắn với đúng một PSP. Báo cáo và webhook của từng PSP khác định dạng: chuẩn hoá về một mô hình nội bộ trước khi đối soát.
- **Nhất quán và triển khai**: payment và sổ cái ở database quan hệ, một nơi ghi chính (không active-active cho tiền). Báo kết quả sang Order qua [[outbox|outbox]]; Order xử lý idempotent (bài Outbox & CDC).
- **Ước lượng**: 800 thanh toán/s lúc đỉnh, PSP trả lời trung bình 2 giây: theo Little's law có khoảng 1.600 lời gọi đang chờ cùng lúc. Gọi PSP bằng virtual thread hay client bất đồng bộ, pool kết nối tới PSP đủ cho số đó; database thì không phải nút cổ chai (vài journal mỗi thanh toán, xa trần đo ở trên).
