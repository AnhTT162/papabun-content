## Quick

Key-value store phân tán kiểu Dynamo chia key lên các node bằng [[consistent-hashing|consistent hashing]], ghi mỗi key lên N bản sao, đọc ghi theo [[quorum|quorum]] (R, W), gắn phiên bản để phát hiện xung đột, và tự chữa khi node chết bằng [[hinted-handoff|hinted handoff]] và [[anti-entropy|anti-entropy]]. **Quyết định gốc là có leader cho mỗi partition hay không: không leader (Dynamo, Cassandra) thì luôn ghi được nhưng phải giải xung đột; có leader (DynamoDB, TiKV) thì không xung đột nhưng partition mất leader sẽ ngừng ghi vài giây.** Mọi lựa chọn khác (R, W, cách giải xung đột, cách xoá) đi theo quyết định đó và theo nghiệp vụ.

## Interview

Tôi hỏi trước: giá trị lớn cỡ nào, bao nhiêu thao tác mỗi giây, có cần đọc thấy ngay lần ghi vừa xong, mất một AZ có phải vẫn ghi được, có cần quét theo khoảng.

**Chia và nhân bản**: vòng hash có [[virtual-node|virtual node]] (chi tiết ở bài Consistent hashing). Mỗi key có [[preference-list|preference list]] gồm N = 3 node, mỗi node ở một AZ. Mô phỏng 9 node trên 3 AZ: đặt bản sao không biết AZ thì 14,4% key mất quorum khi một AZ chết; biết AZ thì 0%.

**Đường ghi**: client gửi tới một [[coordinator-node|coordinator]], coordinator gửi cho cả 3 bản sao và trả lời khi đủ W xác nhận. Mỗi node ghi commit log rồi [[memtable]], đầy thì xả ra [[sstable|SSTable]] ([[lsm-tree|LSM-tree]], bài Storage engine).

**Đường đọc**: hỏi R bản sao. `R + W > N` thì tập đọc giao tập ghi. Mô phỏng N = 3 có 1% replica chậm thêm 50 ms: R = W = 1 đọc ngay sau khi ghi trả về thì 45% thấy giá trị cũ, sau 5 ms còn 1,3%, phải tới khoảng 100 ms mới hết; R = W = 2 thì 0%.

**Xung đột**: [[last-write-wins|LWW]] theo đồng hồ âm thầm mất ghi: mô phỏng 3 node lệch nhau tới 35 ms, hai lần ghi cách nhau 0–100 ms, mất 8% số lần ghi. [[vector-clock|Version vector]] phát hiện hai phiên bản đồng thời và giữ cả hai làm [[sibling-version|sibling]] cho ứng dụng gộp. Gộp giỏ hàng bằng phép hợp làm món đã xoá sống lại, nên cần [[crdt|CRDT]] như OR-Set.

**Node chết**: [[gossip-protocol|gossip]] lan trạng thái, [[phi-accrual|phi accrual]] quyết định khi nào coi node đã chết. Chết tạm thì coordinator giữ hint và chuyển lại khi node về; quá cửa sổ hint thì phải repair bằng cây Merkle. Xoá là ghi [[tombstone|tombstone]], và tombstone chỉ được dọn sau khi mọi bản sao đã nhận nó.

**Bẫy**: LWW cho dữ liệu không được mất ghi, không repair kịp trước khi tombstone bị dọn, tự xây khi Cassandra hay DynamoDB đã đủ.

## Deep

- **Yêu cầu quyết định thiết kế**:
  - Cần luôn ghi được kể cả khi mạng chia đôi (giỏ hàng, session, đếm lượt xem): không leader, chấp nhận xung đột và có cách gộp.
  - Cần không mất ghi và đọc thấy ngay (số dư, tên đăng nhập duy nhất, khoá): leader theo partition với [[raft|Raft]] hay Paxos, hoặc thao tác có điều kiện chạy qua consensus (Cassandra lightweight transaction).
  - Cần quét theo khoảng key: chia theo khoảng thay vì theo hash (TiKV, HBase, Bigtable), đổi lại phải tách và gộp vùng khi một vùng nóng.
