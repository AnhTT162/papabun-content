## Quick

Trong [[event-driven-architecture|event-driven architecture]], service **phát event về việc đã xảy ra** (`OrderPlaced`) mà không biết ai nghe; bên quan tâm tự đăng ký và tự phản ứng. Lợi ích: thêm bên nghe không phải sửa bên phát, bên nghe chết không làm hỏng bên phát. Cái giá: dữ liệu chỉ [[eventual-consistency|nhất quán sau một lúc]], **thứ tự chỉ được giữ theo từng key**, event có thể đến **nhiều lần**, và luồng nghiệp vụ không còn nằm ở một chỗ để đọc.

## Interview

**"Event-driven" là bốn thứ khác nhau** (theo Martin Fowler):
- **[[event-notification|Event notification]]**: event chỉ báo hiệu (`OrderPlaced{orderId}`), bên nghe gọi API lấy chi tiết. Đơn giản, nhưng tải dồn ngược về bên phát và bên nghe vẫn phụ thuộc nó.
- **[[event-carried-state|Event-carried state transfer]]**: event mang đủ dữ liệu, bên nghe giữ bản sao cục bộ. Chạy được khi bên phát chết, đổi lại dữ liệu nhân bản và schema là hợp đồng lớn (bài Event schema evolution).
- **[[event-sourcing|Event sourcing]]** và **[[cqrs|CQRS]]**: lưu trạng thái dưới dạng chuỗi event, tách mô hình ghi và đọc. Là cách lưu dữ liệu trong một service, không bắt buộc đi cùng event-driven giữa các service (bài CQRS & Event Sourcing).

**Broker**: Kafka giữ log theo partition, nhiều [[consumer-group|consumer group]] đọc độc lập và đọc lại được; queue cổ điển của RabbitMQ và SQS thì xoá message khi đã ack. Cần đọc lại lịch sử hoặc thêm bên nghe mới thường xuyên thì log hợp hơn (bài Kafka architecture).

**Bốn điều phải thiết kế**:
- **Phát tin cậy**: ghi dữ liệu và phát event là [[dual-write|dual write]]; dùng [[outbox|outbox]] hoặc [[cdc|CDC]] (bài Transactional outbox & CDC).
- **Trùng lặp**: giao ít nhất một lần, nên mọi bên nghe là [[idempotent-consumer|consumer idempotent]] (bài Messaging fundamentals).
- **Thứ tự**: key của message là id của [[aggregate-root|aggregate]] (`orderId`) để mọi event của một đơn vào cùng [[kafka-partition|partition]]. Giữa các đơn, giữa các topic thì không có thứ tự.
- **Lỗi**: message lỗi mãi vào [[dead-letter-queue|DLQ]] kèm cảnh báo, không chặn cả partition.

**Khi nào không dùng**: người dùng cần câu trả lời ngay (còn hàng không, thanh toán được không) thì gọi đồng bộ. Nghiệp vụ có thứ tự bước chặt chẽ và cần biết đang ở bước nào thì một orchestrator dễ hiểu hơn chuỗi event ([[choreography|choreography]] và orchestration: bài Saga).

## Deep

