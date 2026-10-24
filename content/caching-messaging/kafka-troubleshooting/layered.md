## Quick

Bốn sự cố Kafka hay gặp nhất:
- **[[consumer-lag|Consumer lag]]** tăng: consumer không theo kịp producer.
- **[[rebalance-storm|Rebalance storm]]**: nhóm consumer chia lại partition liên tục, gần như không xử lý được gì.
- **[[poison-message|Poison message]]**: một message làm consumer lỗi mãi, chặn cả partition.
- **Số partition sai**: quá ít thì không thêm được consumer, quá nhiều thì tốn tài nguyên; và không giảm được.

Đo lag **theo thời gian** (message cũ nhất chờ bao lâu), không chỉ theo số message. Trước khi thêm consumer, xem lag dồn vào **một partition** hay rải đều: thêm consumer chỉ giúp khi lag rải đều và số consumer còn nhỏ hơn số partition.

## Interview

**Lag tăng, tìm nguyên nhân theo thứ tự**:
- Lag dồn ở vài partition: key lệch ([[hot-partition|hot partition]]) hoặc một consumer chậm. Thêm consumer không giúp.
- Lag đều mọi partition: xử lý chậm (gọi API, database), hoặc producer tăng tải. Xem thời gian xử lý mỗi record và thời gian chờ downstream.
- Lag tăng theo bậc thang kèm log rebalance: nhóm đang rebalance liên tục.

**Rebalance storm**:
- Xử lý một lô lâu hơn `max.poll.interval.ms` (mặc định 5 phút): consumer bị loại, lô bị xử lý lại ở consumer khác, consumer cũ quay lại gây rebalance tiếp.
- GC dừng lâu hoặc CPU bị giới hạn làm mất heartbeat quá `session.timeout.ms`.
- Kubernetes liveness probe giết pod đang xử lý lâu, hoặc deploy liên tục.
- Sửa: giảm `max.poll.records`, đặt timeout cho lời gọi ra ngoài, static membership, cooperative rebalance hoặc giao thức KIP-848.

**Poison message**: lỗi deserialize hoặc dữ liệu sai làm listener lỗi mãi ở cùng offset. Dùng `ErrorHandlingDeserializer`, phân loại lỗi không retry, chuyển sang DLT kèm header lý do, có cảnh báo và công cụ đẩy lại.

**Số partition**:
- Đủ cho throughput mục tiêu (đo throughput một consumer đạt được trên một partition) và cho số consumer song song tối đa.
- Tăng partition làm đổi ánh xạ key → partition, phá thứ tự theo key trong lúc chuyển; không giảm được.
- Quá nhiều partition tốn file handle, bộ nhớ, thời gian failover và thời gian rebalance.

**Phía broker**: theo dõi partition thiếu replica (under-replicated), ISR co lại, đĩa đầy và độ trễ request.

## Deep

- **Đo lag đúng**:
  - `kafka-consumer-groups --bootstrap-server ... --describe --group g` cho lag theo offset từng partition (các lệnh khác trong bài viết tắt `--bootstrap-server`); lag theo thời gian cần công cụ (Burrow, kafka-exporter, hoặc metric `records-lag-max` cộng timestamp của record; Kafka Lag Exporter đã ngừng phát triển từ 2024).
  - Lag thấp hoặc không có số liệu khi nhóm không có consumer nào là giả: metric phía client biến mất cùng consumer, còn CLI vẫn tính theo offset đã commit tới khi chúng hết hạn. Cảnh báo cả khi nhóm không có member.
  - Lag lớn hơn retention: message bị xoá trước khi đọc, consumer gặp offset không còn và nhảy theo `auto.offset.reset` (mặc định `latest`), **mất dữ liệu âm thầm**. Cảnh báo khi tuổi lag tới 50% retention.
- **Hot partition**:
  - Một key chiếm phần lớn lưu lượng (một merchant lớn, key là ngày) dồn vào một partition. `key = null` với sticky partitioner 2.4–3.2 cũng dồn vào partition của broker chậm; KIP-794 sửa ở 3.3.
  - Đổi key thành tổ hợp (`merchantId:orderId`) nếu thứ tự chỉ cần theo đơn, hoặc tách khách lớn sang topic riêng.
  - Xem phân bố bằng kích thước log mỗi partition (`kafka-log-dirs --describe`) hoặc tốc độ ghi từng partition.
