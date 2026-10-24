## Quick

Index là cấu trúc dữ liệu đã sắp xếp (thường là [[b-tree|B-tree]]) giúp tìm dòng trong O(log n) thay vì đọc cả bảng. Đổi lại, mỗi lần ghi chậm hơn và tốn thêm dung lượng. **Đừng đoán query có dùng index hay không: đọc `EXPLAIN ANALYZE`.**

## Interview

B-tree index lưu các key đã sắp xếp trong các page, thành một cây thấp (thường 3–4 tầng cho hàng chục triệu dòng). Lá của cây chứa key và vị trí của dòng, và các lá nối với nhau. Nhờ vậy, index phục vụ được tìm bằng (`=`), tìm theo khoảng (`>`, `BETWEEN`, `LIKE 'abc%'`) và `ORDER BY` mà không cần sort.

Cách lưu khác nhau giữa hai database phổ biến:
- **PostgreSQL**: bảng là một vùng lưu riêng (heap). Mọi index trỏ tới vị trí vật lý của dòng ([[tid|TID]]).
- **MySQL InnoDB**: bảng chính là [[clustered-index|clustered index]] theo primary key. Index phụ lưu primary key, nên tìm qua index phụ phải tra thêm một lần nữa vào clustered index.

Với **[[composite-index|index nhiều cột]]** `(a, b, c)`, B-tree sắp theo `a`, rồi `b`, rồi `c`. Index tìm thẳng được với `a`, `a + b`, `a + b + c`, nhưng không với riêng `b`. Cột so sánh bằng nên đặt trước, cột so sánh khoảng hoặc `ORDER BY` đặt sau. Nếu index chứa đủ mọi cột query cần ([[covering-index|covering index]]), database trả kết quả từ index ([[index-only-scan|Index Only Scan]]).

**[[execution-plan|Execution plan]]**: planner ước lượng chi phí của các cách chạy dựa trên [[planner-statistics|thống kê]] của bảng, rồi chọn cách rẻ nhất. Nếu điều kiện khớp quá nhiều dòng (độ [[selectivity|chọn lọc]] thấp), [[seq-scan|Seq Scan]] đọc tuần tự lại rẻ hơn hàng trăm nghìn lần nhảy qua lại giữa index và bảng.

Đọc plan theo các bước:
1. `EXPLAIN` chỉ cho ước lượng. `EXPLAIN ANALYZE` chạy thật và cho số liệu thật.
2. So `rows` ước lượng với `actual rows`. Lệch hàng chục lần thường do thống kê cũ (chạy `ANALYZE`), các cột tương quan với nhau (`CREATE STATISTICS`), hoặc điều kiện bọc trong hàm.
3. Tìm node tốn thời gian nhất, và các dòng `Rows Removed by Filter` lớn.

Ba lý do hay gặp khiến index không được dùng. Cả ba đều là điều kiện không [[sargable]]:
- Bọc cột trong hàm: `WHERE date(created_at) = ...` hay `lower(email) = ...`.
- `LIKE '%abc'`: có ký tự đại diện ở đầu.
- So sánh khác kiểu dữ liệu, buộc database ép kiểu từng dòng.

## Deep

- **Không chỉ có B-tree** (PostgreSQL):
  - **Hash**: chỉ phục vụ so sánh bằng, một cột, không làm UNIQUE được (an toàn khi sập máy từ PostgreSQL 10); hiếm khi hơn B-tree.
  - **[[gin-index|GIN]]**: index đảo ngược cho giá trị chứa nhiều phần tử: `jsonb` (`@>`; operator class `jsonb_path_ops` nhỏ hơn nhưng không hỗ trợ `?`), mảng, full-text search (`tsvector`), và `LIKE '%abc%'` qua extension `pg_trgm` với `gin_trgm_ops`.
  - **GiST**: dữ liệu không gian (PostGIS), khoảng thời gian (`tstzrange`), tìm láng giềng gần nhất; là nền của exclusion constraint, ví dụ hai lượt đặt phòng không được chồng thời gian (`EXCLUDE USING gist (room_id WITH =, during WITH &&)`, cần extension `btree_gist` cho phần `room_id`).
  - **[[brin-index|BRIN]]**: chỉ lưu min/max cho mỗi dải page, nhỏ hơn B-tree hàng trăm lần. Hợp với bảng rất lớn mà giá trị tăng theo thứ tự ghi (log, sự kiện theo `created_at`); vô dụng khi dữ liệu xáo trộn.
  - MySQL InnoDB chủ yếu có B-tree, cộng `FULLTEXT` và `SPATIAL` (R-tree).
