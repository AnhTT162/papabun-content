## Quick

Khác biệt gốc nằm ở **cách lưu dòng**: PostgreSQL lưu bảng dạng **heap**, mọi index trỏ tới vị trí vật lý; InnoDB lưu bảng chính là **[[clustered-index|clustered index]]** theo primary key, index phụ trỏ tới primary key. Từ đó kéo theo khác biệt về [[mvcc|MVCC]] (VACUUM và undo/purge), chi phí `UPDATE`, replication và cách chọn primary key. **PostgreSQL mạnh về tính năng SQL, kiểu dữ liệu và extension; MySQL đơn giản, nhiều công cụ vận hành cho quy mô lớn.** Chọn theo nhu cầu sản phẩm và kinh nghiệm của đội, không theo "cái nào nhanh hơn".

## Interview

**Lưu trữ**:
- PostgreSQL: dòng nằm trong heap không thứ tự; mọi index trỏ tới vị trí vật lý của dòng.
- InnoDB: dòng nằm trong lá của B+tree theo primary key. Tra theo primary key rất nhanh, nhưng index phụ phải tra thêm clustered index.
- Primary key ngẫu nhiên (UUID v4) làm InnoDB tách page liên tục và mọi index phụ phình theo độ rộng của khoá. Nên dùng khoá tăng dần hoặc [[uuid-v7|UUID v7]].

**MVCC**:
- PostgreSQL giữ phiên bản cũ trong heap, cần [[vacuum|VACUUM]], và phải freeze để tránh [[xid-wraparound|XID wraparound]]. Mỗi `UPDATE` tạo phiên bản mới và ghi entry vào **mọi** index, trừ khi là [[hot-update|HOT update]] (không đổi cột có index và page còn chỗ).
- InnoDB sửa tại chỗ và đẩy bản cũ sang [[undo-log|undo log]]; transaction dài làm history list phình.

**[[isolation-level|Isolation]] mặc định**: PostgreSQL READ COMMITTED; InnoDB REPEATABLE READ có [[gap-lock|gap lock]], nên cùng code có thể deadlock trên MySQL mà không deadlock trên PostgreSQL.

**Replication**:
- PostgreSQL: [[streaming-replication|streaming]] vật lý theo WAL (cùng major version), cộng logical replication.
- MySQL: [[binlog|binlog]] dạng dòng, chạy được giữa các phiên bản. Hệ sinh thái lớn: gh-ost, Orchestrator, Group Replication, Vitess.

**Connection**: PostgreSQL mỗi connection là một process, tốn vài MB trở lên, nên hệ thống lớn gần như luôn cần [[pgbouncer|PgBouncer]]. MySQL dùng một thread mỗi connection nên nhẹ hơn, dù vài nghìn connection vẫn làm nó chậm (thread pool chỉ có ở bản Enterprise, Percona, MariaDB).

**Tính năng**:
- PostgreSQL: [[partial-index|partial index]], [[gin-index|GIN]]/GiST/BRIN, [[jsonb|JSONB]] có index, [[exclusion-constraint|exclusion constraint]], DDL trong transaction, row-level security, extension (PostGIS, pgvector).
- MySQL: `INSTANT ADD COLUMN`, invisible index, optimizer hint có sẵn.

**Chọn cho dự án mới**: nhiều team mặc định PostgreSQL khi cần query phức tạp, JSON, dữ liệu địa lý hay ràng buộc mạnh. MySQL hợp khi đội đã vận hành giỏi MySQL, schema đơn giản, OLTP đọc nhiều và có thể sharding bằng Vitess. Cả hai đều có bản managed tốt trên cloud.

## Deep