- **API**: `get(key)` trả giá trị kèm `context` (phiên bản); `put(key, context, value)` gửi lại context đã đọc. Ghi không kèm context (blind write) thì hệ không biết lần ghi này đã thấy phiên bản nào, và mọi phiên bản cũ đều thành xung đột.
- **Preference list theo AZ**: lấy N node khác máy vật lý tiếp theo trên vòng, bỏ qua node cùng AZ với bản đã chọn (Cassandra `NetworkTopologyStrategy` cùng snitch biết rack). Mô phỏng 9 node, 3 node mỗi AZ, 16 virtual node mỗi node, 100.000 key: không biết AZ thì 73,1% key không trải đủ 3 AZ và 14,4% key mất quorum khi một AZ chết; biết AZ thì cả hai là 0%. Hệ quả: số node mỗi AZ nên bằng nhau, vì AZ ít node thì mỗi node của nó gánh phần lớn hơn.
- **Đường ghi trên một node** (Cassandra): ghi commit log, ghi memtable, trả lời; memtable đầy thì xả thành SSTable không bao giờ sửa, compaction gộp dần ở nền. Mặc định `commitlog_sync: periodic` fsync 10 giây một lần, nên máy sập (mất điện, kernel panic; process chết thì dữ liệu vẫn trong page cache) có thể mất lần ghi đã báo thành công trong 10 giây đó; dữ liệu vẫn còn nhờ bản sao ở AZ khác, miễn là W ≥ 2. Muốn mỗi lần ghi đều fsync thì dùng `batch` hoặc `group`, đổi lại latency ghi tăng.
- **Đường đọc** (Cassandra): coordinator xin dữ liệu đầy đủ từ một replica nhanh nhất và chỉ xin digest (hash của kết quả) từ các replica còn lại. Digest lệch thì đọc đầy đủ từ cả nhóm, lấy bản mới nhất, ghi đè lên replica cũ trước khi trả lời ([[read-repair|read repair]] chặn). Cassandra 4.0 đã bỏ `read_repair_chance` (read repair nền theo xác suất); bản sao lệch giờ dựa vào repair định kỳ.
- **[[speculative-retry|Speculative retry]]**: replica chậm vì GC hay đĩa là chuyện thường. Phía server, Cassandra mặc định `speculative_retry = '99p'`: replica chưa trả lời sau p99 latency của bảng thì coordinator hỏi thêm một replica khác. Phía client, driver Java DataStax có speculative execution riêng (gửi cùng câu tới coordinator khác), và driver chỉ dùng nó cùng retry cho câu được đánh dấu idempotent (`setIdempotent(true)`).
- **Lab xác suất đọc cũ** (kiểu PBS của Bailis): N = 3, mỗi replica áp bản ghi sau thời gian theo phân phối mũ trung bình 1 ms, 1% replica chậm thêm 50 ms; đọc gửi sau khi lần ghi trả về Δ ms, tới replica sau thêm trung bình 0,5 ms, replica đọc chọn ngẫu nhiên, bỏ qua thời gian ack về client. Con số cụ thể nhạy với các giả định này; hình dạng thì không:

  | R, W | Δ = 0 | 1 ms | 5 ms | 20 ms | 100 ms |
  |---|---|---|---|---|---|
  | 1, 1 | 44,7% | 17,2% | 1,3% | 1,0% | 0% |
  | 1, 2 | 22,6% | 9,0% | 1,1% | 1,0% | 0% |
  | 2, 1 | 15,0% | 2,2% | 0,02% | 0,01% | 0% |
  | 2, 2 | 0% | 0% | 0% | 0% | 0% |

  Cửa sổ đọc cũ bị chặn bởi **đuôi** của replica chậm, không bởi latency trung bình. R = 1 W = 1 hợp với dữ liệu đọc lại sau vài giây (đếm lượt xem), không hợp với "lưu xong rồi tải lại trang".
