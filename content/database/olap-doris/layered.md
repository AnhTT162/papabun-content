## Quick

[[oltp|OLTP]] (PostgreSQL, MySQL) đọc ghi vài dòng mỗi lần; [[olap|OLAP]] quét và gộp hàng trăm triệu dòng nhưng chỉ vài cột. Apache Doris là OLAP engine [[columnar-storage|lưu theo cột]], chạy truy vấn [[mpp|MPP]] trên nhiều node, nói giao thức MySQL. **Doris không thay database nghiệp vụ**: dữ liệu được nạp theo lô (mỗi lô là một phiên bản, trễ vài giây tới một phút), bảng được thiết kế theo câu hỏi báo cáo, và [[doris-table-model|mô hình bảng]], cột partition, cột bucket chốt lúc tạo bảng, không đổi được; đổi khoá sắp xếp là schema change nặng, viết lại toàn bộ dữ liệu.

## Interview

**Vì sao không chạy báo cáo trên PostgreSQL**: lưu theo dòng nên `SUM(amount) GROUP BY day` trên 2 tỉ dòng phải đọc mọi cột của mọi dòng, và chiếm tài nguyên của primary. Lưu theo cột chỉ đọc vài cột cần, nén mạnh vì giá trị cùng kiểu nằm cạnh nhau, và chạy [[vectorized-execution|vector hoá]] theo khối hàng nghìn giá trị.

**Kiến trúc**: FE (Java) giữ metadata, lập kế hoạch truy vấn; BE (C++) lưu dữ liệu và thực thi. Ứng dụng kết nối FE bằng driver MySQL. Từ 3.0 có chế độ tách compute và storage, dữ liệu nằm trên S3.

**Thiết kế bảng** gồm ba quyết định:
- Mô hình: Duplicate giữ mọi dòng (log, event); Aggregate gộp sẵn theo khoá (`SUM`, `MAX`, `REPLACE`, `HLL_UNION`); Unique giữ bản mới nhất mỗi khoá, dùng cho dữ liệu đồng bộ từ OLTP.
- Phân vùng theo thời gian để bỏ qua ngày không cần ([[partition-pruning|pruning]]) và xoá dữ liệu cũ theo partition; mỗi partition chia bucket theo hash thành các [[tablet|tablet]].
- Khoá sắp xếp: cột lọc nhiều nhất đứng đầu, vì [[prefix-index|prefix index]] chỉ dùng phần đầu của khoá.

**Nạp dữ liệu**: Stream Load qua HTTP, Routine Load kéo từ Kafka (exactly-once theo offset), Flink [[cdc|CDC]] từ database. Mỗi lần nạp tạo một phiên bản dữ liệu, gộp dần bằng [[compaction|compaction]]. Bẫy số một: ứng dụng `INSERT` từng dòng, phiên bản tăng nhanh hơn compaction, rồi Doris từ chối ghi với lỗi -235. Gom lô, hoặc bật [[doris-group-commit|group commit]].

**Tăng tốc**: [[materialized-view|materialized view]] đồng bộ cho một bảng, materialized view bất đồng bộ cho join, cả hai được optimizer tự dùng khi truy vấn khớp.

**Khi nào không dùng**: dữ liệu vài chục GB thì PostgreSQL với index và materialized view đã đủ; cần transaction nhiều bảng, update từng dòng liên tục, hay phục vụ hàng chục nghìn truy vấn phức tạp mỗi giây với latency mili giây thì Doris là lựa chọn sai.

## Deep

