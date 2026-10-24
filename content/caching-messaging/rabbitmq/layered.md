## Quick

RabbitMQ là **broker thông minh**: producer gửi message tới một **[[amqp-exchange|exchange]]**, exchange dựa vào **[[routing-key|routing key]]** và binding để chép message vào các **queue**, broker **đẩy** message tới consumer và **xoá message khi consumer [[message-ack|ack]]**. Kafka ngược lại: một log lưu theo thời gian, consumer tự kéo và tự giữ offset, đọc lại được. Muốn không mất message trên RabbitMQ cần đủ ba thứ: queue bền vững (**[[quorum-queue|quorum queue]]**), **[[publisher-confirm|publisher confirm]]**, và **ack thủ công** sau khi xử lý xong; cộng consumer idempotent vì có thể nhận trùng. **[[prefetch|Prefetch]]** có giới hạn thì giúp chia việc đều.

## Interview

**Định tuyến**: bốn loại exchange.
- `direct`: khớp đúng routing key.
- `topic`: khớp mẫu, `*` một từ, `#` không hoặc nhiều từ (`order.*.paid`).
- `fanout`: chép cho mọi queue được bind, bỏ qua key.
- `headers`: khớp theo header, ít dùng.

Exchange mặc định (tên rỗng) gửi thẳng vào queue trùng tên với routing key. Thêm consumer vào cùng một queue là thêm người xử lý ([[competing-consumers|competing consumers]]).

**Loại queue**:
- **Classic**: một node giữ dữ liệu; mirrored classic queue đã bị bỏ ở RabbitMQ 4.0.
- **Quorum**: nhân bản bằng Raft trên 3 hoặc 5 node, cần đa số node sống để chạy, là lựa chọn mặc định cho dữ liệu quan trọng.
- **[[rabbitmq-stream|Stream]]**: log chỉ ghi nối, consumer đọc theo offset và đọc lại được, giống Kafka.

**Không mất message**:
- Producer bật publisher confirm và chờ broker xác nhận, kèm cờ `mandatory` để biết message không vào được queue nào.
- Consumer ack **sau** khi xử lý; lỗi thì `nack` với `requeue=false` để message sang **[[dead-letter-exchange|dead-letter exchange]]** rồi vào [[dead-letter-queue|DLQ]].
- Consumer vẫn có thể nhận trùng, nên phải [[idempotent-consumer|idempotent]].

**Prefetch** (`basic.qos`) giới hạn số message chưa ack mỗi consumer giữ. Quá lớn thì một consumer ôm hàng nghìn message trong khi consumer khác rảnh; `autoAck` không có giới hạn này và mất mọi message đang giữ khi pod chết.

**Thứ tự**: một queue giao theo thứ tự FIFO, nhưng nhiều consumer, message bị requeue, hay message giao lại khi consumer chết đều có thể làm đảo thứ tự. Cần thứ tự thì dùng single active consumer, hoặc chia nhiều queue theo khoá.

**Chọn RabbitMQ khi** cần định tuyến linh hoạt, phân việc cho worker với ack từng message, priority, TTL, độ trễ thấp. **Chọn Kafka khi** cần lưu sự kiện để đọc lại, nhiều nhóm consumer độc lập, throughput rất cao và thứ tự theo key.

## Deep

- **Connection và channel**:
  - Một connection TCP chứa nhiều channel; mọi lệnh AMQP chạy trên channel.
  - Mở connection cho mỗi message tốn handshake TCP và TLS, làm broker quá tải.
  - Channel của Java client không nên dùng chung giữa các thread để publish. Spring AMQP `CachingConnectionFactory` giữ một connection và cache channel (mặc định 25).
- **Publisher confirm chi tiết**:
  - Confirm đến **không đồng bộ**; chờ từng message một (`waitForConfirms` sau mỗi lần gửi) làm throughput giảm hàng chục lần. Gửi lô rồi theo dõi theo sequence number.
  - Message không khớp binding nào bị **bỏ âm thầm** nếu không có `mandatory` hoặc alternate exchange; confirm vẫn báo `ack` vì broker đã xử lý xong.
  - Spring Boot: `spring.rabbitmq.publisher-confirm-type=correlated`, `publisher-returns=true`, `spring.rabbitmq.template.mandatory=true`.
  - Với classic queue, chỉ message persistent (`delivery_mode=2`) trên queue durable mới sống sót sau khi broker khởi động lại; quorum queue và stream luôn ghi đĩa.
  - Ghi database rồi publish vẫn là [[dual-write|dual write]]; confirm không thay được [[outbox|outbox]].
- **Ack mode của Spring AMQP**:
  - Mặc định `AUTO`: container ack khi listener trả về bình thường, `nack` khi ném exception, và **requeue** (`defaultRequeueRejected=true`).
  - Ngoại lệ: lỗi mà `ConditionalRejectingErrorHandler` coi là fatal (convert message thất bại, `@Valid` không qua, sai kiểu tham số) bị reject **không** requeue; không có dead-letter exchange thì message mất âm thầm.
  - Với classic queue, một [[poison-message|poison message]] quay vòng mãi, CPU broker và consumer cao, log đầy. Ném `AmqpRejectAndDontRequeueException` hoặc đặt `defaultRequeueRejected=false` cho lỗi vĩnh viễn.
  - Retry trong consumer: `RetryInterceptorBuilder` có backoff, và khi hết lượt thì dùng `RejectAndDontRequeueRecoverer` (hoặc `RepublishMessageRecoverer`) để message sang dead-letter. Recoverer mặc định của Spring AMQP chỉ log cảnh báo rồi ack, tức message mất.
  - Quorum queue từ 4.0 có `delivery-limit` mặc định 20: quá số lần giao thì message bị bỏ, hoặc chuyển sang dead-letter exchange nếu có cấu hình. Từ 4.3, `delivery-count` chỉ đếm lần xử lý lỗi, còn số lần requeue nói chung đếm riêng (`acquired-count`).
  - Prefetch mặc định của Spring AMQP là 250; message xử lý lâu (vài giây) thì giảm xuống 1–10 để chia việc đều.