- **Quorum chưa phải linearizable**: lần ghi báo lỗi vì thiếu W vẫn nằm trên replica đã nhận và có thể bị đọc thấy sau đó; [[sloppy-quorum|sloppy quorum]] làm `R + W > N` mất tác dụng (bài Consistency, CAP & PACELC).
- **LWW và đồng hồ**:
  - Lab: 3 coordinator lệch {0, +5, -30} ms, mỗi lần ghi đi qua một coordinator ngẫu nhiên. Ghi cách nhau 0–20 ms: mất 34% số lần ghi; 0–100 ms: 8%; 0–1.000 ms: 0,75%. Lần ghi bị mất vẫn báo thành công.
  - Cassandra áp LWW cho **từng ô** (cột của một dòng), không cho cả dòng. Mô hình giỏ hàng thành mỗi món một dòng `(cart_id, sku)` thì hai người thêm hai món khác nhau không đè nhau; chỉ cùng món mới tranh nhau.
  - Driver Java DataStax 4.x mặc định tự gán timestamp phía client (`AtomicTimestampGenerator`), tức theo đồng hồ máy app; muốn coordinator gán thì cấu hình `advanced.timestamp-generator.class = ServerSideTimestampGenerator`. Cách nào cũng phụ thuộc đồng hồ máy (bài Đồng hồ & ID).
- **Version vector và sibling**:
  - Mỗi phiên bản mang bộ đếm theo node đã ghi. Lab: giỏ `{A:1} [sách]`; người 1 thêm bút qua A thành `{A:2} [sách, bút]`; người 2 cùng lúc xoá sách qua B thành `{A:1, B:1} []`. Không vector nào lớn hơn hoặc bằng vector kia, nên hai phiên bản là sibling.
  - Lần đọc sau nhận cả hai sibling, ứng dụng gộp rồi ghi lại với context chứa cả hai vector, và các sibling được dọn.
  - Gộp bằng phép hợp ra `[bút, sách]`: món đã xoá sống lại. Bài báo Dynamo ghi nhận đúng hiện tượng này ở giỏ hàng của Amazon.
  - Vector dài theo số node từng ghi vào key nên phải cắt bớt hay dùng dotted version vector (bài Đồng hồ & ID).
- **CRDT thay cho gộp tay** (bài Multi-region & active-active): OR-Set gắn tag riêng cho mỗi lần thêm; lần xoá chỉ xoá các tag nó đã thấy. Lab: gộp hai sibling ở trên ra `[bút]` đúng ý; thêm lại sách (tag mới) đồng thời với lần xoá cũ thì sách vẫn còn, vì lần xoá không thấy tag mới. Bộ đếm dùng PN-counter (mỗi node một cặp tăng/giảm). Counter của Cassandra không idempotent: client retry sau timeout có thể cộng hai lần.
- **Xoá và tombstone**:
  - Xoá ghi một tombstone (bản ghi đánh dấu đã xoá) có timestamp, vì nếu xoá vật lý thì replica đang chết quay về sẽ đem giá trị cũ "sửa" lại cho các replica khác.
  - Cassandra chỉ dọn tombstone sau `gc_grace_seconds` (mặc định 864.000, tức 10 ngày). Phải chạy repair xong trên mọi replica trong khoảng đó; nếu không, dữ liệu đã xoá sống lại.
  - TTL cũng sinh tombstone khi hết hạn. Đọc qua nhiều tombstone thì chậm; Cassandra cảnh báo ở 1.000 tombstone mỗi lần đọc và huỷ truy vấn ở 100.000 (`tombstone_warn_threshold`, `tombstone_failure_threshold`). Mẫu xấu kinh điển: dùng bảng như hàng đợi, xoá từng dòng sau khi xử lý.