- **[[collation|Collation]] và so sánh chuỗi**:
  - MySQL 8.0 mặc định `utf8mb4_0900_ai_ci`: bỏ qua hoa thường (`ci`) và dấu (`ai`). `WHERE name = 'cafe'` khớp `Café`, và unique index coi `Nam` và `nam` là trùng.
  - PostgreSQL mặc định phân biệt hoa thường; cần không phân biệt thì dùng `citext`, index trên `lower(col)`, hoặc ICU collation non-deterministic (bản 12+). Collation non-deterministic không dùng được với `LIKE` trước bản 18.
  - `utf8` trong MySQL, kể cả 8.4, vẫn là tên khác (đã deprecated) của `utf8mb3`, không chứa được emoji; luôn dùng `utf8mb4` (mặc định từ 8.0). Từ 8.0.30 có `utf8mb4_vi_0900_ai_ci` cho tiếng Việt; cần phân biệt hoa thường và dấu thì dùng `utf8mb4_0900_as_cs` hoặc `utf8mb4_bin`.
- **Ép kiểu ngầm**: MySQL so `varchar_col = 123` bằng cách đổi chuỗi thành số. Index trên cột chuỗi không dùng được, và `'123abc'` cũng khớp. PostgreSQL báo lỗi kiểu, buộc sửa code. Tham số JDBC truyền đúng kiểu tránh được cả hai vấn đề.
- **Mức nghiêm của MySQL**: `sql_mode` strict là mặc định từ 5.7; trước đó MySQL cắt chuỗi quá dài và nhận ngày `0000-00-00` chỉ kèm warning. `CHECK` constraint chỉ thực sự được kiểm tra từ 8.0.16; bản cũ hơn parse rồi bỏ qua. Hệ thống nâng cấp từ bản cũ thường còn dữ liệu bẩn vì vậy.
- **`GROUP BY`**: MySQL từ 5.7 bật `ONLY_FULL_GROUP_BY`; tắt nó đi thì MySQL trả giá trị bất kỳ cho cột không nằm trong `GROUP BY`. PostgreSQL luôn báo lỗi, trừ khi cột phụ thuộc hàm vào primary key đã group.
- **Lỗi giữa transaction**: PostgreSQL đánh dấu transaction hỏng, mọi câu sau báo `current transaction is aborted` tới khi rollback (pgJDBC có `autosave=conservative` tự đặt savepoint trước mỗi câu); MySQL chỉ huỷ câu lỗi và cho chạy tiếp, trừ deadlock thì rollback cả transaction (bài ACID & transaction cơ bản).
- **DDL**: PostgreSQL rollback được DDL trong transaction; MySQL commit ngầm ở mỗi DDL ([[implicit-commit|implicit commit]]) nhưng có `ALGORITHM=INSTANT` cho nhiều thay đổi cột (bài Migration không downtime).
- **[[upsert|Upsert]]**: PostgreSQL `INSERT ... ON CONFLICT (cột) DO UPDATE` chỉ định rõ ràng buộc nào (bản 15+ còn có `MERGE`); MySQL `ON DUPLICATE KEY UPDATE` kích hoạt khi trùng **bất kỳ** unique key nào, khó đoán khi bảng có nhiều unique key. Cả hai đều tiêu một giá trị sequence hoặc `AUTO_INCREMENT` khi upsert rơi vào nhánh update, nên bảng upsert dày đặc có id rất thưa. MySQL không có `RETURNING`; JDBC lấy khoá sinh ra qua `getGeneratedKeys`.
- **Thứ tự `NULL`**: PostgreSQL coi `NULL` lớn nhất (đứng cuối khi `ASC`) và có `NULLS FIRST/LAST`; MySQL coi `NULL` nhỏ nhất. Phân trang theo cột có `NULL` cho thứ tự khác nhau giữa hai bên.
- **Ngữ nghĩa isolation**: REPEATABLE READ của PostgreSQL là [[snapshot-isolation|snapshot isolation]] thật: `UPDATE` một dòng đã bị transaction khác sửa sau snapshot báo `could not serialize access`. InnoDB REPEATABLE READ đọc snapshot cho `SELECT` thường, nhưng `UPDATE` và `SELECT ... FOR UPDATE` đọc bản mới nhất, nên lost update không bị phát hiện. SERIALIZABLE của PostgreSQL là [[ssi|SSI]]; của InnoDB là biến mọi `SELECT` thành locking read.
- **Kiểu thời gian**: MySQL `TIMESTAMP` lưu UTC và đổi theo múi giờ session, nhưng chỉ tới năm 2038; `DATETIME` không có múi giờ. PostgreSQL `timestamptz` lưu UTC, `timestamp` không có múi giờ. Chọn sai kiểu là nguồn bug lệch giờ khi server và client khác múi giờ.
- **Index**:
  - MySQL không có partial index; thay thế bằng functional index (8.0.13+) hoặc cột sinh. Index giảm dần có từ 8.0.
  - JSON: PostgreSQL index GIN trên `jsonb` cho toán tử chứa (`@>`); MySQL index qua cột sinh hoặc multi-valued index (8.0.17+) cho mảng JSON.
  - Index-only scan của PostgreSQL chỉ hiệu quả khi visibility map đã được VACUUM cập nhật; covering index của InnoDB thường không cần tra lại bảng, trừ khi page index vừa bị sửa bởi transaction mới hơn read view. PostgreSQL không có clustered index được duy trì (`CLUSTER` chỉ sắp xếp một lần).
