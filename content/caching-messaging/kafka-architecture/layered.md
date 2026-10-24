## Quick

Kafka lưu message trong **log chỉ ghi nối**, chia thành các **[[kafka-partition|partition]]**; mỗi message có một **[[kafka-offset|offset]]** tăng dần trong partition, và được giữ theo retention chứ không bị xoá khi đã đọc. Mỗi partition có một **leader** và các follower; tập replica theo kịp là **[[isr|ISR]]**. Độ bền quyết định bởi **[[kafka-acks|`acks`]]** và **[[min-insync-replicas|`min.insync.replicas`]]**. Thứ tự chỉ được đảm bảo **trong một partition**, nên message cùng key đi chung partition. **[[consumer-group|Consumer group]]** chia partition cho các consumer, mỗi partition một consumer.

## Interview

**Cấu trúc**:
- Topic gồm nhiều partition, mỗi partition là một log nằm trên một broker leader, sao chép sang `replication.factor - 1` follower.
- Producer chọn partition theo `hash(key)`. Không có key thì dùng sticky partitioner (từ 2.4, cải tiến ở 3.3): gom lô vào một partition rồi đổi sang partition khác.
- Consumer đọc theo offset và tự lưu offset đã xử lý vào topic nội bộ `__consumer_offsets`.

**Replication và ISR**: follower kéo dữ liệu từ leader. Follower tụt quá `replica.lag.time.max.ms` (mặc định 30 giây) bị loại khỏi ISR. **[[high-watermark|High watermark]]** là offset mà mọi replica trong ISR đã có; consumer chỉ đọc được tới đó.

**`acks`**:
- `0`: không chờ gì.
- `1`: chờ leader ghi; leader chết trước khi follower kịp kéo về là mất.
- `all` (mặc định từ Kafka 3.0, cùng lúc với `enable.idempotence=true`): chờ mọi replica trong ISR. Đi cùng `min.insync.replicas=2` thì mỗi message xác nhận nằm ở ít nhất hai broker.

**Leader election**: controller chọn leader mới trong ISR khi broker chết. [[unclean-leader-election|Unclean election]] (mặc định tắt) cho replica ngoài ISR làm leader: còn chạy được nhưng mất dữ liệu.

**[[kraft|KRaft]]**: metadata của cluster do các controller tự quản lý bằng giao thức đồng thuận, thay ZooKeeper. Kafka 4.0 bỏ hẳn ZooKeeper.

**Consumer group**: trong một group là [[competing-consumers|competing consumers]], mỗi partition được giao cho đúng một consumer; consumer nhiều hơn partition thì có consumer ngồi không. Nhiều group cùng đọc một topic, mỗi group nhận đủ mọi message: đó là [[pub-sub|pub/sub]].

**Vì sao nhanh**: ghi tuần tự vào cuối file, dựa vào page cache của hệ điều hành, gửi theo lô có nén, và đọc bằng [[zero-copy|zero-copy]] từ page cache ra socket.

**Retention**: xoá theo thời gian hoặc dung lượng (`retention.ms` mặc định 7 ngày), hoặc [[log-compaction|log compaction]] giữ bản mới nhất của mỗi key.

## Deep

- **Log trên đĩa**: mỗi partition là một thư mục gồm các segment (mặc định 1GB, `segment.bytes`), mỗi segment có file index theo offset và theo thời gian. Retention xoá nguyên segment cũ, không xoá từng message, và xét theo timestamp lớn nhất trong segment; topic ghi chậm giữ segment mở tới `segment.ms` (mặc định 7 ngày), nên dữ liệu có thể nằm lâu hơn `retention.ms` tới cỡ `segment.ms`. Segment active không bao giờ bị compact, nên muốn compaction chạy sớm thì giảm `segment.ms` hoặc đặt `max.compaction.lag.ms`.
- **Độ bền và fsync**: Kafka mặc định không fsync mỗi message mà để hệ điều hành ghi xuống; độ bền đến từ replication. Ba replica ở ba AZ (`broker.rack` cộng rack awareness) chịu được mất cả một AZ. Mất điện đồng thời cả ba máy thì có thể mất phần chưa xuống đĩa. KIP-966 (Eligible Leader Replicas, có từ 4.0, bật mặc định cho cluster mới từ 4.1) giúp bầu leader an toàn hơn trong ca chỉ còn một replica sống sót.
- **Tính toán chịu lỗi** với `replication.factor=3`, `min.insync.replicas=2`, `acks=all`:
  - Mất 1 broker: vẫn đọc ghi bình thường.
  - Mất 2 broker: ISR còn 1 nhỏ hơn 2, producer nhận `NotEnoughReplicasException`; consumer vẫn đọc được dữ liệu đã commit.
  - `min.insync.replicas=3` thì chỉ cần mất 1 broker là không ghi được: thường quá chặt.