- **Phát hiện node chết**:
  - Gossip: mỗi giây mỗi node trao đổi trạng thái với một node ngẫu nhiên (Cassandra dùng ba message SYN, ACK, ACK2, tức kiểu đẩy và kéo). Lab, số vòng để mọi node biết một tin: 1.000 node chỉ đẩy 18 vòng, đẩy và kéo 9 vòng; 10.000 node 24 và 12 vòng.
  - Phi accrual: không trả lời "chết hay sống" theo một timeout cố định mà tính mức nghi ngờ φ theo khoảng cách heartbeat đã thấy. Cassandra coi khoảng cách theo phân phối mũ: φ = thời gian im lặng / khoảng cách trung bình × log10(e). Ngưỡng mặc định `phi_convict_threshold` 8 với heartbeat trung bình 1 giây nghĩa là im lặng khoảng 18 giây mới bị coi là chết; ngưỡng 12 là 28 giây. Mạng cloud hay giật thì tăng lên 10–12 để không báo nhầm.
  - "Chết" theo failure detector chỉ là tạm. Thêm, bỏ hay thay node là thao tác do người vận hành ra lệnh (Dynamo cũng làm vậy), để một node chập chờn không làm cả cụm chuyển dữ liệu qua lại.
- **Chữa sau sự cố** (cơ chế ở bài Consistent hashing, đây là số liệu Cassandra):
  - Hinted handoff: Cassandra giữ hint ở coordinator tối đa `max_hint_window` (mặc định 3 giờ). Node chết lâu hơn thì không còn hint cho phần sau, phải repair.
  - Anti-entropy: mỗi replica dựng [[merkle-tree|cây Merkle]] theo khoảng token, so từ gốc xuống và chỉ chuyển các khoảng lệch (`nodetool repair`). Incremental repair chỉ so dữ liệu chưa repair. Lên lịch repair cho cả cụm xong trong mỗi chu kỳ ngắn hơn `gc_grace_seconds`.
  - Node chết hẳn: thay bằng node mới nhận cùng token (`-Dcassandra.replace_address_first_boot`), dữ liệu được stream từ các replica còn lại; giới hạn băng thông stream để không bóp nghẹt lưu lượng thật.
- **Leader theo partition, phương án kia**: DynamoDB (bài báo năm 2022) cho mỗi partition một nhóm 3 bản sao ở 3 AZ chạy Multi-Paxos; leader nhận mọi lần ghi, ghi xong khi 2 trên 3 bản đã lưu log. Đọc mạnh đi qua leader. Không có sibling, có thao tác có điều kiện (`ConditionExpression`) và transaction. Đổi lại: leader chết thì partition đó ngừng ghi tới khi bầu xong, leader của partition nóng là nút cổ chai, và mạng chia đôi thì phía thiểu số không ghi được.
- **Nhiều region**: thường quorum trong region (`LOCAL_QUORUM`) và sao chép bất đồng bộ sang region khác, giải xung đột liên region bằng LWW (DynamoDB global tables mặc định, Cassandra). Từ 6/2025 DynamoDB global tables có thêm chế độ nhất quán mạnh nhiều region (MRSC), đổi lại ghi chậm hơn. Dữ liệu không chịu được LWW thì có một region chủ cho mỗi key (bài Multi-region & active-active).
- **Ước lượng dung lượng**: dữ liệu × [[replication-factor|replication factor]] × hệ số compaction. Size-tiered compaction có lúc cần trống gần bằng dung lượng đang dùng, leveled khoảng 10%. Value lớn (vài trăm KB trở lên) không nên nằm trong KV: DynamoDB giới hạn item 400 KB; với Cassandra, partition lớn làm compaction và repair nặng. Để value ở object storage, KV giữ con trỏ.
- **Key nóng**: chia đều theo số key không có nghĩa là đều theo lưu lượng. Tách key, cache ở client, hay nhân bản key đọc nhiều (bài Consistent hashing). DynamoDB giới hạn mỗi partition 3.000 đơn vị đọc và 1.000 đơn vị ghi mỗi giây, nên key nóng bị throttle dù bảng còn dư.
- **Tự xây hay dùng có sẵn**: phỏng vấn hỏi "thiết kế" để xem bạn hiểu các cơ chế trên. Ngoài đời, câu trả lời của architect thường là chọn hệ có sẵn theo yêu cầu (Cassandra hay ScyllaDB cho ghi nhiều và luôn ghi được; DynamoDB khi muốn managed; etcd chỉ cho metadata nhỏ cần nhất quán mạnh; Redis khi chấp nhận mất dữ liệu gần nhất) và chỉ tự xây khi có yêu cầu mà không hệ nào đáp ứng.
