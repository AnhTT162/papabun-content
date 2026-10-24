## Quick

"NoSQL" là nhiều họ database khác nhau, mỗi họ tối ưu cho một kiểu đọc: **[[key-value-store|key-value]]** (lấy theo khoá), **[[document-database|document]]** (lấy cả một aggregate), **[[wide-column-store|wide-column]]** (lấy một dải dòng trong một partition), **[[graph-database|graph]]** (đi theo quan hệ nhiều bước). Quy tắc chung: **thiết kế theo [[access-pattern|access pattern]] trước, dữ liệu sau**, vì query nào không được tính trước thì thường không chạy được hoặc rất đắt.

## Interview

**Key-value** (Redis, Memcached, và lõi của DynamoDB): `get`/`put` theo khoá, cực nhanh, scale ngang dễ. Không tìm được theo giá trị. Hợp với session, cache, bộ đếm, cấu hình.

**Document** (MongoDB, Couchbase; [[jsonb]] của PostgreSQL ở mức nhỏ): mỗi bản ghi là một document JSON lồng nhau, thường chứa trọn một aggregate (đơn hàng cùng các dòng hàng). Có index trên field và query linh hoạt. Câu hỏi thiết kế chính: **nhúng (embed)** dữ liệu con vào document hay **tham chiếu (reference)** sang collection khác.

**Wide-column** (Cassandra, ScyllaDB, HBase, Bigtable): dữ liệu chia theo [[partition-key|partition key]], trong partition sắp theo [[clustering-key|clustering key]]. Query phải chỉ rõ partition key; mỗi access pattern thường có một bảng riêng, dữ liệu được ghi lặp ở nhiều bảng. Ghi rất rẻ ([[lsm-tree|LSM-tree]]), [[tunable-consistency|độ nhất quán chỉnh được]] theo từng query (`ONE`, `QUORUM`, `ALL`).

**DynamoDB** (key-value và document, managed): khoá gồm partition key và sort key tuỳ chọn. Muốn query theo thuộc tính khác thì cần [[gsi|GSI]] (bản sao bất đồng bộ, khoá khác) hoặc [[lsi|LSI]] (cùng partition key, sort key khác, phải tạo cùng bảng). Đọc mặc định là eventually consistent.

**Graph** (Neo4j, Amazon Neptune): node và cạnh là dữ liệu chính; query "bạn của bạn của bạn" hay tìm đường đi nhanh hơn nhiều so với join đệ quy.

**Bẫy chung**: [[hot-partition|hot partition]] (một khoá nhận quá nhiều lưu lượng), access pattern mới không có khoá phù hợp, và mất ràng buộc: tính đúng của dữ liệu chuyển hết về ứng dụng.

**Khi nào vẫn chọn database quan hệ**: dữ liệu có nhiều quan hệ, cần transaction nhiều bản ghi, cần query tuỳ ý cho báo cáo, hoặc access pattern chưa rõ. Nhiều hệ thống dùng nhiều loại cùng lúc ([[polyglot-persistence|polyglot persistence]]): PostgreSQL làm nguồn gốc, Redis cho cache, search engine cho tìm kiếm.

## Deep