- **Dead-lettering**: message sang dead-letter exchange khi bị `reject`/`nack` không requeue, hết TTL, queue vượt giới hạn độ dài (`x-max-length` với `overflow=drop-head`), hoặc vượt `delivery-limit` của quorum queue. Header `x-death` ghi lý do và số lần. Dead-letter của quorum queue mặc định `at-most-once`; đặt `dead-letter-strategy=at-least-once` (cần `overflow=reject-publish`) để không mất message trên đường sang DLQ.
- **Retry có độ trễ**:
  - Kiểu phổ biến: queue chờ có `x-message-ttl` cố định, hết TTL thì dead-letter quay về queue chính. Mỗi mức trễ một queue chờ (5 giây, 1 phút, 10 phút).
  - TTL đặt **trên từng message** chỉ được kiểm tra ở đầu queue: message TTL 10 giây nằm sau message TTL 1 giờ phải chờ cả giờ ([[head-of-line-blocking|head-of-line blocking]]).
  - Plugin delayed message exchange đã ngừng phát triển (archived từ 4.3): không nhân bản, không hỗ trợ `mandatory`, tắt plugin là mất message hẹn giờ. Không dùng cho hệ mới.
  - Bản mới có sẵn trong quorum queue: delayed retry từ 4.3 (`x-delayed-retry-type`, `x-delayed-retry-min`, `x-delayed-retry-max`, backoff tuyến tính), và hẹn giờ giao message từ 4.4 (`x-opt-delivery-time` qua AMQP 1.0). Cần đúng các mức trễ cố định (10 giây, 1 phút, 5 phút) thì mẫu queue chờ + TTL vẫn là cách chạy được trên mọi phiên bản; nhiều message hẹn giờ xa thì cân nhắc lịch trong database.
- **Quorum queue**:
  - Ghi cần đa số **replica** xác nhận (mặc định 3 replica, kể cả trong cụm 5 node): 3 replica chịu được mất 1. Tốn đĩa và RAM hơn classic, không hợp cho queue tạm thời không cần bền vững (`exclusive`, auto-delete).
  - Priority: classic queue dùng `x-max-priority`. Quorum queue 4.0–4.2 có hai mức tương đối, giao theo tỉ lệ khoảng 2:1, không phải ưu tiên tuyệt đối; từ 4.3 có 32 mức ưu tiên nghiêm ngặt (0–31, mặc định 4, bỏ qua `x-max-priority`), nên luồng ưu tiên cao liên tục có thể làm message ưu tiên thấp chờ mãi.
  - Leader của các queue nên rải đều trên các node; sau khi một node khởi động lại, kiểm tra lại phân bố (`rabbitmq-queues rebalance`).
- **Queue dài là trạng thái xấu**: RabbitMQ chạy tốt nhất khi queue gần rỗng. Khi bộ nhớ vượt `vm_memory_high_watermark` hoặc đĩa trống dưới `disk_free_limit`, broker **chặn mọi publisher** (`connection.blocked`): một consumer chậm làm cả hệ thống ngừng gửi. Theo dõi số message ready/unacked, tốc độ publish và ack, và đặt `x-max-length` hoặc TTL cho queue có thể phình.
- **Consumer giữ message quá lâu**: trước 4.3, broker đóng channel khi một delivery chưa ack quá `consumer_timeout` (mặc định 30 phút), và message được giao lại. Từ 4.3 chỉ quorum queue áp timeout: consumer bị huỷ (cancel), message quay lại queue; classic queue không còn kiểm tra; chỉnh riêng bằng `x-consumer-timeout`. Việc dài hơn thế không nên chạy trong listener; nhận message, ghi việc vào database, ack, rồi xử lý riêng.
- **Stream và super stream**: stream giữ dữ liệu theo dung lượng hoặc thời gian, nhiều consumer đọc độc lập từ offset tuỳ chọn, throughput cao nhất với client giao thức stream riêng. Super stream chia một stream logic thành nhiều partition theo key, tương tự partition của Kafka.
- **So với Kafka ở mức sâu**:
  - Ack theo từng message cho phép bỏ qua một message lỗi mà không chặn message sau; Kafka commit offset theo vị trí, message lỗi phải được chuyển đi (retry topic, DLT) để partition chạy tiếp.
  - Kafka chia việc theo partition, nên số consumer có ích bị giới hạn bởi số partition; RabbitMQ thêm consumer vào queue là có thêm người xử lý. Share groups (KIP-932, sẵn sàng production từ Kafka 4.2) cho Kafka cách chia việc theo message.
  - RabbitMQ định tuyến ở broker; Kafka để consumer tự lọc, hoặc tách topic (bài Kiến trúc Kafka).
- **Giao thức**: RabbitMQ 4.0 hỗ trợ AMQP 1.0 ngay trong lõi, bên cạnh AMQP 0-9-1 mà Spring AMQP dùng; MQTT và STOMP qua plugin. Từ 4.3, metadata của cụm chỉ lưu trong Khepri (dựa trên Raft); Mnesia và các chiến lược `pause_minority`, `autoheal` đã bị gỡ. Nâng từ 4.2 lên phải bật feature flag `khepri_db` trước: một bẫy nâng cấp hay gặp.
