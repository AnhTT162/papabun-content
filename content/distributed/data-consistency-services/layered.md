## Quick

Khi mỗi service sở hữu database riêng, **không còn transaction ACID bao nhiều service**. Dữ liệu giữa các service chỉ có [[eventual-consistency|eventual consistency]], và việc của kiến trúc là làm cho nó **hội tụ chắc chắn**. Bẫy số một là [[dual-write|dual write]]: ghi database rồi gửi message (hoặc gọi service khác) như hai bước rời, crash giữa hai bước là lệch. Bộ công cụ: [[outbox|outbox]] hoặc [[cdc|CDC]] để ghi và phát event nguyên tử, [[saga|saga]] cho nghiệp vụ nhiều bước có bù trừ, [[idempotent-consumer|consumer idempotent]], và [[reconciliation|reconciliation]] làm lưới an toàn cuối cùng.

## Interview

**Dual write hỏng theo hai chiều**:
- Database commit, gửi Kafka lỗi (broker chậm, pod bị kill): đơn tồn tại nhưng Inventory không bao giờ biết.
- Gửi Kafka trong method `@Transactional`, rồi database rollback (vi phạm constraint ở bước sau): consumer xử lý event của một đơn **không tồn tại**.

`@TransactionalEventListener(AFTER_COMMIT)` gửi sau commit nên tránh được chiều thứ hai, nhưng pod chết ngay sau commit vẫn mất event; exception trong listener cũng không báo về bên gọi, và publish khi không có transaction thì listener không chạy (trừ khi `fallbackExecution = true`).

**Outbox**: trong cùng transaction với thay đổi nghiệp vụ, ghi event vào bảng `outbox`. Một relay (poller hoặc CDC như Debezium đọc WAL) đẩy sang broker và đánh dấu đã gửi. Kết quả: event chắc chắn được phát **ít nhất một lần** nếu và chỉ nếu transaction commit (bài Transactional outbox & CDC).

**Vì sao không dùng 2PC**: coordinator chết giữa chừng làm các bên giữ khoá chờ; mọi bên phải hỗ trợ XA (Kafka, REST API thì không); thêm vòng mạng cho mỗi giao dịch (bài 2PC & giao dịch phân tán).

**Saga**: chuỗi transaction cục bộ; bước sau lỗi thì chạy bước bù trừ cho các bước trước. Bù trừ là hành động nghiệp vụ mới (hoàn tiền, nhả hàng), không phải rollback (bài Saga).

**Đọc dữ liệu của service khác**: gọi API khi cần (API composition), hoặc giữ bản sao cục bộ cập nhật bằng event; bản sao đọc nhanh, chịu được service kia chết, đổi lại có thể cũ.

## Deep

- **Kafka transaction không bao được database**: transaction của Kafka chỉ nguyên tử cho chuỗi đọc, xử lý, ghi lại Kafka. Ghi PostgreSQL và gửi Kafka vẫn là hai hệ thống; `ChainedTransactionManager` chỉ commit lần lượt, không nguyên tử (deprecated từ Spring Data Commons 2.5). `KafkaTemplate` có `transactionIdPrefix` thì Spring Kafka đồng bộ một Kafka transaction vào transaction database: database commit trước, Kafka commit sau (best-effort 1PC). Database rollback thì message bị abort, nhưng Kafka commit lỗi sau khi database đã commit thì event vẫn mất, nên cách này không thay được outbox.
- **"Listen to yourself"**: service chỉ ghi event vào Kafka, rồi chính nó tiêu thụ event để cập nhật database của mình. Không còn dual write, nhưng service không đọc được ngay dữ liệu mình vừa ghi, và kiểm tra ràng buộc (còn hàng không, email đã tồn tại chưa) trở nên khó.
- **Trạng thái trung gian thay cho khoá**: đơn ở `PENDING` cho tới khi giữ hàng và thanh toán xong. Giao diện và các service khác phải hiểu trạng thái này; đây là "semantic lock" của saga, giúp không ai dùng đơn chưa hoàn tất.
- **Bù trừ không hoàn hảo**: email đã gửi thì không thu hồi được, chỉ gửi thêm thư xin lỗi; tiền hoàn có thể mất phí. Thiết kế thứ tự bước để việc khó bù trừ (trừ tiền, gửi hàng) diễn ra sau cùng.
- **Thứ tự và trùng lặp**: event của cùng một đơn nên đi cùng partition (key là `orderId`) để giữ thứ tự; consumer vẫn phải idempotent và bỏ qua chuyển trạng thái không hợp lệ (`OrderShipped` tới khi đơn đã huỷ). Relay của outbox cũng phải giữ thứ tự: nhiều instance poll song song có thể đảo thứ tự event của cùng một đơn (bài Transactional outbox & CDC).
- **Reconciliation không phải dấu hiệu thiết kế kém**: lỗi phần mềm, sự cố của đối tác, thao tác tay trên database đều tạo ra lệch mà không pattern nào chặn hết. Job định kỳ so nguồn sự thật (đơn `PAID` mà không có giao dịch ở cổng thanh toán, hàng bị giữ quá 30 phút mà đơn đã huỷ) rồi tự sửa hoặc mở việc cho người xử lý. Hệ thống tài chính luôn có bước này.
- **Phát hiện saga bị kẹt**: lưu trạng thái của từng saga (hoặc của đơn) kèm thời điểm cập nhật; cảnh báo khi có đơn ở trạng thái trung gian quá lâu. Correlation id xuyên suốt các event giúp lần theo một đơn qua mọi service.
- **Schema của event là hợp đồng công khai**: thay đổi phải tương thích ngược, có version (bài Event schema evolution); event mang đủ dữ liệu để consumer không phải gọi ngược lại service phát ([[event-carried-state|event-carried state transfer]]) khi có thể.
- **Khi nào nên gộp lại**: hai service luôn phải nhất quán ngay với nhau và gọi nhau cho mọi thao tác có thể là một [[bounded-context|bounded context]] bị tách nhầm. Đưa về một service (hoặc một module trong modular monolith) và dùng lại transaction cục bộ thường đơn giản hơn mọi pattern ở trên.