- **[[bitmap-scan|Bitmap Index Scan]]**: với độ chọn lọc trung bình (vài phần trăm bảng), PostgreSQL gom vị trí dòng từ index thành bitmap theo page, rồi đọc bảng theo thứ tự vật lý (`Bitmap Heap Scan`). Nó còn kết hợp được nhiều index bằng `BitmapAnd`/`BitmapOr`, ví dụ `WHERE status = 'NEW' OR customer_id = 42`. MySQL có cơ chế tương tự gọi là index merge. Khi bitmap vượt `work_mem`, nó chuyển sang lossy (chỉ nhớ page, không nhớ dòng): `EXPLAIN ANALYZE` hiện `Heap Blocks: lossy=…` và `Rows Removed by Index Recheck`, vì mọi dòng trong page phải kiểm lại điều kiện.
- **Thứ tự sắp xếp trong index**: `ORDER BY created_at DESC, id ASC` chỉ tránh được sort khi index là `(created_at DESC, id ASC)` hoặc đảo ngược toàn bộ. Index `(created_at, id)` thì không, vì hai cột ngược chiều. MySQL hỗ trợ index giảm dần thật từ 8.0; PostgreSQL có thêm `NULLS FIRST/LAST`.
- **[[index-bloat|Index phình]]**: trong PostgreSQL, `UPDATE`/`DELETE` để lại entry chết trong index; page B-tree đã tách không tự gộp lại, nên index của bảng ghi nhiều có thể to gấp nhiều lần dữ liệu thật. Kiểm tra bằng extension `pgstattuple`, dọn bằng `REINDEX INDEX CONCURRENTLY` (PostgreSQL 12+). VACUUM có dọn entry chết nhưng chỉ để tái sử dụng chỗ trống, không trả lại dung lượng. Từ PostgreSQL 13, B-tree gộp các key trùng (deduplication); từ 14, bottom-up deletion dọn sớm entry của các bản cập nhật không phải HOT, nên bloat giảm đáng kể.
- **Unique index và `NULL`**: cả PostgreSQL và MySQL đều cho nhiều dòng `NULL` trong cột unique, vì `NULL` không bằng `NULL`. PostgreSQL 15 có `UNIQUE NULLS NOT DISTINCT` để coi chúng là trùng.
- **Thử bỏ index an toàn**: MySQL 8.0 có invisible index (`ALTER TABLE orders ALTER INDEX idx_status INVISIBLE`): optimizer bỏ qua nhưng index vẫn được cập nhật (index UNIQUE vẫn kiểm tra trùng; primary key thì không ẩn được), thấy chậm thì bật lại ngay thay vì tạo lại hàng giờ. PostgreSQL không có sẵn; extension `hypopg` cho thử index giả định trong `EXPLAIN` mà không cần tạo thật.
- **Bảng cực lớn chia [[partitioning|partition]]** thì index cũng chia theo partition, dẫn tới câu hỏi local index hay global index: xem bài Partitioning & Global/Local Index.
- **`EXPLAIN ANALYZE` thực thi câu lệnh**: với `UPDATE`/`DELETE` trên PostgreSQL, chạy trong `BEGIN; ... ROLLBACK;`. Thêm `BUFFERS` để thấy số page đọc từ cache và từ đĩa (từ PostgreSQL 18, `ANALYZE` tự kèm `BUFFERS`).
- **`LIKE 'abc%'` trong PostgreSQL** chỉ dùng B-tree thường khi collation là `C`. Với collation khác (ví dụ `en_US.UTF-8`), cần index với `text_pattern_ops`.
- **Index Only Scan vẫn có thể đọc bảng**: dòng `Heap Fetches: N` cho biết số lần phải đọc bảng vì page chưa all-visible trong visibility map. Bảng ghi nhiều cần autovacuum chạy đủ thường. Từ PostgreSQL 11, `INCLUDE (col)` thêm cột vào index chỉ để covering, không dùng để sắp xếp.
- **[[expression-index|Expression index]]**: `CREATE INDEX ON users (lower(email))` (PostgreSQL), hoặc functional index từ MySQL 8.0.13 với hai lớp ngoặc: `CREATE INDEX idx_email_lower ON users ((lower(email)))`. Query phải dùng đúng biểu thức đó thì mới khớp index.
- **[[partial-index|Partial index]]** (PostgreSQL): `CREATE INDEX ON orders (created_at) WHERE status = 'PENDING'`. Index nhỏ, hợp với query luôn lọc theo một trạng thái hiếm.
- **Index trên khoá ngoại**: PostgreSQL không tự tạo index cho cột foreign key, còn InnoDB thì tự tạo. Thiếu index này thì mỗi lần xoá hoặc đổi key của dòng cha phải quét cả bảng con, và join lọc theo khoá ngoại cũng chậm.
- **Tạo index trên bảng đang chạy**: trong PostgreSQL, `CREATE INDEX` thường chặn ghi cho tới khi xong. `CREATE INDEX CONCURRENTLY` không chặn ghi nhưng quét bảng hai lần và chờ mọi transaction đang chạy; nếu lỗi sẽ để lại index `INVALID`, cần `DROP INDEX CONCURRENTLY` hoặc `REINDEX INDEX CONCURRENTLY`. MySQL InnoDB mặc định đã tạo index online. Ghi rõ `ALGORITHM=INPLACE, LOCK=NONE` để lệnh báo lỗi thay vì âm thầm khoá bảng, và coi chừng chờ metadata lock khi có transaction dài.
- **Mỗi index là chi phí ghi**: mỗi `INSERT` phải cập nhật mọi index. Trong PostgreSQL, sửa cột có B-tree index còn chặn tối ưu [[hot-update|HOT update]]. Tìm index không dùng qua `pg_stat_user_indexes` (`idx_scan = 0`), nhưng loại trừ index của PRIMARY KEY/UNIQUE (vẫn đang giữ ràng buộc), kiểm tra cả replica (thống kê tính riêng từng máy), và chắc chắn thống kê đã tích luỹ đủ lâu.
- **Primary key ngẫu nhiên trong InnoDB** (UUID v4): dòng mới chèn vào giữa clustered index, gây tách page và phân mảnh. Mọi index phụ cũng to ra vì chứa primary key. UUID v7 (có thứ tự theo thời gian) hoặc số tăng dần tránh được việc này.
- **[[skip-scan|Skip scan]]**: MySQL 8.0.13+ và PostgreSQL 18 có thể dùng index `(a, b)` cho điều kiện chỉ trên `b`, nhưng chỉ hiệu quả khi `a` có ít giá trị khác nhau. Đừng thiết kế index dựa vào nó.
- **`OFFSET` lớn vẫn chậm** dù có index, vì phải đi qua và bỏ đi mọi dòng phía trước. Phân trang theo key (`WHERE id > :lastId ORDER BY id LIMIT 20`) giữ được tốc độ ổn định.
