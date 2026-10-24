## Quick

**Producer** gom message thành lô theo partition, nén, rồi gửi; bật sẵn **[[idempotent-producer|idempotent producer]]** để retry không tạo bản trùng hay đảo thứ tự trong một partition. **[[kafka-transaction|Transaction]]** cho phép ghi nhiều partition và commit offset của consumer như một khối, để luồng đọc từ Kafka, xử lý, ghi lại Kafka đạt exactly-once. **Consumer** gọi `poll()` trong vòng lặp, xử lý, rồi **commit [[kafka-offset|offset]]** (vị trí message **kế tiếp** cần đọc). Thời điểm commit so với lúc xử lý quyết định mất hay trùng message. [[consumer-rebalance|Rebalance]] chia lại partition khi consumer vào ra nhóm.

## Interview

**Producer**:
- `send()` bất đồng bộ: message vào buffer, luồng nền gửi theo lô. Lô được gửi khi đủ `batch.size` hoặc chờ đủ `linger.ms` (mặc định 5ms từ Kafka 4.0, trước đó 0).
- Mặc định `acks=all` từ client 3.0; idempotence mặc định có hiệu lực thật từ 3.0.1/3.1.1/3.2.0 (3.0.0 và 3.1.0 có lỗi khiến nó không bật). Producer có ID và số thứ tự cho mỗi partition; broker bỏ bản gửi lại trùng, và giữ thứ tự với tối đa 5 request đang bay.
- Retry tự động tới khi hết `delivery.timeout.ms` (mặc định 2 phút); sau đó callback nhận lỗi. Không kiểm tra kết quả `send()` là mất message âm thầm.

**Consumer**:
- Offset commit là offset **kế tiếp** cần đọc: xử lý xong offset 41 thì commit 42.
- Auto commit (mặc định 5 giây) commit offset của lô trước **trong lúc gọi `poll()`**: xử lý xong trong vòng lặp thì là [[delivery-semantics|at-least-once]]; đẩy record sang thread pool rồi poll tiếp thì có thể mất message.
- Xử lý một lô quá `max.poll.interval.ms` (mặc định 5 phút) thì consumer bị coi là chết và bị loại khỏi nhóm (với static membership, partition chờ hết session timeout mới bị chia lại).
- Số consumer có ích trong một [[consumer-group|consumer group]] tối đa bằng số partition.

**Rebalance**:
- Kiểu cũ (eager) thu hồi mọi partition rồi chia lại: cả nhóm dừng.
- `CooperativeStickyAssignor` chỉ chuyển partition cần chuyển.
- Giao thức mới [[kip-848|KIP-848]] (`group.protocol=consumer`, chính thức từ Kafka 4.0) để broker điều phối và tăng dần, không còn dừng cả nhóm.
- [[static-membership|Static membership]] (`group.instance.id`) cho phép pod khởi động lại không gây rebalance nếu quay lại trong session timeout.

**Exactly-once**: trong phạm vi Kafka thì dùng transaction cộng `isolation.level=read_committed`. Ghi ra database thì transaction Kafka không bao được: lưu offset trong cùng transaction database, hoặc [[idempotent-consumer|consumer idempotent]].

## Deep

- **Lô và hiệu năng producer**:
  - `batch.size` mặc định 16KB mỗi partition; tăng lên 64–256KB cùng `linger.ms` 10–50ms và `compression.type=lz4` hoặc `zstd` cho throughput cao. Nén theo lô, nên lô lớn nén tốt hơn.
  - `buffer.memory` (32MB) đầy thì `send()` **chặn** tối đa `max.block.ms` (60 giây) rồi ném lỗi; gọi `send()` trong luồng xử lý request HTTP thì luồng đó bị giữ khi broker chậm.
  - Key `null`: từ 2.4 dùng sticky partitioner, gửi cả lô vào một partition rồi đổi, thay vì xoay vòng từng message. Từ 3.3 (KIP-794), partitioner có sẵn đổi partition sau mỗi `batch.size` byte và ưu tiên broker đang nhanh; 4.0 đã gỡ `DefaultPartitioner` và `UniformStickyPartitioner`.
