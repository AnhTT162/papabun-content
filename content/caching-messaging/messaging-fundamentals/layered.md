## Quick

Gửi **message** qua một broker thay vì gọi trực tiếp giúp hai bên **tách rời về thời gian**: bên gửi không chờ, bên nhận xử lý theo sức mình, và lỗi tạm thời được retry. **[[message-queue|Queue]]**: mỗi message chỉ một consumer xử lý. **[[pub-sub|Pub/sub]]**: mỗi subscriber nhận một bản. Hầu hết hệ thống thật giao message **ít nhất một lần** (at-least-once), nên **consumer phải [[idempotent-consumer|idempotent]]**, và message lỗi mãi phải được đưa vào **[[dead-letter-queue|DLQ]]**.

## Interview

**Khi nào dùng bất đồng bộ**: việc không cần kết quả ngay (gửi email, tạo hoá đơn), cần hấp thụ đợt tăng tải, hoặc một sự kiện có nhiều bên quan tâm. Cái giá: dữ liệu nhất quán sau một lúc (eventual consistency), khó lần theo luồng xử lý, thêm một hệ thống phải vận hành.

**Queue và pub/sub**:
- Queue (point-to-point): nhiều consumer cùng đọc một queue thì mỗi message chỉ tới một người ([[competing-consumers|competing consumers]]), thêm consumer là tăng tốc độ xử lý.
- Pub/sub: mỗi subscriber có bản riêng ([[fan-out|fan-out]]).
- Kafka kết hợp cả hai: mỗi consumer group nhận đủ mọi message, trong một group thì mỗi partition chỉ một consumer, nên số consumer có ích bị giới hạn bởi số partition.

**Ack và giao lại**: consumer nhận message, xử lý, rồi mới [[message-ack|ack]] (SQS: `DeleteMessage`). Chưa ack thì message được giao lại: SQS sau [[visibility-timeout|visibility timeout]] (mặc định 30 giây), RabbitMQ khi channel hay connection đóng hoặc consumer nack kèm requeue.

**[[delivery-semantics|Ba mức đảm bảo]]**:
- **At-most-once**: ack trước khi xử lý; chết giữa chừng là mất message.
- **At-least-once**: ack sau khi xử lý; chết sau khi xử lý mà trước khi ack thì bị xử lý lại.
- **Exactly-once**: chỉ có trong phạm vi một hệ thống (Kafka transaction đọc, xử lý, ghi lại Kafka). SQS FIFO chỉ khử trùng lúc gửi trong 5 phút; consumer vẫn có thể nhận lại. Hiệu ứng ra ngoài (database, email, thanh toán) đạt được "đúng một lần" chỉ nhờ consumer idempotent.

**Message lỗi**: retry có backoff; lỗi quá N lần (SQS `maxReceiveCount`) thì chuyển vào DLQ để không chặn các message khác, kèm cảnh báo và cách đẩy lại sau khi sửa. Message không bao giờ xử lý được là [[poison-message|poison message]].

**Thứ tự**: queue thường không đảm bảo thứ tự khi có nhiều consumer. Cần thứ tự thì phân nhóm theo khoá (SQS FIFO message group, partition key của Kafka) và chấp nhận mỗi nhóm chỉ xử lý tuần tự.

## Deep

- **Consumer idempotent làm thế nào**:
  - Bảng `processed_message(message_id PRIMARY KEY)` được ghi **trong cùng transaction** với thay đổi dữ liệu; trùng khoá nghĩa là đã xử lý, bỏ qua và ack.
  - Hoặc thao tác tự nhiên idempotent: `UPDATE order SET status = 'PAID' WHERE id = ? AND status = 'PENDING'`, upsert theo khoá nghiệp vụ.
  - Gọi hệ thống bên ngoài (thanh toán) thì gửi [[idempotency-key|idempotency key]] lấy từ message.
  - Kiểm tra "đã xử lý chưa" ở Redis rồi mới xử lý thì có khoảng hở giữa kiểm tra và ghi; chỉ dùng được làm lớp lọc nhanh.
- **Visibility timeout của SQS**:
  - Message đang được xử lý bị ẩn khỏi các consumer khác trong khoảng này (mặc định 30 giây, tối đa 12 giờ). Hết giờ mà chưa xoá thì người khác nhận được.
  - Xử lý lâu hơn timeout là cách phổ biến nhất để một message bị xử lý **song song** hai lần. Đặt timeout lớn hơn thời gian xử lý tệ nhất, hoặc gia hạn bằng `ChangeMessageVisibility` khi việc còn đang chạy.
  - `ApproximateReceiveCount` (phải yêu cầu qua thuộc tính hệ thống khi nhận) cho biết message đã được nhận bao nhiêu lần; SQS tự chuyển sang DLQ khi vượt `maxReceiveCount` của redrive policy. Vì mỗi lần hết timeout là một lần nhận, message chậm nhưng **vẫn xử lý thành công** cũng có thể bị đẩy vào DLQ: DLQ có message mà log không có lỗi.
