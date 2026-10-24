## Quick

[[partitioning|Partitioning]] chia một bảng logic thành nhiều bảng vật lý theo [[partition-key|partition key]]. Query có điều kiện trên key thì chỉ đọc các partition liên quan ([[partition-pruning|pruning]]), và xoá dữ liệu cũ thành drop cả partition. **[[local-index|Local index]] chia theo cùng partition nên dễ bảo trì, nhưng không đảm bảo unique trên toàn bảng và phải dò mọi partition khi query thiếu partition key; [[global-index|global index]] thì ngược lại.**

## Interview

Ba kiểu chia phổ biến: **range** (theo khoảng, thường là thời gian), **list** (theo danh sách giá trị như quốc gia), **hash** (chia đều theo hàm băm). Partitioning có ích khi bảng rất lớn và hầu hết query, cùng việc xoá dữ liệu cũ, đều theo partition key. Nó không làm một query đơn lẻ đã có index tốt nhanh hơn đáng kể.

Index trên bảng partition có hai kiểu:
- **Local index**: mỗi partition có index riêng. Drop hay detach một partition thì index của nó đi theo, không ảnh hưởng phần còn lại. Đổi lại, query không có partition key phải dò index của **từng** partition, và ràng buộc unique chỉ kiểm tra được trong một partition, nên unique key bắt buộc chứa partition key.
- **Global index**: một index cho cả bảng, trỏ tới dòng ở bất kỳ partition nào. Nó tra nhanh theo cột không phải partition key và đảm bảo unique toàn bảng. Đổi lại, mỗi lần drop hay truncate partition phải dọn các entry trong global index.

Mỗi database hỗ trợ một kiểu:
- **PostgreSQL** và **MySQL** chỉ có local index, nên primary key và mọi unique key phải chứa cột partition. Muốn unique trên cột khác thì phải dùng bảng tra cứu riêng không chia partition.
- **Oracle** có cả hai kiểu. Drop partition mà không kèm `UPDATE GLOBAL INDEXES` sẽ làm global index thành `UNUSABLE`.

Chọn partition key theo cách dữ liệu được **đọc và xoá**: đơn hàng, log, sự kiện thường chia theo tháng của `created_at`. Điều kiện phải viết [[sargable]] trên chính cột đó (`created_at >= ... AND created_at < ...`) thì planner mới pruning được.

Partitioning nằm trong một database. Khi dữ liệu vượt một máy, chia sang nhiều server là [[sharding]], và câu chuyện local/global index lặp lại ở quy mô mạng. DynamoDB có [[lsi|LSI]] (local, cùng partition key) và [[gsi|GSI]] (global, cập nhật bất đồng bộ nên có thể đọc dữ liệu trễ). Cassandra có secondary index local trên từng node, nên query thiếu partition key phải hỏi mọi node.

## Deep

- **Ràng buộc unique trong PostgreSQL**: `ALTER TABLE orders ADD PRIMARY KEY (id)` trên bảng chia theo `created_at` báo lỗi `unique constraint on partitioned table must include all partitioning columns`. Phải dùng `PRIMARY KEY (id, created_at)`, và lúc đó `id` không còn được database đảm bảo unique toàn bảng. Giữ unique bằng bộ sinh id (sequence chung, UUID v7, snowflake) hoặc bảng tra cứu.
- **MySQL** có cùng quy tắc: mọi unique key, kể cả primary key, phải chứa mọi cột trong biểu thức partition. Bảng InnoDB có partition không hỗ trợ foreign key.
- **Tạo index trên bảng partition đang chạy (PostgreSQL)**: `CREATE INDEX CONCURRENTLY` không dùng được trên bảng cha. Cách làm:
  - `CREATE INDEX ... ON ONLY orders (...)` tạo index rỗng, trạng thái invalid.
  - `CREATE INDEX CONCURRENTLY` trên từng partition.
  - `ALTER INDEX parent_idx ATTACH PARTITION child_idx` cho từng partition; gắn đủ thì index cha tự thành valid.
- **Pruning lúc chạy**: PostgreSQL 11+ pruning cả khi giá trị chỉ biết lúc thực thi (tham số của prepared statement, giá trị từ subquery). Plan có dòng `Subplans Removed: N`. Bọc partition key trong hàm (`date_trunc('month', created_at) = ...`) thì mất pruning, giống như mất index.
- **Xoá dữ liệu cũ**: `ALTER TABLE orders DETACH PARTITION orders_2023_01 CONCURRENTLY` (PostgreSQL 14+) rồi `DROP TABLE`: gần như tức thì, không sinh dòng chết, không cần VACUUM. `DELETE` hàng trăm triệu dòng thì ngược lại. `CONCURRENTLY` không chạy trong transaction block và **không dùng được khi bảng có partition `DEFAULT`**; khi đó dùng `DETACH` thường (giữ lock ngắn).
- **Oracle**: local index có thể là *prefixed* (cột đầu là partition key) hoặc *non-prefixed*. Global index ở trạng thái `UNUSABLE`: loại không unique thì optimizer bỏ qua (đổi plan); loại **unique** thì mọi `INSERT`/`UPDATE` lỗi `ORA-01502`, kể cả khi bật `SKIP_UNUSABLE_INDEXES`. Từ 12c, `DROP PARTITION ... UPDATE INDEXES` chỉ đánh dấu entry mồ côi trong global index rồi dọn sau bằng job nền `PMO_DEFERRED_GIDX_MAINT_JOB` (hoặc gọi `DBMS_PART.CLEANUP_GIDX`), nên lệnh drop không còn phải chờ lâu.
- **Quá nhiều partition** làm planning chậm và tốn bộ nhớ, nhất là với query không pruning được. Chia theo ngày cho dữ liệu giữ 10 năm (hơn 3.600 partition) thường là quá tay; theo tháng là đủ. Tạo trước partition cho các tháng sắp tới. Partition `DEFAULT` nhận dòng ngoài mọi khoảng, nhưng bị khoá và quét mỗi lần tạo partition mới, và chặn `DETACH CONCURRENTLY`; nếu dùng thì giữ nó luôn rỗng và cảnh báo khi có dòng rơi vào.
- **[[hot-partition|Hot partition]]**: chia theo thời gian thì mọi `INSERT` dồn vào partition mới nhất. Trong một máy, điều này còn có lợi (dữ liệu nóng nằm trong cache). Nhưng khi sharding theo thời gian thì một shard gánh toàn bộ lượt ghi, nên shard key thường là hash của `customer_id` hoặc `tenant_id`.
- **DynamoDB**:
  - LSI phải tạo cùng lúc với bảng, đọc được strongly consistent (luôn thấy lần ghi mới nhất), và giới hạn 10GB cho mỗi giá trị partition key.
  - GSI thêm được bất cứ lúc nào, partition key và sort key tuỳ chọn, nhưng chỉ đọc eventually consistent và có throughput riêng. GSI bị throttle (vượt throughput nên request bị từ chối) thì ghi vào bảng chính cũng bị chặn theo.
- **Distributed SQL** (database SQL chạy trên nhiều node như CockroachDB, Spanner, TiDB): trên bảng thường, secondary index mặc định là global, nằm trên node khác với dòng dữ liệu. Mỗi `INSERT` thành transaction phân tán qua nhiều node, nên số index ảnh hưởng latency ghi rõ hơn hẳn so với database một máy.
