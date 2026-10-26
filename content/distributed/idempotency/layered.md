## Quick

Một thao tác [[idempotency|idempotent]] khi làm nhiều lần cho cùng kết quả (cùng trạng thái hệ thống) như làm một lần. Qua mạng, retry là bắt buộc, nên **mọi thao tác ghi có thể bị gửi lại phải idempotent**. Thao tác vốn không idempotent (tạo đơn, trừ tiền) được làm cho idempotent bằng [[idempotency-key|idempotency key]]: client sinh key cho mỗi **thao tác** (không phải mỗi lần thử), server **giữ chỗ cho key trước** dưới một unique constraint (chỉ một request thắng), **đánh dấu hoàn tất cùng transaction với thay đổi nghiệp vụ**, và trả lại kết quả cũ khi gặp key đã xử lý.

## Interview

**Idempotent sẵn và không**: theo HTTP, `GET`, `PUT`, `DELETE` là idempotent, `POST` thì không. `DELETE` lần hai trả `404` vẫn là idempotent: trạng thái sau cùng như nhau. `UPDATE orders SET status = 'PAID' WHERE id = ? AND status = 'PENDING'` idempotent; `UPDATE accounts SET balance = balance - 100` thì không.

**Cài đặt idempotency key đúng cách**:
1. Client sinh UUID cho thao tác (bấm "Thanh toán" một lần) và gửi lại **cùng key** ở mọi lần retry, thường qua header `Idempotency-Key`.
2. Server `INSERT` một dòng `(key, user_id, request_hash, status = IN_PROGRESS)` với unique constraint trên `(user_id, key)` **trước** khi làm việc. Ai insert được thì làm; ai trùng thì không làm lại.
3. Làm thao tác nghiệp vụ và cập nhật dòng key thành `COMPLETED` kèm response, **trong cùng transaction** với thay đổi nghiệp vụ.
4. Gặp key đã `COMPLETED`: trả lại response đã lưu. Key đang `IN_PROGRESS`: trả `409` để client thử lại sau. Cùng key nhưng nội dung request khác (hash khác): trả `422`, vì client đang dùng nhầm key.

**Bẫy hay gặp**:
- Kiểm tra "key đã có chưa" rồi mới làm: hai request trùng đến cùng lúc đều thấy "chưa có" ([[check-then-act|check-then-act]]).
- Lưu key ở Redis, còn kết quả nghiệp vụ ở database: crash giữa hai bước là lệch.
- Client sinh key mới cho mỗi lần retry: key không còn tác dụng gì.

**Phía consumer**: message được giao ít nhất một lần, nên consumer phải [[idempotent-consumer|idempotent]] theo id của message hoặc khoá nghiệp vụ (bài Messaging fundamentals).

## Deep

- **Exactly-once là [[delivery-semantics|at-least-once]] cộng idempotent**: chi tiết phía Kafka (idempotent producer, transaction, consumer) ở bài Messaging fundamentals và Kafka producer & consumer.
- **Một transaction có đủ không**: khi thao tác chỉ ghi database (không gọi ra ngoài), insert key và thay đổi nghiệp vụ trong **một** transaction là đủ và đơn giản nhất. Với PostgreSQL, request trùng chạy `INSERT ... ON CONFLICT DO NOTHING` sẽ **chờ** trên unique index tới khi transaction đầu commit (rồi insert 0 dòng) hoặc rollback (rồi insert thành công). Hai pha `IN_PROGRESS` rồi `COMPLETED` chỉ cần khi có tác dụng phụ ra ngoài kéo dài, để không giữ transaction và khoá trong lúc chờ.
- **Tác dụng phụ ra ngoài database**: gọi cổng thanh toán, gửi email, gọi service khác không nằm trong transaction của bạn. Truyền tiếp idempotency key xuống (cổng thanh toán lớn đều hỗ trợ), hoặc ghi việc cần làm vào [[outbox]] và để worker gửi với key dẫn xuất từ key gốc.
- **Ngữ nghĩa khi lần đầu lỗi**: nên lưu và trả lại cả kết quả lỗi nghiệp vụ (thẻ bị từ chối) để retry không đổi kết quả. Nhưng lỗi xảy ra trước khi bắt đầu xử lý (validate thất bại, mất kết nối database) thì không lưu key, để client sửa và gửi lại.
- **Phạm vi và thời hạn của key**: key gắn với người dùng (hoặc tenant) và endpoint, để key của người này không chặn người khác. Giữ key đủ lâu để phủ khoảng thời gian retry (thường 24 giờ tới vài ngày), rồi dọn bằng job theo `created_at`.
- **MySQL**: dùng `INSERT ... ON DUPLICATE KEY UPDATE id = id` thay cho `ON CONFLICT DO NOTHING`, và kiểm tra số dòng ảnh hưởng (quy ước khác PostgreSQL: cập nhật một dòng có sẵn tính là 2). Tránh `INSERT IGNORE`: nó biến cả các lỗi khác (dữ liệu quá dài, sai kiểu) thành warning.
- **Chuẩn hoá**: bản thảo IETF `draft-ietf-httpapi-idempotency-key-header` mô tả header `Idempotency-Key`, mã `400` khi endpoint bắt buộc mà thiếu key, `409` và `422`; và khuyên key đủ ngẫu nhiên (UUID v4) để không ai đoán được key của client khác. Nhiều API thanh toán công khai dùng đúng ngữ nghĩa này.
- **`PUT` idempotent nhưng vẫn có [[lost-update|lost update]]**: hai client cùng `PUT` bản đầy đủ của một tài nguyên thì bản sau ghi đè bản trước. Idempotency không thay cho kiểm soát đồng thời; dùng [[etag|`ETag`]] với `If-Match` hoặc cột version (bài Optimistic & pessimistic locking).
- **Idempotent tự nhiên thay vì bảng key**: [[upsert|upsert]] theo khoá nghiệp vụ (`INSERT ... ON CONFLICT (order_id) DO NOTHING`), chuyển trạng thái có điều kiện, hay đặt giá trị tuyệt đối (`SET quantity = 5`) thay vì cộng dồn (`quantity = quantity + 1`). Khi làm được, cách này đơn giản hơn bảng idempotency key.
- **Thứ tự**: idempotent không có nghĩa là đúng thứ tự. Event `OrderShipped` đến trước `OrderPaid` vẫn cần xử lý riêng (bỏ qua chuyển trạng thái không hợp lệ, hay xử lý lại sau).
- **Webhook từ bên ngoài**: nhà cung cấp gửi lại webhook nhiều lần khi không nhận được `2xx`. Lưu `event_id` của họ với unique constraint, xử lý trong cùng transaction, và trả `2xx` cho bản trùng.