- **SQS standard và FIFO**:
  - Standard: gần như không giới hạn throughput, at-least-once, thứ tự chỉ là cố gắng (best-effort).
  - FIFO: thứ tự trong mỗi `MessageGroupId`, khử trùng theo `MessageDeduplicationId` trong 5 phút, throughput có giới hạn theo từng queue (chế độ high throughput nâng giới hạn này lên nhiều). Một message trong group đang lỗi chặn mọi message sau nó trong group đó.
  - Long polling (`WaitTimeSeconds` tới 20 giây) giảm số lần nhận rỗng, tức giảm chi phí và độ trễ.
- **SNS + SQS fan-out**: service đặt hàng publish một lần lên SNS topic; mỗi bên quan tâm (email, kho, phân tích) có SQS queue riêng subscribe vào. Một bên chậm hay lỗi không ảnh hưởng bên khác, mỗi bên có DLQ riêng. Subscription filter policy cho mỗi queue chỉ nhận loại sự kiện nó cần.
- **Retry đúng cách**:
  - Phân biệt lỗi tạm thời (timeout, 503) với lỗi vĩnh viễn (dữ liệu sai, 400). Lỗi vĩnh viễn đưa thẳng vào DLQ, retry chỉ tốn tài nguyên.
  - [[retry-backoff|Backoff]] tăng dần kèm jitter, để không cùng lúc dội lại hệ thống vừa phục hồi.
  - DLQ không phải thùng rác: cần cảnh báo khi có message, công cụ xem nội dung, và cách đẩy lại (SQS có redrive từ DLQ về queue gốc).
  - Với SQS standard, message chuyển sang DLQ **giữ nguyên thời điểm vào queue ban đầu**: đã nằm 3 ngày ở queue gốc mà DLQ giữ 4 ngày thì chỉ còn 1 ngày trước khi bị xoá. Đặt retention của DLQ dài hơn queue gốc (thường 14 ngày).
- **Thứ tự và song song**: cần thứ tự theo đơn hàng thì khoá nhóm là `order_id`, không phải một nhóm cho cả hệ thống, để các đơn khác nhau vẫn xử lý song song. Kể cả có thứ tự, retry và giao lại vẫn có thể làm message đến trễ; consumer nên kiểm tra phiên bản hoặc trạng thái thay vì tin vào thứ tự.
- **Lỗi từ phía producer**:
  - Ghi database rồi gửi message là [[dual-write|dual write]]: commit xong mà gửi lỗi thì mất sự kiện; gửi trước rồi commit lỗi thì có sự kiện cho thứ không tồn tại. Cách đúng là [[outbox|transactional outbox]] (bài Transactional outbox & CDC).
  - Producer gửi, broker đã lưu nhưng phản hồi bị mất, producer gửi lại: trùng ngay từ đầu nguồn. Kafka chặn trường hợp này bằng idempotent producer (bật mặc định từ client 3.0), nhưng chỉ với retry nội bộ của client trong một phiên producer: ứng dụng tự bắt lỗi rồi gọi `send` lại, hoặc producer khởi động lại, thì vẫn trùng. Với SQS standard thì consumer phải tự khử trùng.
- **[[backpressure|Backpressure]] và giám sát**: queue cho phép producer nhanh hơn consumer một thời gian, không phải mãi mãi. Theo dõi độ dài queue và **tuổi của message cũ nhất** (SQS `ApproximateAgeOfOldestMessage`, Kafka consumer lag): tuổi tăng đều là consumer không theo kịp. SQS giữ message tối đa 14 ngày (mặc định 4); quá hạn là message bị xoá âm thầm.
- **Push và pull**: RabbitMQ đẩy message tới consumer, giới hạn số message chưa ack bằng `prefetch`; SQS và Kafka để consumer tự kéo về. Prefetch quá lớn làm một consumer ôm nhiều message trong khi consumer khác rảnh.
- **Message nên nhỏ**: broker có giới hạn kích thước và message lớn làm chậm cả hệ thống. Payload lớn (file, ảnh) đặt ở object storage, message chỉ mang đường dẫn (claim check).
- **Request/reply qua queue** để giả lập gọi đồng bộ (gửi rồi chờ message trả lời) thường có hết nhược điểm của cả hai: vừa chậm, vừa phức tạp. Cần kết quả ngay thì gọi trực tiếp.
- **Spring: exception trong listener được xử lý rất khác nhau theo thư viện**, phải cấu hình và kiểm thử, không giả định:
  - Spring Kafka (`@KafkaListener`): `DefaultErrorHandler` mặc định thử 10 lần liên tiếp không nghỉ, rồi **log lỗi, commit offset và bỏ qua record**: message mất âm thầm nếu không cấu hình `DeadLetterPublishingRecoverer`. Lỗi deserialize bỏ qua retry ngay từ đầu.
  - Spring AMQP (`@RabbitListener`): mặc định requeue message lỗi, với classic queue là lặp mãi; quorum queue từ RabbitMQ 4.0 giới hạn 20 lần giao (`delivery-limit`), quá thì bỏ hoặc chuyển sang dead-letter exchange nếu có.
  - Spring Cloud AWS (`@SqsListener`): mặc định chỉ xoá khi xử lý thành công; lỗi thì message hiện lại sau visibility timeout, tới `maxReceiveCount` thì vào DLQ.