- **High watermark và log end offset**: leader có thể đã nhận message (log end offset tăng) mà follower chưa kéo về. High watermark bằng log end offset nhỏ nhất trong ISR, tức offset của message kế tiếp; consumer đọc được các offset nhỏ hơn nó (với `isolation.level=read_committed` thì chỉ tới LSO, thấp hơn nữa). Nếu leader chết, phần chưa vào high watermark có thể bị cắt khi replica khác lên làm leader; từ KIP-101, follower cắt log theo leader epoch thay vì theo high watermark để tránh mất hay lệch dữ liệu. Producer với `acks=all` chỉ nhận xác nhận sau khi high watermark vượt qua message của nó.
- **Unclean election**: bật `unclean.leader.election.enable=true` cho phép một replica tụt hậu làm leader khi không còn replica ISR nào, đổi tính sẵn sàng lấy mất dữ liệu (các message nó chưa có biến mất, và offset có thể bị dùng lại). Chỉ hợp với dữ liệu như log hay metric.
- **Controller và KRaft**:
  - Controller giữ metadata (topic, partition, leader, ISR) và quyết định bầu leader.
  - KRaft lưu metadata trong một topic nội bộ được sao chép bằng giao thức kiểu Raft giữa các controller (thường 3 hoặc 5), thay vì ZooKeeper. Failover controller nhanh hơn và cluster chịu được nhiều partition hơn.
  - Kafka 3.3 đưa KRaft vào production; 4.0 bỏ ZooKeeper và không còn công cụ chuyển đổi. Lộ trình cho cluster cũ: nâng lên 3.9 (bản cuối còn ZooKeeper), chạy migration ZooKeeper sang KRaft, rồi mới lên 4.x.
- **Chọn partition**:
  - Hash mặc định là murmur2 của key, chia lấy dư cho số partition. Key phân bố lệch (một khách hàng chiếm 30% message) làm một partition nóng.
  - Partitioner tuỳ chỉnh, hoặc thêm hậu tố vào key nóng, giúp chia tải nhưng mất thứ tự chung của key đó.
- **Số partition**:
  - Là giới hạn trên của số consumer xử lý song song trong một group.
  - Nhiều partition hơn: throughput cao hơn, nhưng thêm file mở, thêm việc cho controller khi failover, và rebalance lâu hơn.
  - Ước lượng: lấy throughput mục tiêu chia cho throughput một consumer xử lý được (thường thấp hơn nhiều so với throughput của producer), cộng dư cho tăng trưởng.
- **Consumer group chi tiết**:
  - Group coordinator (một broker) quản lý thành viên. Consumer gửi heartbeat; im lặng quá `session.timeout.ms` (mặc định 45 giây từ 3.0) hoặc không gọi `poll` trong `max.poll.interval.ms` (mặc định 5 phút) thì bị coi là chết và partition bị chia lại (rebalance).
  - `session.timeout.ms` ở trên là của giao thức classic. Giao thức consumer mới (KIP-848, GA ở 4.0) bật ở client bằng `group.protocol=consumer`; nó chuyển việc phân chia sang broker và rebalance từng phần, đỡ cảnh cả group dừng lại, và timeout phiên khi đó do broker cấu hình (`group.consumer.session.timeout.ms`). Bài Kafka producer & consumer chuyên sâu đi sâu.
- **Offset và thời điểm commit**: commit sau khi xử lý là [[delivery-semantics|at-least-once]]; commit trước là at-most-once. `auto.offset.reset` (`latest` mặc định, hoặc `earliest`) chỉ áp khi group chưa có offset đã commit hoặc offset đó đã bị retention xoá; Kafka 4.0 thêm `by_duration:<ISO8601>`.
- **Đọc từ follower**: từ 2.4 (KIP-392), consumer đặt `client.rack` có thể đọc từ follower cùng rack hoặc AZ, giảm chi phí truyền dữ liệu giữa các AZ.
- **Log compaction**:
  - `cleanup.policy=compact` giữ ít nhất bản mới nhất cho mỗi key; message có giá trị `null` (tombstone) đánh dấu xoá key, và tombstone được giữ thêm `delete.retention.ms` (mặc định 1 ngày) rồi mới bị dọn.
  - Dùng cho dữ liệu dạng trạng thái: cấu hình, bảng tra cứu, changelog của Kafka Streams, `__consumer_offsets`.
  - Compaction không chạy tức thì: có thể có nhiều bản của cùng key tới khi cleaner chạy.
- **Vì sao nhanh, chi tiết**:
  - Ghi tuần tự cuối file nhanh trên cả HDD lẫn SSD.
  - Dữ liệu mới thường được consumer đọc ngay từ page cache, không chạm đĩa; vì vậy heap JVM của broker không cần lớn, phần lớn RAM để cho page cache.
  - `sendfile` chuyển dữ liệu từ page cache ra socket không qua user space (zero-copy). TLS phá vỡ tối ưu này vì dữ liệu phải được mã hoá trong JVM.
  - Lô và nén (`compression.type` của producer: lz4, zstd) giảm số request và băng thông; broker lưu nguyên lô đã nén.
- **Message lớn**: giới hạn mặc định khoảng 1MB (`message.max.bytes` của broker, `max.request.size` của producer). Payload lớn hơn nên đặt ở object storage và gửi đường dẫn.
- **Tiered storage** (KIP-405, production-ready từ 3.9): đẩy segment cũ sang object storage, broker chỉ giữ phần gần đây trên đĩa cục bộ, giúp giữ dữ liệu lâu mà không cần thêm broker. Không áp dụng cho topic compacted, và Kafka không kèm sẵn plugin cho S3 hay GCS: phải dùng plugin bên ngoài.
- **Kafka không phải queue cổ điển**: với consumer group cổ điển, Kafka không xoá message khi đã đọc, không ack từng message, không có DLQ có sẵn (tự làm bằng topic riêng), và một message lỗi chặn cả partition nếu consumer cứ retry. Đổi lại: đọc lại được từ bất kỳ offset nào, nhiều group độc lập, throughput rất cao. Từ Kafka 4.2, share group (KIP-932) đã production-ready: nhiều consumer đọc chung một partition, ack từng message và đếm số lần giao lại, tức kiểu đọc như queue ngay trong Kafka.