- **Xử lý chậm**:
  - Mỗi record gọi HTTP đồng bộ 200ms thì một partition chỉ xử lý tối đa 5 record mỗi giây. Gom lô (batch listener, ghi database theo lô), gọi song song có giới hạn trong một lô, hoặc song song theo key.
  - Consumer chờ database bị khoá hay connection pool cạn: lag là triệu chứng, gốc ở downstream.
  - `pause()`/`resume()` partition khi downstream quá tải thay vì để lô quá hạn `max.poll.interval.ms`.
- **Rebalance chi tiết**:
  - Phía consumer: `consumer poll timeout has expired` là vượt `max.poll.interval.ms`; `session timed out without receiving a heartbeat response` hay `Attempt to heartbeat failed since member id ... is not valid` là mất heartbeat. Phía broker (coordinator): `Member ... has failed, removing it from the group` là vượt `session.timeout.ms`.
  - Static member (giao thức classic) không gửi LeaveGroup khi hết poll timeout; partition của nó giữ nguyên tới khi hết session timeout.
  - `max.poll.records` × thời gian xử lý tệ nhất mỗi record phải nhỏ hơn hẳn `max.poll.interval.ms`.
  - Mỗi lần rebalance, các record đã xử lý mà chưa commit sẽ bị xử lý lại: storm kéo theo trùng lặp.
  - Giao thức KIP-848 (`group.protocol=consumer`, Kafka 4.0+) bỏ đồng bộ toàn nhóm; vẫn phải xử lý nhanh hơn `max.poll.interval.ms`. Session timeout và heartbeat khi đó do broker cấu hình (`group.consumer.session.timeout.ms`); client đặt `session.timeout.ms` không có tác dụng. Mặc định 4.x vẫn là `classic`.
- **Poison message chi tiết**:
  - Lỗi deserialize xảy ra trong `poll()`, trước listener: không có `ErrorHandlingDeserializer` thì consumer quay lại cùng offset mãi.
  - Spring Kafka `DefaultErrorHandler` mặc định thử 10 lần không nghỉ rồi **bỏ qua** record (chỉ log); thêm `DeadLetterPublishingRecoverer` để chuyển sang DLT (`<topic>-dlt` từ 3.3) thay vì mất. Lỗi được coi là fatal (`DeserializationException`, `MessageConversionException`, `ClassCastException`...) gọi recoverer ngay lần đầu, không thử lại.
  - Bỏ qua thủ công khi khẩn cấp: dừng nhóm, `kafka-consumer-groups --group g --reset-offsets --to-offset N+1 --topic t:p --execute`, ghi lại offset bị bỏ để xử lý sau.
- **Lỗi phía producer**:
  - `RecordTooLargeException`: message vượt `max.request.size` của producer (1MB) hoặc `message.max.bytes` của broker (`max.message.bytes` của topic); tăng các giới hạn đó, hoặc tốt hơn là dùng claim check. Consumer không bị kẹt vì batch đầu tiên luôn được trả về dù vượt `max.partition.fetch.bytes`.
  - `NotEnoughReplicasException`: ISR nhỏ hơn `min.insync.replicas`; xem broker nào chết hoặc tụt.
  - `TimeoutException` có hai dạng: `send()` chặn vì buffer đầy rồi ném lỗi sau `max.block.ms` (60 giây), message chưa gửi; hoặc record hết hạn sau `delivery.timeout.ms` (2 phút) vì broker chậm hay mạng lỗi, message có thể đã ghi hoặc chưa.
- **Phía broker**:
  - `UnderReplicatedPartitions` > 0 kéo dài: follower không theo kịp (đĩa chậm, mạng, broker quá tải). `OfflinePartitionsCount` > 0: partition không có leader, không đọc ghi được.
  - Đĩa đầy làm broker dừng; retention theo dung lượng (`retention.bytes`) cộng cảnh báo ở 70–80%.
  - Leader dồn vào vài broker sau khi khởi động lại: chạy lại bầu leader ưa thích (`kafka-leader-election --election-type PREFERRED --all-topic-partitions`) hoặc để `auto.leader.rebalance.enable` (mặc định bật) làm.
  - Thêm broker không tự chuyển partition sang: phải reassign (`kafka-reassign-partitions`, Cruise Control), có giới hạn băng thông để không làm nghẽn cụm.
- **Chọn số partition**:
  - Ước lượng: `max(throughput mục tiêu / throughput một partition phía producer, throughput mục tiêu / throughput một consumer)`, nhân dư cho tăng trưởng 1–2 năm.
  - Kafka với KRaft chịu được số partition mỗi cụm lớn hơn nhiều so với thời ZooKeeper, nhưng mỗi partition vẫn tốn tài nguyên trên broker và client.
  - Topic cần thứ tự theo key: chọn số partition một lần cho đủ lâu; cần tăng thì tạo topic mới và chuyển có kế hoạch.