- **Embed hay reference (MongoDB)**: embed khi dữ liệu con luôn được đọc cùng cha và số lượng có giới hạn (địa chỉ của khách, dòng hàng của đơn). Reference khi dữ liệu con tăng không giới hạn (bình luận của bài viết nổi tiếng) hoặc được dùng chung: document tối đa 16MB, và mảng tăng mãi làm mỗi lần ghi đắt dần.
- **MongoDB transaction và độ bền**: transaction nhiều document có từ 4.0 (replica set) và 4.2 (sharded cluster), nhưng chậm hơn thao tác trên một document; thiết kế để thao tác quan trọng nằm gọn trong một document. Từ 5.0, write concern mặc định là `majority`, trừ replica set có arbiter như PSA (2 node dữ liệu + 1 arbiter), khi đó mặc định là `w: 1`; nên đặt write concern tường minh. Scale ghi bằng [[sharding]] theo shard key: khoá tăng đơn điệu (thời gian, ObjectId) dồn mọi lần ghi vào một shard, nên dùng hashed shard key hoặc khoá ghép. Dùng `$jsonSchema` validation để collection không thành bãi rác schema.
- **Cassandra: thiết kế theo query**: bảng `messages_by_conversation` có `PRIMARY KEY ((conversation_id, bucket), message_id)`: `(conversation_id, bucket)` là partition key, `message_id` (kiểu `timeuuid`, vừa chứa thời gian vừa unique) là clustering key, nên không cần cặp `sent_at, message_id`. Giữ partition dưới khoảng 100MB bằng cách thêm "bucket" (tháng, ngày) vào partition key. `ALLOW FILTERING` là dấu hiệu query đang quét nhiều partition. Secondary index truyền thống hạn chế; Cassandra 5 có Storage-Attached Index (SAI) tốt hơn nhưng vẫn không thay được bảng thiết kế cho query.
- **Không sửa được clustering key**: đổi giá trị của cột trong khoá chính là xoá dòng cũ rồi ghi dòng mới, và mỗi lần xoá để lại tombstone (xem bài Storage engine). Danh sách "sắp theo thời gian cập nhật" sửa liên tục là một bẫy kinh điển.
- **Lightweight transaction** (`INSERT ... IF NOT EXISTS`) của Cassandra dùng Paxos, chậm hơn nhiều lần ghi thường; chỉ dùng cho chỗ thật sự cần, như giữ chỗ username.
- **Nhất quán chỉnh được**: với replication factor 3, ghi `QUORUM` (2 node) và đọc `QUORUM` (2 node) luôn chồng nhau ít nhất một node, nên đọc thấy bản ghi mới nhất (R + W > N). `ONE`/`ONE` nhanh hơn nhưng có thể đọc dữ liệu cũ. Ba điều kiện kèm theo: chỉ đúng với lần ghi `QUORUM` thành công (ghi thất bại có thể đã nằm trên một replica, lúc thấy lúc không); xung đột được giải bằng last-write-wins theo timestamp, nên lệch đồng hồ có thể làm "mất" bản mới; nhiều data center thì `QUORUM` tính trên mọi DC, thường dùng `LOCAL_QUORUM`.
- **DynamoDB chi tiết**: item tối đa 400KB. `Query` theo khoá rẻ, `Scan` đọc cả bảng và tính phí theo dung lượng đọc. Mỗi trang kết quả tối đa 1MB, phải phân trang bằng `LastEvaluatedKey`. `FilterExpression` không giảm chi phí: phí và giới hạn 1MB tính trên dữ liệu đọc trước khi lọc. GSI không hỗ trợ strongly consistent read. Transaction (`TransactWriteItems`) tối đa 100 item và tốn gấp đôi capacity. Một partition vật lý chịu tối đa khoảng 3.000 RCU và 1.000 WCU; adaptive capacity giúp phần nào nhưng không cứu được một khoá quá nóng: thêm hậu tố ngẫu nhiên vào khoá (write sharding).
- **[[single-table-design|Single-table design]]** (DynamoDB): đặt nhiều loại thực thể vào một bảng với khoá dạng `PK = CUSTOMER#42`, `SK = ORDER#2026-10-24#9001`, để một `Query` lấy được khách cùng các đơn của họ mà không cần join. Tiết kiệm request nhưng khó hiểu và khó đổi khi access pattern mới xuất hiện.
- **Redis làm database chính**: dữ liệu nằm trong RAM nên dung lượng bị giới hạn bởi RAM. Độ bền phụ thuộc cấu hình: RDB (snapshot định kỳ) có thể mất vài phút dữ liệu, AOF với `appendfsync everysec` mất tới khoảng 1 giây. Replication bất đồng bộ nên failover có thể mất ghi.
- **Các loại chuyên dụng khác**: search engine (Elasticsearch, OpenSearch) cho tìm kiếm theo chữ; time-series (TimescaleDB, InfluxDB) cho metric theo thời gian; columnar (ClickHouse) cho phân tích. Chúng thường là bản sao được đồng bộ từ nguồn gốc qua [[cdc|CDC]] hoặc [[outbox]], không phải nơi ghi chính.
- **PostgreSQL làm được khá nhiều**: `jsonb` cho document, partition và Citus (sharding) cho dữ liệu lớn, extension cho time-series (TimescaleDB) và vector (pgvector). Một database ít thành phần hơn thường thắng nhiều database "đúng loại" khi đội nhỏ.
- **Chi phí chuyển đổi**: đổi database chính sau khi đã chạy là dự án nhiều tháng (ghi kép, backfill, đối soát, chuyển đọc dần). Tính chi phí đó vào quyết định ban đầu.
