## Quick

Mô hình nhất quán (consistency model) nói một hệ nhiều bản sao **hứa gì với người đọc**. Mạnh nhất là [[linearizability|linearizability]]: hệ thống trông như chỉ có một bản dữ liệu, đọc luôn thấy lần ghi đã xác nhận gần nhất. Yếu nhất là [[eventual-consistency|eventual consistency]]: các bản sao sẽ khớp nhau, nhưng không nói khi nào. [[cap-theorem|CAP]] nói: **khi có [[network-partition|network partition]], phải chọn giữa linearizable và việc mọi node còn sống đều trả lời**. [[pacelc|PACELC]] bổ sung: khi không có partition, vẫn phải chọn giữa latency thấp và nhất quán mạnh.

## Interview

**Các mức nhất quán, từ mạnh tới yếu**:
- *Linearizable*: như một bản duy nhất. Cần cho khoá phân tán, bầu leader, kiểm tra unique, số dư.
- *Sequential*: mọi người thấy các thao tác theo cùng một thứ tự, nhưng thứ tự đó không cần khớp thời gian thực, nên có thể đọc thấy dữ liệu cũ (mức của lệnh đọc ZooKeeper).
- *[[causal-consistency|Causal]]*: nếu sự kiện B xảy ra vì A (trả lời một bình luận), ai thấy B cũng đã thấy A. Các sự kiện không liên quan có thể thấy theo thứ tự khác nhau.
- *Đảm bảo theo phiên*: [[read-your-writes|read-your-writes]] (thấy ngay cái mình vừa ghi), [[monotonic-reads|monotonic reads]] (không thấy dữ liệu lùi về cũ hơn lần đọc trước).
- *Eventual*: không ghi thêm thì cuối cùng mọi bản sao bằng nhau.

**CAP nói gì thật sự**: không phải "chọn 2 trong 3". Partition sẽ xảy ra, nên không có hệ phân tán "CA". Khi có partition, một bên của partition phải chọn: từ chối request để giữ linearizable (CP: etcd; ZooKeeper cho lệnh ghi, còn đọc linearizable phải gọi `sync()` trước; PostgreSQL khi mọi lần đọc và ghi đều trên primary), hoặc tiếp tục trả lời và chấp nhận lệch (AP: Cassandra, Riak, họ hệ thống theo bài báo Dynamo dùng sloppy quorum). Dịch vụ DynamoDB thì khác bài báo Dynamo: ghi qua leader của từng partition, chỉ eventual read là có thể trả dữ liệu cũ.

**PACELC thực dụng hơn**: partition hiếm, còn latency thì luôn có. Replication đồng bộ (chờ replica xác nhận) cho nhất quán mạnh nhưng mỗi lần ghi chậm thêm một vòng mạng; replication bất đồng bộ nhanh nhưng đọc từ replica có thể cũ, và failover có thể mất lần ghi chưa kịp sang.

**Ví dụ hay gặp**: ghi vào PostgreSQL primary rồi đọc từ replica bất đồng bộ, người dùng không thấy cập nhật vừa lưu. Sửa bằng đọc từ primary trong vài giây sau khi ghi, hoặc đọc từ replica đã áp tới LSN của lần ghi đó (bài Replication & HA).

## Deep

- **Linearizable khác serializable**: serializable là mức **isolation** của transaction (kết quả như chạy tuần tự theo một thứ tự nào đó, có thể không theo thời gian thực). Linearizable là **consistency** của một object theo thời gian thực. Có cả hai là strict serializability, như Spanner (nhờ đồng hồ TrueTime); CockroachDB thì chỉ hứa serializable cộng linearizable cho từng key.
- **[[quorum|Quorum]] `R + W > N` chưa đủ để linearizable**: với N = 3, ghi chờ W = 2, đọc hỏi R = 2 thì tập đọc và tập ghi giao nhau. Nhưng đọc trong lúc ghi đang dở, [[sloppy-quorum|sloppy quorum]] (ghi tạm vào node khác khi node chính chết), và giải quyết xung đột bằng last-write-wins theo đồng hồ đều có thể trả giá trị cũ hoặc làm mất lần ghi. Lần ghi báo lỗi vì không đủ W xác nhận cũng không được rollback trên các node đã nhận, nên sau đó vẫn có thể bị đọc thấy.
- **[[tunable-consistency|Tunable consistency]]**: Cassandra cho chọn mức theo từng câu (`ONE`, `QUORUM`, `LOCAL_QUORUM` trong một data center, `ALL`), và lightweight transaction (`INSERT ... IF NOT EXISTS`) chạy Paxos với mức `SERIAL` cho thao tác linearizable như kiểm tra unique, đổi lại chậm hơn nhiều; DynamoDB có strongly consistent read (đọc từ leader, tốn gấp đôi read capacity) bên cạnh eventual read mặc định; MongoDB có `writeConcern: majority` cùng `readConcern: majority` hoặc `linearizable`.
- **Kafka**: [[kafka-acks|`acks=all`]] cùng [[min-insync-replicas|`min.insync.replicas=2`]] (với replication factor 3) nghĩa là lần ghi đã xác nhận nằm ở ít nhất hai broker. Thiếu replica đồng bộ thì producer nhận lỗi: chọn C hơn A cho việc ghi. Bẫy: `acks=all` là mặc định từ Kafka 3.0 nhưng `min.insync.replicas` mặc định là 1, nên ISR co còn mỗi leader thì lần ghi vẫn được xác nhận; giữ `unclean.leader.election.enable=false` (bài Kafka architecture).
- **Redis replication là bất đồng bộ**: failover sang replica có thể mất các lần ghi gần nhất. `WAIT` chờ replica xác nhận nhưng không biến Redis thành hệ linearizable.
- **Causal là mức mạnh nhất còn giữ được khả dụng khi có partition**, với điều kiện client luôn nói chuyện với cùng một replica (sticky available). Đây là lý do nó hấp dẫn cho đảm bảo theo phiên. MongoDB có causal consistency session, nhưng chỉ đảm bảo khi dùng `majority` cho cả read concern lẫn write concern, và khi đó phía thiểu số không còn phục vụ.
- **Hội tụ của eventual consistency**: bản sao lệch phải được hoà giải. [[last-write-wins|Last-write-wins]] đơn giản nhưng âm thầm bỏ lần ghi khi đồng hồ lệch; [[crdt|CRDT]] (counter, set có thể gộp) hợp nhất được mà không mất dữ liệu cho một số kiểu dữ liệu; còn lại phải để nghiệp vụ tự giải quyết (bài Multi-region & active-active).
- **Theo dõi độ lệch**: với replica bất đồng bộ, đo [[replica-lag|lag]] (`pg_stat_replication.replay_lag` của PostgreSQL; với MySQL, `Seconds_Behind_Source` không đáng tin, nên dùng bảng heartbeat như bài Replication & HA) và cảnh báo; quyết định đọc từ replica nên dựa trên mức lag mà nghiệp vụ chấp nhận được.
- **Chọn theo dữ liệu, không theo cả hệ thống**: số dư, tồn kho khi giữ hàng, unique username cần nhất quán mạnh; số lượt xem, gợi ý sản phẩm, feed chấp nhận eventual. Một hệ thống thường có cả hai.