- **Planner**:
  - PostgreSQL không có hint sẵn (extension `pg_hint_plan`), dựa vào thống kê và extended statistics; có parallel query cho quét, join và aggregate.
  - MySQL có optimizer hint và index hint; hash join từ 8.0.18; parallel query rất hạn chế. `EXPLAIN ANALYZE` có ở cả hai (MySQL từ 8.0.18).
- **Sequence và auto-increment**: cả hai không đảm bảo liên tục. PostgreSQL sequence không rollback; InnoDB `innodb_autoinc_lock_mode = 2` (mặc định từ 8.0) cho insert đồng thời nhanh; `INSERT ... VALUES` nhiều dòng vẫn nhận dãy liền nhau, nhưng bulk insert (`INSERT ... SELECT`, `LOAD DATA`) có thể xen kẽ với câu chạy đồng thời, và mode này không an toàn với binlog dạng statement. Bản 18 của PostgreSQL có sẵn hàm `uuidv7()`.
- **Connection và bộ nhớ**: PostgreSQL `max_connections` mặc định 100, mỗi phép sort hay hash trong query có thể dùng tới `work_mem` riêng, nên nhiều connection cộng query nặng dễ hết RAM. MySQL mặc định 151 connection, bộ nhớ chính là buffer pool dùng chung.
- **Nâng cấp và vòng đời**:
  - PostgreSQL ra major version mỗi năm, mỗi bản được hỗ trợ 5 năm. Nâng major cần `pg_upgrade` (nhanh với `--link`, vẫn phải dừng) hoặc logical replication sang cluster mới để gần như không dừng.
  - MySQL chia thành LTS (khoảng hai năm một bản, 8.4 ra năm 2024) và Innovation; 8.0 hết hỗ trợ tháng 4/2026. Chỉ nâng được từ một LTS lên LTS kế tiếp, nên từ 8.0 phải qua 8.4 trước; xem trang lifecycle của MySQL để biết bản LTS mới nhất. Nâng được làm tại chỗ hoặc qua replica chạy bản mới rồi failover, nhờ binlog chạy được giữa các phiên bản.
  - Chạy bản đã hết hỗ trợ trên RDS bị tính thêm phí Extended Support.
- **Cloud**: cả hai có RDS và Aurora (lớp lưu trữ riêng, replica dùng chung storage), Cloud SQL, Azure. Aurora PostgreSQL và Aurora MySQL khác nhau về tính năng và độ tương thích với bản gốc; kiểm tra extension cần dùng có được hỗ trợ không.
- **Giấy phép và nhánh**: PostgreSQL dùng giấy phép kiểu BSD, phát triển bởi cộng đồng. MySQL do Oracle sở hữu, bản community theo GPL. MariaDB tách ra năm 2009 (từ MySQL 5.1), đi riêng hẳn từ bản 10.0 và đã khác nhiều (GTID, JSON, optimizer), không nên coi là thay thế nguyên vẹn.
