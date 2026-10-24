## Quick

[[sharding|Sharding]] chia dữ liệu qua **nhiều database server**, mỗi shard giữ một phần dòng theo **[[shard-key|shard key]]**. Nó giải quyết giới hạn **ghi và dung lượng** của một máy, nhưng biến query, transaction và unique key xuyên shard thành bài toán khó. **Chọn shard key sao cho gần như mọi query và transaction chỉ chạm một shard**, và chia thành nhiều **[[logical-shard|logical shard]]** ngay từ đầu để sau này thêm máy không phải chép lại tất cả.

## Interview

**Khi nào cần**: một primary không còn chịu nổi lượng ghi, hoặc dữ liệu quá lớn cho việc vận hành (backup, restore, tạo index, VACUUM mất hàng chục giờ). Đọc nhiều thì replica và cache rẻ hơn. Sharding là bước cuối.

**Chọn shard key** theo [[access-pattern|access pattern]]: nhiều giá trị khác nhau, phân bố đều, có mặt trong hầu hết query, và gom dữ liệu hay dùng chung một transaction về cùng shard. Hệ thống SaaS thường chọn `tenant_id`, thương mại điện tử chọn `customer_id`. Shard **theo khoảng** trên thời gian hay id tăng dần thì dồn mọi lượt ghi vào shard cuối ([[hot-partition|hot shard]]).

**Ba cách gán dòng vào shard**:
- **Hash**: phân bố đều, nhưng mất truy vấn theo khoảng; `hash % N` buộc chuyển gần hết dữ liệu khi đổi N.
- **Range**: truy vấn theo khoảng tốt và dễ tách shard, nhưng dễ lệch tải với key tăng dần.
- **[[directory-sharding|Directory]]**: một bảng tra cứu ghi tenant nằm ở shard nào. Linh hoạt nhất, chuyển riêng từng tenant được, đổi lại thêm một lần tra cứu, nên phải cache và giữ nó luôn sẵn sàng.

Thực tế hay dùng **logical shard**: băm key vào 1.024 bucket cố định, rồi gán bucket cho máy vật lý. [[resharding|Resharding]] chỉ là chuyển vài bucket.

**Cái giá**:
- Query thiếu shard key thành **[[scatter-gather|scatter-gather]]**: hỏi mọi shard và chờ shard chậm nhất.
- Unique key toàn hệ thống (email đăng nhập) và tra cứu theo cột khác cần bảng tra cứu riêng.
- JOIN với bảng nhỏ dùng chung phải chép bảng đó lên mọi shard ([[reference-table|reference table]]).
- Transaction qua nhiều shard: tránh bằng thiết kế, hoặc dùng saga hay 2PC.
- Auto-increment trùng giữa các shard, nên dùng [[uuid-v7|UUID v7]] hoặc snowflake.

**Công cụ**: Citus (PostgreSQL), Vitess (MySQL), ShardingSphere (thư viện JDBC hoặc proxy), hoặc distributed SQL tự chia và tự tách khi lớn (CockroachDB, TiDB theo khoảng; YugabyteDB mặc định theo hash).

## Deep

- **Vì sao `% N` đắt**: key `k` nằm ở shard `hash(k) % N`. Đổi N từ 8 lên 9, key chỉ đứng yên khi `hash % 8 == hash % 9`, tức khoảng 1/9 số key; 8/9 phải chuyển. Logical shard hoặc consistent hashing (bài Consistent hashing) chỉ chuyển khoảng 1/N. Redis Cluster dùng 16.384 slot cố định; Citus mặc định 32 shard cho mỗi bảng phân tán (`citus.shard_count`); Vitess chia keyspace ID (8 byte với hash vindex) thành các khoảng, đặt tên shard theo khoảng như `-80`, `80-`.
- **Tenant quá lớn**: directory cho phép đặt riêng nó lên một shard. Nếu một tenant vượt cả một máy thì phải chia tiếp bên trong tenant đó theo key thứ hai (ví dụ `(tenant_id, store_id)`), và các query của tenant đó lại thành xuyên shard. Key "nóng" kiểu tài khoản người nổi tiếng thì thêm muối (salting): ghi vào `key#0..key#7` rồi gộp khi đọc.
- **Scatter-gather chi tiết**:
  - Phân trang `ORDER BY created_at DESC LIMIT 20 OFFSET 1000` trên 8 shard: mỗi shard phải trả 1.020 dòng để lớp định tuyến trộn lại, nên OFFSET càng sâu càng đắt. Dùng [[keyset-pagination|keyset pagination]].
  - Tổng và đếm cộng được từ từng shard; trung bình phải gom tổng và số lượng; đếm phân biệt (`COUNT(DISTINCT)`) chính xác thì phải gom giá trị, nên thường dùng ước lượng HyperLogLog.
  - Latency bằng shard chậm nhất: 1 shard có p99 50ms thì hỏi 16 shard, xác suất ít nhất một shard chậm hơn p99 là `1 - 0,99^16 ≈ 15%`.