- **Lưu theo cột chạy thế nào**: mỗi tablet gồm các rowset (một rowset mỗi lần nạp), mỗi rowset gồm segment file; trong segment, mỗi cột lưu riêng thành các page có mã hoá (dictionary, RLE...) và nén. Bản 4.1.5 nén mặc định bằng ZSTD (`default_compression_type`); bản cũ hơn mặc định LZ4F. Truy vấn chỉ mở cột được nhắc tới, nên `SELECT *` trên bảng 200 cột là cách nhanh nhất để mất lợi thế lưu theo cột.
- **Phiên bản và lỗi -235**: mỗi lần nạp thành công tạo một phiên bản trên mỗi tablet nó chạm tới. Cumulative compaction gộp các phiên bản nhỏ, base compaction gộp vào bản nền. Khi số phiên bản của một tablet vượt `max_tablet_version_num` (2.000 ở BE 4.1.5; bản cũ có thể thấp hơn), lần nạp sau bị từ chối với `TOO_MANY_VERSION` (-235). Nguyên nhân gần như luôn là nạp quá thường xuyên với lô quá nhỏ, hoặc mỗi lô rải vào quá nhiều tablet. Nâng ngưỡng chỉ hoãn lỗi. Cách đúng: gom lô theo vài giây, dùng group commit (gộp các lần ghi nhỏ, mặc định commit sau 10 giây hoặc 64 MB), hoặc ghi qua Kafka rồi Routine Load.
- **Group commit đổi lấy gì**: `async_mode` trả lời ngay sau khi ghi WAL, nhưng WAL chỉ có một bản trên một BE, mất đĩa thì mất dữ liệu chưa commit; group commit cũng không giữ thứ tự commit, nên bảng Unique cần sequence column. Lần ghi có label thì Doris không gom (chạy như ghi thường), nên dùng group commit là bỏ label: retry sau timeout có thể nạp hai lần, bảng Aggregate `SUM` cộng hai lần. Nó cũng không gom `INSERT ... VALUES` có biểu thức, và từ chối ghi trong lúc schema change nặng.
- **Routine Load**: mỗi task là một transaction, offset Kafka được commit cùng dữ liệu nên không mất, không trùng tính từ Kafka. Mặc định một lô kết thúc sau 60 giây, 20 triệu dòng hoặc 1 GB, tuỳ cái nào tới trước; muốn dữ liệu mới trong vài giây thì hạ `max_batch_interval`, đổi lại nhiều phiên bản hơn. `max_error_number` mặc định 0: một message JSON hỏng làm job chuyển sang PAUSED, nên phải có cảnh báo theo trạng thái job. Exactly-once chỉ tính từ Kafka: producer gửi trùng message thì bảng Aggregate vẫn cộng hai lần.
- **Stream Load và label**: mỗi lần nạp gắn một label; gửi lại cùng label của một lần đã thành công thì bị từ chối thay vì nạp hai lần, còn label của lần thất bại thì dùng lại được, nên retry với cùng label là an toàn. Label của Stream Load chỉ được nhớ 12 giờ (`streaming_label_keep_max_second`), Broker Load 3 ngày (`label_keep_max_second`). Gửi tới FE cổng HTTP (mặc định 8030), FE chuyển hướng 307 sang một BE.
- **Duplicate**: giữ nguyên mọi dòng, hợp với log, clickstream. Khoá chỉ là thứ tự sắp xếp, không phải ràng buộc duy nhất. Chỉ bảng Duplicate được dùng random bucketing (rải đều khi không có cột hash tốt), đổi lại không cắt bucket theo khoá khi truy vấn.
- **Aggregate**: dòng cùng khoá được gộp lúc nạp, lúc compaction và lúc truy vấn. Bẫy:
  - `count(*)` phải gộp mọi phiên bản để biết còn bao nhiêu dòng sau khi gộp, chậm hơn bảng Duplicate; thêm cột `SUM` giá trị 1 rồi cộng cột đó.
  - `REPLACE` lấy giá trị của lần nạp sau, nhưng thứ tự trong cùng một lô không được đảm bảo.
  - Đếm người dùng khác nhau: `BITMAP_UNION` chính xác (id phải là số nguyên), `HLL_UNION` xấp xỉ với bộ nhớ cố định ([[hyperloglog|HyperLogLog]]).
- **Unique: merge-on-write và merge-on-read**: [[merge-on-write|merge-on-write]] (mặc định cho bảng mới từ 2.1) đánh dấu xoá bản cũ ngay lúc ghi bằng delete bitmap, nên truy vấn không phải gộp và đẩy được điều kiện lọc xuống storage. Merge-on-read ghi nhanh hơn nhưng truy vấn phải gộp phiên bản. Chọn lúc tạo bảng, không đổi được.
- **Đồng bộ từ OLTP**:
  - CDC (Flink CDC hoặc Kafka + Routine Load) vào bảng Unique theo khoá chính.
  - Sự kiện tới sai thứ tự thì khai báo sequence column (`function_column.sequence_col`, ví dụ cột `updated_at` hoặc LSN) để bản cũ không đè bản mới.
  - Xoá đi qua cột ẩn `__DORIS_DELETE_SIGN__`.
  - Partial column update (chỉ với merge-on-write) cho bảng rộng mà mỗi nguồn cập nhật vài cột.
  - Partition key phải nằm trong khoá của bảng Unique, giống unique index trên bảng partition ở bài Partitioning.
- **Partition và bucket**:
  - Partition theo ngày hoặc tháng; dynamic partition tự tạo partition tương lai và xoá partition quá hạn (`dynamic_partition.start = -90`), rẻ hơn nhiều so với `DELETE`.
  - Bucket theo cột có nhiều giá trị khác nhau và hay xuất hiện trong điều kiện lọc.
  - Tài liệu khuyên tablet 1–20 GB dữ liệu nén (bảng Unique dưới 10 GB).
  - Quá nhiều tablet nhỏ làm FE nặng metadata và mỗi lần nạp chạm nhiều tablet hơn; quá ít thì mất song song.
  - Số bucket chỉ đổi được cho partition mới, không đổi được cho partition đã có; `BUCKETS AUTO` (từ 2.0) ước theo `estimate_partition_size`.
