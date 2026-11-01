## Quick

Message queue phân tán kiểu Kafka là một **log chỉ ghi nối** chia thành nhiều [[kafka-partition|partition]], mỗi partition nhân bản lên vài broker, và consumer tự giữ vị trí đọc ([[kafka-offset|offset]]). **Quyết định gốc là lưu trạng thái theo từng message (queue cổ điển: ack từng message, xoá khi xong) hay chỉ lưu một offset cho mỗi partition (log: rẻ, đọc lại được, nhưng một message chậm chặn cả partition).** Thứ tự chỉ có trong một partition, nên chọn key và số partition là quyết định khó sửa nhất.

## Interview

Tôi hỏi trước: message để giao việc (mỗi việc một người làm) hay để phát sự kiện (nhiều hệ cùng đọc, đọc lại được); cần thứ tự theo phạm vi nào; giữ bao lâu; throughput và kích thước message; mất message có chấp nhận được không.

**Lưu trữ**: mỗi partition là chuỗi [[log-segment|segment]] chỉ ghi nối, kèm [[sparse-index|index thưa]] từ offset sang vị trí byte. Ghi là nối cuối file, đọc là tìm trong index rồi quét tuần tự. Retention xoá nguyên segment. Segment cũ có thể đẩy sang object storage ([[tiered-storage|tiered storage]]).

**Nhân bản**: một leader cho mỗi partition, follower chủ động kéo dữ liệu. Offset follower xin lần sau chính là xác nhận đã có dữ liệu trước đó. Message đã commit khi mọi replica trong [[isr|ISR]] có nó; [[high-watermark|high watermark]] là ranh giới consumer được đọc. Khi leader đổi, follower cắt log theo [[leader-epoch|leader epoch]] chứ không theo high watermark, nếu không sẽ mất message đã báo thành công.

**Consumer**: kéo (pull) theo lô, long poll. Offset của [[consumer-group|consumer group]] lưu ngay trong một topic compacted của chính hệ.

**Thứ tự và scale**: partition = hash(key) mod N. Đổi N làm key đổi partition: thử 1 triệu key với partitioner của Kafka, 12 lên 16 partition thì 75% key đổi chỗ. Nên chọn N đủ cho vài năm ngay từ đầu.

**Chi phí**: trên cloud, sao chép giữa các AZ thường đắt hơn máy. Với 3 AZ, mỗi GB ghi vào tốn ít nhất 2 GB đi chéo AZ cho replication; consumer đọc follower cùng AZ để không nhân thêm.

**Bẫy**: dùng log cho việc chạy lâu (một việc treo chặn partition, rebalance liên tục), tăng partition giữa chừng với dữ liệu cần thứ tự, giữ mọi thứ trên đĩa local.

## Deep

- **Queue hay log, chọn từ yêu cầu**:
  - Queue cổ điển (SQS, RabbitMQ classic): mỗi message có trạng thái riêng (sẵn sàng, đang xử lý tới hạn [[visibility-timeout|visibility timeout]], đã xoá). Giao cho nhiều worker, ack từng cái, retry từng cái, DLQ có sẵn. Giá: mỗi message ít nhất vài lần ghi trạng thái, không đọc lại được sau khi xoá, thứ tự yếu.
  - Log: broker chỉ ghi nối; consumer chỉ lưu một số cho mỗi partition và commit định kỳ. Rẻ tới mức nhiều group độc lập đọc cùng dữ liệu và đọc lại từ đầu. Giá: song song tối đa bằng số partition, một message lỗi hay chậm chặn mọi message sau nó trong partition ([[head-of-line-blocking|head-of-line blocking]]).
  - Lai: [[share-group|share group]] của Kafka (KIP-932, production-ready ở 4.2) giữ trên broker một cửa sổ message đang xử lý của mỗi partition, cho nhiều consumer đọc chung một partition và ack từng message. Hợp với việc độc lập không cần thứ tự; mỗi message bị khoá có thời hạn (mặc định 30 giây) rồi giao lại cho người khác.
  - Chi tiết ack, visibility timeout, DLQ ở bài Messaging fundamentals; đây chỉ là lựa chọn thiết kế.
- **Định dạng lưu**:
  - Producer gửi theo lô; broker lưu nguyên lô (đã nén) và cấp offset tăng dần. Lô mang producer id và sequence để broker bỏ bản trùng khi producer retry ([[idempotent-producer|idempotent producer]], bài Kafka producer & consumer).
  - Index thưa: cứ khoảng `index.interval.bytes` (mặc định 4.096 byte) dữ liệu thì ghi một mục 8 byte (offset tương đối, vị trí). Segment 1 GiB có khoảng 262.144 mục, 2 MiB, nằm gọn trong RAM qua mmap. Tìm offset là tìm nhị phân trong index rồi quét khoảng 4 KB cộng một lô (mục index đặt ở ranh giới lô). Có thêm time index để tìm theo thời gian (`offsetsForTimes`).
  - Vì dữ liệu không bao giờ bị sửa tại chỗ, đọc phần mới thường lấy từ page cache và gửi bằng zero-copy (bài Kafka kiến trúc).