- **Tra cứu theo cột không phải shard key** (tìm đơn theo `order_no`, user theo email): bảng tra cứu `order_no → tenant_id` chia shard theo chính `order_no`, giống [[global-index|global index]] của bài Partitioning. Ghi vào hai shard không cùng transaction, nên hoặc ghi bảng tra cứu trước (giữ chỗ, unique), rồi ghi dữ liệu chính, kèm job đối soát dọn chỗ giữ mồ côi; hoặc cập nhật bảng tra cứu bất đồng bộ qua [[cdc|CDC]] và chấp nhận trễ. Vitess gọi đây là lookup vindex.
- **ID**: đặt shard hoặc bucket vào trong ID (snowflake có bit cho máy sinh) thì định tuyến được chỉ từ ID. Không để mỗi shard tự đánh sequence từ 1. Chi tiết ở bài Đồng hồ, thứ tự & sinh ID.
- **Resharding không dừng hệ thống** (cách Vitess `Reshard`/`MoveTables` và các công cụ tương tự làm):
  - Chép snapshot các bucket cần chuyển sang shard mới.
  - Đọc binlog hoặc WAL để áp tiếp các thay đổi xảy ra trong lúc chép.
  - So sánh dữ liệu hai bên (Vitess có `VDiff`).
  - Chuyển đọc trước (Vitess chuyển replica trước, primary sau), so kết quả đọc hai bên trên một phần lưu lượng.
  - Cắt chuyển ghi: chặn ghi các bucket đó **ngay trong database cũ** (không chỉ cờ trong ứng dụng, vì pod cache directory cũ hoặc transaction đang mở vẫn ghi được), chờ bên mới theo kịp **theo vị trí log** chứ không theo số giây, đổi directory có số phiên bản (shard từ chối request mang phiên bản cũ), rồi mở ghi.
  - Trước khi mở ghi, bật replication **ngược** từ shard mới về shard cũ (Vitess `SwitchTraffic` tự làm). Nhờ vậy quay lại chỉ là cắt chuyển theo chiều ngược; không có nó, quay lại sẽ mất mọi lượt ghi sau cắt chuyển. Chỉ xoá dữ liệu cũ sau khi đã tắt replication ngược.
- **Logical replication của PostgreSQL để chuyển tenant**: bản 15+ có row filter (`CREATE PUBLICATION ... FOR TABLE orders WHERE (tenant_id = 42)`), lần chép đầu cũng theo filter. Điều kiện và giới hạn:
  - Với `UPDATE`/`DELETE`, cột trong filter phải thuộc [[replica-identity|replica identity]], tức `tenant_id` nằm trong primary key; không thì phải `REPLICA IDENTITY FULL`, rất đắt.
  - Không chép sequence (phải `setval` bên đích trước cắt chuyển), không chép DDL (đóng băng migration trong lúc chuyển), không chép large object.
  - `TRUNCATE` không theo row filter: chạy trên bảng nguồn là xoá sạch bảng ở đích.
  - Chép ban đầu của tenant lớn kéo dài nhiều giờ, slot giữ WAL và giữ xmin horizon trên primary (bài MVCC, VACUUM & undo log); bản 16+ cho phép logical decoding trên standby.
- **Citus**: `SELECT create_distributed_table('orders', 'tenant_id');`. Các bảng có cột phân tán cùng kiểu, cùng số shard và cùng nhóm được **[[co-location|co-location]]** (shard cùng khoảng hash nằm trên cùng node), nên JOIN và transaction theo `tenant_id` chạy trọn trên một node. `create_reference_table('currencies')` chép bảng nhỏ lên mọi node. Query có `tenant_id` được đẩy thẳng xuống một shard; query không có thì chạy song song trên mọi shard. `citus_rebalance_start()` chuyển shard giữa các node bằng logical replication mà không chặn ghi; `isolate_tenant_to_new_shard()` tách riêng một tenant. Từ Citus 11 query chạy được từ mọi node; Citus 12 có thêm sharding theo schema, hợp với SaaS mỗi tenant một schema.
- **Sharding trong ứng dụng Java**:
  - Tự làm: `AbstractRoutingDataSource` chọn DataSource theo shard key đặt trong context của request. Bẫy: connection được lấy ngay khi `@Transactional` bắt đầu, nên shard key phải được đặt **trước** đó (filter, interceptor) hoặc dùng `LazyConnectionDataSourceProxy`; đặt key bên trong method transactional là đã muộn. Xoá ThreadLocal trong `finally`; `@Async` và thread pool không tự mang key sang. Một transaction Spring chỉ được chạm một shard.
  - Hibernate 6 có multi-tenancy (`@TenantId`, `MultiTenantConnectionProvider` + `CurrentTenantIdentifierResolver`), dùng làm điểm định tuyến theo tenant được, dù nó không phải công cụ sharding đầy đủ.
  - ShardingSphere: khai báo thuật toán chia và viết lại SQL, chạy dạng thư viện JDBC hoặc proxy.
  - Connection nhân lên: 60 pod × 8 shard × pool 10 = 4.800, tức mỗi shard vẫn 600 connection mà đa số rảnh vì mỗi shard chỉ nhận 1/8 tải. Giảm pool mỗi shard, hoặc đặt [[pgbouncer|PgBouncer]] chế độ transaction trước mỗi shard (prepared statement chỉ được hỗ trợ từ PgBouncer 1.21; session state và advisory lock theo session không dùng được).
- **Vận hành N lần**:
  - Migration phải chạy trên mọi shard và chịu được trạng thái nửa vời (shard 1–5 đã đổi, 6–8 chưa), nên càng cần kiểu expand-contract (bài Migration không downtime).
  - Backup của các shard không nhất quán với nhau tại cùng một thời điểm; PITR từng shard về cùng giờ chỉ gần đúng.
  - Giám sát, cảnh báo và runbook phải theo từng shard; một shard chậm làm chậm mọi query scatter-gather.
- **Kích thước shard** nên tính từ vận hành, không chỉ từ tải: restore 1TB mất bao lâu so với RTO, tạo index mất bao lâu. Nhiều đội giữ mỗi shard dưới khoảng 1–2TB.
- **Distributed SQL** tự chia dữ liệu thành các khoảng nhỏ (CockroachDB mặc định 512MB một range) và tự tách, tự cân bằng, mỗi range có Raft riêng. Đổi lại: mỗi lần ghi phải qua đồng thuận nên latency cao hơn database một máy, transaction xuyên range đắt hơn, và secondary index thường nằm khác node với dòng dữ liệu.