- **Index**:
  - Prefix index tự có: thưa, mỗi 1.024 dòng một mục, tối đa 36 byte đầu của khoá, gặp cột `VARCHAR` thì dừng. Vì vậy khoá `(seller_id BIGINT, dt DATE, ...)` lọc theo seller nhanh, còn chỉ lọc theo `dt` thì không dùng được prefix index.
  - [[zone-map|ZoneMap]] (min/max mỗi page) tự có, giúp bỏ page khi lọc theo khoảng.
  - Tạo thêm khi cần: Bloom filter cho `=`/`IN` trên cột nhiều giá trị, NGram Bloom filter cho `LIKE '%...%'`, và [[inverted-index|inverted index]] (từ 2.0) cho `MATCH_ANY`, `MATCH_ALL`, `MATCH_PHRASE`, `MATCH_PHRASE_PREFIX`. Từ 4.0 có `score()` chấm BM25 và hàm `SEARCH()`, nên Doris làm được tìm log kiểu Elasticsearch bằng SQL.
- **Materialized view**:
  - Đồng bộ: trên một bảng, cập nhật cùng lúc với lần nạp, dùng để gộp trước hoặc sắp xếp theo khoá khác.
  - Bất đồng bộ (`CREATE MATERIALIZED VIEW ... REFRESH AUTO ON SCHEDULE EVERY 1 HOUR`): join nhiều bảng, refresh theo lịch, theo partition thay đổi, hoặc `ON COMMIT` từ 2.1.4.
  - Optimizer viết lại truy vấn để dùng view khi khớp (SPJG: select, project, join, group by). View bất đồng bộ có thể cũ hơn bảng gốc; `grace_period` quy định chấp nhận cũ bao lâu khi viết lại.
- **Join**: broadcast (bảng nhỏ gửi tới mọi node), shuffle (chia cả hai bên theo khoá join), bucket shuffle (chỉ chia một bên theo bucket của bên kia), và [[colocate-join|colocate join]] (hai bảng cùng cột bucket, cùng số bucket trong một colocation group thì join tại chỗ, không truyền qua mạng). Runtime filter đẩy tập khoá của bảng nhỏ sang phía quét bảng lớn. Join hai bảng hàng tỉ dòng vẫn tốn; báo cáo cố định thường dựng bảng rộng phi chuẩn hoá trước.
- **Truy vấn điểm**: bảng Unique merge-on-write bật `"store_row_column" = "true"` (lưu thêm bản theo dòng) và dùng prepared statement phía server (Connector/J `useServerPrepStmts=true`, nên thêm `cachePrepStmts=true`) với điều kiện `=` trên toàn bộ khoá thì `WHERE id = ?` đi đường ngắn, không qua bộ lập kế hoạch đầy đủ. Đây là tra theo khoá; truy vấn có `GROUP BY` hay `ORDER BY ... LIMIT` trên nhiều dòng vẫn tốn cỡ chục mili giây trở lên và giới hạn số truy vấn đồng thời mỗi node.
- **Từ Java**: MySQL Connector/J tới FE cổng 9030; nhớ `rewriteBatchedStatements=true` nếu dùng `INSERT` theo lô qua JDBC, nhưng nạp lớn thì dùng Stream Load hoặc connector Flink/Kafka. Kết nối qua HikariCP như MySQL, nhưng truy vấn báo cáo dài nên đặt `queryTimeout` và giới hạn đồng thời ở phía ứng dụng.
- **Tách compute và storage (3.0+)**: BE không giữ dữ liệu, chỉ cache trên đĩa local; dữ liệu và metadata nằm ở object storage và meta service. Lợi: scale compute nhanh, nhiều compute group cô lập ETL với dashboard. Giá: truy vấn chạm dữ liệu chưa có trong cache chậm hơn nhiều (đọc S3), nên phải theo dõi tỉ lệ cache hit.
- **Doris và các lựa chọn khác**:
  - ClickHouse: rất mạnh với truy vấn một bảng; khử trùng bằng ReplacingMergeTree chỉ xảy ra khi merge (đọc đúng phải `FINAL`); bản tự vận hành cần Keeper/ZooKeeper cho replication. Doris có upsert merge-on-write, giao thức MySQL, FE tự quản metadata, join MPP.
  - [[data-warehouse|Warehouse]] managed (BigQuery, Redshift, Snowflake): không vận hành cụm, tính tiền theo dữ liệu quét hoặc compute, hợp báo cáo nội bộ; dashboard cho khách hàng hàng nghìn truy vấn mỗi phút thì tiền và latency thường nghiêng về engine real-time như Doris.
  - Elasticsearch: mạnh ở relevance và tìm kiếm; phân tích log khối lượng lớn bằng SQL thì Doris thường rẻ hơn về lưu trữ. Doris cũng đọc được bảng Hive, Iceberg, Paimon qua catalog.