- **Vì sao follower kéo chứ không leader đẩy**: follower tự điều tốc theo sức của nó, gom lô lớn, và request kéo tiếp theo (`fetch offset = X`) vừa là đơn xin dữ liệu vừa là xác nhận đã có mọi thứ trước X. Leader không cần theo dõi ack riêng. Follower không gửi fetch trong `replica.lag.time.max.ms` (mặc định 30 giây) hoặc không bắt kịp trong khoảng đó thì bị loại khỏi ISR.
- **ISR khác quorum đa số**: [[raft|Raft]] cần 2f + 1 bản sao để chịu f lỗi, vì mỗi lần ghi chỉ cần đa số. ISR chờ **mọi** replica đang đồng bộ, nên f + 1 bản sao đã chịu được f lỗi mà không mất dữ liệu đã commit, với điều kiện ISR không co lại; ISR được co tới `min.insync.replicas`, nên bảo đảm thật là chịu `min.insync.replicas − 1` lỗi (RF 3, min 2: một lỗi). Đổi lại, một replica chậm làm chậm cả lần ghi cho tới khi bị đá khỏi ISR (tối đa 30 giây kể trên), và việc ai được làm leader phải do một bộ điều khiển có consensus quyết định (controller [[kraft|KRaft]]). Redpanda chọn Raft cho từng partition; Kafka dùng Raft chỉ cho metadata.
- **Leader epoch, ca mất dữ liệu cụ thể** (KIP-101, sửa ở Kafka 0.11):
  - Leader A và follower B, `acks=all`. B kéo message m2; A thấy cả ISR có m2 nên tăng high watermark và báo thành công cho producer. B chỉ biết high watermark mới ở lần fetch sau.
  - B khởi động lại trước lần fetch đó, cắt log về high watermark nó biết, mất m2. Ngay sau đó A chết, B lên làm leader: m2 đã báo thành công mà biến mất.
  - Cách sửa: mỗi lần đổi leader tăng một số epoch, log ghi offset bắt đầu của từng epoch. Follower khởi động lại hỏi leader "epoch của tôi kết thúc ở offset nào" rồi chỉ cắt phần thật sự lệch. Bài học thiết kế: ranh giới commit được truyền chậm thì không được dùng làm căn cứ để xoá dữ liệu.
- **Metadata và bầu leader**: controller giữ danh sách partition, leader, ISR, epoch và quyết định leader mới khi broker chết (KRaft, bài Kafka kiến trúc). Đặt 3 replica trên 3 [[availability-zone|AZ]] (`broker.rack`); với `acks=all` và `min.insync.replicas=2`, mất một AZ vẫn ghi được. Bật `unclean.leader.election.enable` là chấp nhận mất dữ liệu để đổi lấy sẵn sàng.
- **Consumer kéo theo lô**: kéo cho consumer tự điều tốc (không bị đè như push), gom lô lớn khi tụt lại, đọc lại khi cần. Nhược điểm của kéo là gọi rỗng khi không có dữ liệu, nên dùng long poll: broker giữ request tới khi có đủ `fetch.min.bytes` (mặc định 1) hay hết `fetch.max.wait.ms` (mặc định 500 ms). Kiểm trên kafka-clients 4.4.0.
- **Offset lưu ở đâu**: trong topic compacted `__consumer_offsets` (mặc định 50 partition). Mỗi group được gán cho partition `abs(hash(group.id)) % 50`, và broker làm leader của partition đó là group coordinator. Không cần database ngoài, và nhân bản, failover của offset dùng chung cơ chế với dữ liệu. Group không còn thành viên quá `offsets.retention.minutes` (mặc định 7 ngày) thì offset bị xoá; consumer quay lại sẽ theo `auto.offset.reset`.
- **Thứ tự và số partition**:
  - Thứ tự chỉ đúng trong một partition, và chỉ khi producer giữ thứ tự khi retry (idempotence, bật mặc định từ Kafka 3.0).
  - Lab với `Utils.murmur2` của kafka-clients 4.4.0, 1 triệu key `account-i`: 12 → 16 partition đổi chỗ 75,0% key; 12 → 24: 50,0%; 12 → 13: 92,3%; 48 → 64: 74,9%. Key giữ chỗ chỉ khi `h mod 12 = h mod 16`, tức `h mod 48 < 12`: 12/48 = 25%.
  - Sau khi tăng, message cũ của một key còn ở partition cũ, message mới vào partition mới, hai consumer khác nhau có thể xử lý lệch thứ tự. Cách an toàn: chọn đủ partition từ đầu, hoặc tạo topic mới và chuyển có kiểm soát (dừng producer theo key, chờ consumer đọc hết topic cũ).
  - 1 triệu key trên 48 partition: ít nhất 20.536, nhiều nhất 21.176 key mỗi partition. Hash đều theo **số key**; lệch thật đến từ key nóng.