- **Idempotence bị tắt mà không biết**: từ client 3.0.1/3.1.1/3.2.0, nếu không bật tường minh mà đặt cấu hình xung đột (`acks=1`, `retries=0`, `max.in.flight.requests.per.connection > 5`), producer **tự tắt** idempotence; bật tường minh thì ném `ConfigException`. Retry khi đó có thể tạo bản trùng, và đảo thứ tự nếu nhiều request đang bay. Đặt `enable.idempotence=true` tường minh để cấu hình xung đột báo lỗi ngay.
- **Phạm vi của idempotence**: chỉ trong một phiên producer và với retry nội bộ của client. Ứng dụng tự gửi lại sau khi nhận lỗi, hoặc producer khởi động lại, thì broker coi là message mới.
- **Transaction**:
  - `transactional.id` cố định cho mỗi producer logic; `initTransactions()` tăng epoch và **chặn** (fence) phiên cũ còn sống cùng id: producer zombie bị từ chối. Phiên cũ nhận `ProducerFencedException` thì phải đóng producer, không retry.
  - Consumer trong luồng đọc, xử lý, ghi phải đặt `enable.auto.commit=false`, vì offset được commit qua transaction.
  - Luồng đọc, xử lý, ghi: `beginTransaction()`, `send()` kết quả, `sendOffsetsToTransaction(offsets, consumer.groupMetadata())`, `commitTransaction()`. Offset đầu vào và message đầu ra cùng thành công hoặc cùng bị huỷ.
  - Consumer `isolation.level=read_committed` chỉ đọc tới **last stable offset**: một transaction mở lâu chặn mọi consumer read_committed của partition đó, nhìn như lag tăng.
  - Mặc định consumer là `read_uncommitted`: thấy cả message của transaction bị huỷ.
  - Transaction tăng độ trễ (commit theo lô, mặc định Kafka Streams commit mỗi 100ms với exactly-once) và không bao gồm gọi HTTP hay ghi database.
- **Commit offset chi tiết**:
  - Spring Kafka tắt auto commit của client (trừ khi bạn đặt `enable.auto.commit` tường minh) và tự commit: `AckMode.BATCH` (mặc định) commit sau khi listener xử lý xong mọi record của lần poll; `RECORD` commit sau từng record; `MANUAL` để code gọi `Acknowledgment.acknowledge()` và gom commit sau lô, `MANUAL_IMMEDIATE` commit ngay khi gọi.
  - Commit đồng bộ (`commitSync`) chặn và retry; bất đồng bộ (`commitAsync`) nhanh nhưng không retry, nên thường `commitAsync` trong vòng lặp và `commitSync` khi đóng hoặc khi bị thu hồi partition.
  - Nhóm mới, offset đã hết hạn (`offsets.retention.minutes`, mặc định 7 ngày, tính từ lúc nhóm không còn member), hoặc offset đã commit bị retention xoá khỏi log đều dùng `auto.offset.reset`: mặc định `latest`, tức **bỏ qua** mọi message có sẵn. Service mới đọc topic cũ thường cần `earliest`.
- **Rebalance an toàn**:
  - `ConsumerRebalanceListener.onPartitionsRevoked`: commit phần đã xử lý trước khi mất partition, nếu không consumer mới xử lý lại.
  - Với giao thức cũ, `session.timeout.ms` (mặc định 45 giây từ 3.0) phát hiện consumer chết qua heartbeat của luồng nền; `max.poll.interval.ms` phát hiện vòng xử lý bị treo.
  - Deploy rolling 30 pod với eager rebalance là ít nhất 30 lần cả nhóm dừng (thường gấp đôi: rời nhóm rồi vào lại); cooperative hoặc KIP-848 cùng static membership giảm gần hết.
  - Với `group.protocol=consumer` (KIP-848), session timeout và heartbeat do broker quyết định (`group.consumer.session.timeout.ms`, `group.consumer.heartbeat.interval.ms`); client không được đặt `session.timeout.ms`, `heartbeat.interval.ms`, và assignor chọn ở broker. Client mặc định vẫn là `group.protocol=classic`.
  - Static membership có giá: trong lúc pod vắng mặt, partition của nó không ai đọc nên lag tăng; pod chết hẳn thì phải chờ hết session timeout mới chia lại. `group.instance.id` phải ổn định và duy nhất: pod của Deployment có tên ngẫu nhiên nên thường dùng StatefulSet; hai instance trùng id (rolling update với `maxSurge`) thì instance cũ bị fence (`FencedInstanceIdException`).
- **Song song hơn số partition**:
  - `KafkaConsumer` không thread-safe; mỗi luồng một consumer, hoặc một consumer poll rồi chia record theo key cho nhiều worker và tự quản lý commit (chỉ commit tới offset mà mọi record trước đó đã xong).
  - Thư viện như Confluent Parallel Consumer làm việc này theo key; share groups (Kafka 4.2) chia việc theo từng message nhưng không giữ thứ tự.
- **Retry ở consumer và thứ tự**:
  - Retry tại chỗ (Spring `DefaultErrorHandler` với backoff) giữ thứ tự nhưng chặn cả partition trong lúc chờ.
  - Retry qua topic khác (`@RetryableTopic`) không chặn partition nhưng message lỗi đi sau message mới hơn của cùng key: chỉ dùng khi thứ tự không quan trọng.
  - Lỗi vĩnh viễn (deserialize, dữ liệu sai) chuyển thẳng sang DLT.
- **Exactly-once với database**:
  - Lưu offset trong bảng của database, cùng transaction với thay đổi dữ liệu; khi khởi động, `seek()` tới offset đã lưu thay vì dùng offset của Kafka.
  - Hoặc bảng `processed_message` theo khoá nghiệp vụ (bài Messaging cơ bản).