- **Event khác command**: event (`OrderPlaced`, thì quá khứ) báo việc đã xảy ra, không ai từ chối được; command (`ReserveStock`) yêu cầu một bên cụ thể làm việc và có thể bị từ chối. Trộn command vào topic event làm bên phát lại phải biết bên nhận (bài Event schema evolution).
- **Chuỗi event không ai nhìn thấy**: `OrderPlaced` làm Inventory phát `StockReserved`, làm Payment phát `PaymentCharged`, làm Shipping... Không file nào mô tả luồng; muốn biết "đơn kẹt ở đâu" phải lần qua log của năm service. Cần [[correlation-id|correlation id]] và trace context (`traceparent` của W3C) trong header message, cùng một chỗ ghi trạng thái nghiệp vụ của từng đơn.
- **RPC trá hình**: service gửi event rồi chờ event trả lời để trả response cho người dùng. Có mọi cái giá của bất đồng bộ (timeout khó đặt, khó debug) mà không có lợi ích nào. Cần kết quả ngay thì gọi đồng bộ.
- **Event nội bộ và event công khai**: [[domain-event|domain event]] trong một service có thể đổi tự do; [[integration-event|integration event]] phát ra ngoài là hợp đồng, nên tách hai loại và chuyển đổi ở ranh giới. Phát thẳng entity JPA ra Kafka làm mọi đổi tên cột thành thay đổi phá vỡ.
- **Event cũ đến sau event mới**: retry qua topic khác, hai producer, hoặc đọc lại từ đầu đều có thể đảo thứ tự. Mỗi event mang `aggregateVersion` tăng dần; bản sao cục bộ chỉ cập nhật khi version mới hơn: `UPDATE product_view SET price = :price, version = :v WHERE id = :id AND version < :v`. Bản sao bỏ qua event cũ thay vì ghi đè dữ liệu mới. Dòng chưa tồn tại thì `UPDATE` không làm gì, nên thực tế dùng upsert có điều kiện (PostgreSQL: `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE product_view.version < EXCLUDED.version`); xoá thì giữ tombstone có version, nếu không event cũ đến muộn sẽ "hồi sinh" bản ghi đã xoá.
- **Read your writes**: người dùng đổi địa chỉ rồi tải lại trang thấy địa chỉ cũ, vì trang đọc từ bản sao chưa nhận event. Trả dữ liệu mới trong response của lệnh ghi, đọc từ service gốc ngay sau khi ghi, hoặc hiện trạng thái "đang cập nhật" trên giao diện.
- **Bên nghe mới cần dữ liệu cũ**: Search ra đời sau 2 năm, cần mọi sản phẩm. Kafka giữ 7 ngày thì không đọc lại đủ; chạy [[backfill|backfill]] từ database của bên phát rồi mới nối vào luồng event. Về lâu dài, topic [[log-compaction|compacted]] giữ bản mới nhất theo key cho phép bên nghe mới đọc từ đầu, nhưng chỉ khi topic đã compacted (hoặc đã được nạp lại) từ trước: đổi `cleanup.policy` bây giờ không lấy lại dữ liệu đã bị xoá.
- **[[fan-out|Fan-out]] và tải**: một event `PriceChanged` cho 1 triệu sản phẩm làm mọi bên nghe xử lý 1 triệu message cùng lúc. Theo dõi [[consumer-lag|consumer lag]] cho từng group, đặt [[slo|SLO]] cho độ trễ của bản sao (ví dụ 99% event được xử lý trong 5 giây). Lag tính bằng số offset; muốn đo theo thời gian thì so timestamp của event với lúc xử lý.
- **Retry và thứ tự mâu thuẫn nhau**: retry tại chỗ giữ thứ tự nhưng chặn partition; đẩy sang retry topic thì không chặn nhưng event lỗi đi sau event mới hơn của cùng key (bài Kafka producer & consumer). Chọn theo nghiệp vụ: bản sao giá sản phẩm có version thì chấp nhận đảo, chuyển trạng thái đơn hàng thì không. Tăng số partition cũng đổi ánh xạ key sang partition và phá thứ tự trong lúc chuyển.
- **Xoá dữ liệu cá nhân**: event nằm trong log nhiều ngày hoặc mãi mãi (topic compacted). Giữ PII ngoài event hoặc mã hoá theo khoá của từng người (bài Event schema evolution).
- **Kiểm thử**: unit test không thấy được chuỗi event. Dùng [[contract-test|contract test]] cho schema event giữa producer và consumer, cùng test tích hợp với broker thật (Testcontainers) cho đường đi chính.
- **Exactly-once chỉ trong Kafka**: [[kafka-transaction|Kafka transaction]] nguyên tử cho chuỗi đọc, xử lý, ghi lại Kafka; ghi ra database hay gọi API thì consumer vẫn phải idempotent.
- **Không thay được đối soát**: event mất do lỗi phần mềm, consumer bỏ qua message sau khi hết retry, sửa tay database. Job [[reconciliation|đối soát]] so nguồn sự thật với bản sao (bài Nhất quán dữ liệu giữa các service).