- **Message trễ và retry có hẹn** ([[delay-queue|delay queue]]): Kafka không có sẵn. Mẹo: mỗi topic retry một độ trễ cố định (1 phút, 10 phút, 1 giờ). Trong một topic như vậy, message vào trước đến hạn trước, nên consumer chỉ cần nhìn message đầu: chưa tới hạn thì `seek()` về offset của nó (`poll()` đã đọc qua rồi), `pause()` partition, `resume()` khi tới hạn, không commit vượt qua nó, và không được ngủ trong vòng `poll()` (quá `max.poll.interval.ms` là bị đá khỏi group). Độ trễ tuỳ ý cho từng message cần bộ hẹn giờ riêng (timing wheel, bài Thiết kế job scheduler). SQS cho trễ tối đa 15 phút; RabbitMQ xem bài RabbitMQ. Retry theo bậc cho gửi thông báo ở bài Thiết kế hệ thống thông báo.
- **Giữ dữ liệu**:
  - Theo thời gian hay dung lượng, xoá cả segment. Topic dạng trạng thái thì compact (giữ bản mới nhất mỗi key).
  - Tiered storage (Kafka 3.9+, không cho topic compacted): broker giữ phần gần, segment cũ lên object storage, chỉ một bản (object storage tự dư thừa). Lợi lớn nhất là vận hành: broker chỉ có 6 TB local thì thay broker chép lại 6 TB, không phải 40 TB.
  - Consumer chậm hơn retention thì dữ liệu tại offset của nó đã bị xoá và nó nhảy theo `auto.offset.reset`: `earliest` mất phần đã xoá, `latest` bỏ thêm cả phần còn trên đĩa; cả hai đều im lặng. Cảnh báo theo lag tính bằng thời gian, so với retention (bài Kafka troubleshooting).
- **Chi phí chéo AZ** (AWS tính 0,01 USD/GB mỗi chiều, tức 0,02 USD/GB), 3 AZ, RF 3, mỗi GB producer ghi:
  - Producer tới leader: 2/3 GB đi chéo AZ (leader nằm AZ khác 2/3 số lần).
  - Replication: 2 GB (hai follower ở hai AZ khác).
  - Mỗi consumer group đọc leader: thêm 2/3 GB. Đọc follower cùng AZ ([[follower-fetching|fetch from follower]], KIP-392, `client.rack`): gần 0.
  - Ví dụ 200 MB/s trung bình (518.400 GB/tháng), 4 group: đọc leader 5,33 GB chéo AZ mỗi GB, khoảng 55.300 USD/tháng; đọc follower 2,67 GB, khoảng 27.600 USD; riêng replication 20.700 USD là phần không bỏ được nếu còn replica trên đĩa broker.
  - Hướng mới: ghi thẳng lên object storage, không replica trên broker (các hệ tương thích Kafka như WarpStream; Kafka có KIP-1150 Diskless Topics đã được chấp thuận nhưng chưa có bản phát hành). Bỏ được phần chéo AZ, đổi lại latency đầu cuối cỡ vài trăm ms vì phải chờ ghi object.
- **Tách tính toán và lưu trữ** (Pulsar): broker không giữ dữ liệu, chỉ phục vụ; dữ liệu nằm ở BookKeeper chia thành các đoạn (ledger), mỗi đoạn ghi lên một nhóm bookie với tham số ensemble E, write quorum Qw, ack quorum Qa (ví dụ 3, 3, 2). Thêm bookie là nhận ghi mới ngay, không phải chuyển partition cũ; chuyển topic giữa broker không phải chép dữ liệu. Giá: thêm một tầng để vận hành và hiểu.
- **Ước lượng**:
  - Đĩa = ingress × thời gian giữ × [[replication-factor|RF]] (đã nén). 200 MB/s giữ 7 ngày: 121 TB, nhân 3 là 363 TB.
  - Mạng của cụm lúc đỉnh 600 MB/s: ghi đĩa 1,8 GB/s kể cả replica, ra consumer 600 × số group, ra replication 1,2 GB/s.
  - Số broker theo trần đo được (load test), rồi thêm để mất một AZ vẫn đủ (bài Capacity planning). Số partition theo throughput một consumer xử lý được, không theo producer.
- **Nhiều tenant**: quota theo client (byte/giây cho produce và fetch) để một đội không chiếm hết; giới hạn số partition mỗi đội; đặt tên topic theo miền và chủ sở hữu; schema registry để đổi schema an toàn (bài Event schema evolution).
- **Nhiều region**: sao chép bất đồng bộ giữa cụm (MirrorMaker 2, cluster linking), offset hai cụm khác nhau nên cần dịch offset khi chuyển consumer; message có thể lặp hay mất phần cuối khi failover (bài Multi-region & active-active).
- **Tự xây hay dùng có sẵn**: phỏng vấn hỏi để xem bạn hiểu log, nhân bản, offset. Ngoài đời: Kafka hay bản managed cho luồng sự kiện; SQS hay RabbitMQ cho giao việc; Redis Streams cho tải nhỏ chấp nhận mất dữ liệu khi failover.
