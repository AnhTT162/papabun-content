## Quick

Query tốt có chi phí tỉ lệ với **số dòng trả về**, không tỉ lệ với kích thước bảng. Bốn mẫu hay gặp: **phân trang bằng [[keyset-pagination|keyset]] thay vì `OFFSET`**, **không đếm chính xác cả bảng khi không cần**, **ghi hàng loạt bằng batch/[[upsert]] thay vì từng dòng**, và **sửa/xoá dữ liệu lớn theo từng lô**.

## Interview

**Phân trang**: `ORDER BY created_at LIMIT 50 OFFSET 100000` bắt database đọc và bỏ đi 100.000 dòng mỗi lần, nên trang càng sâu càng chậm. Nếu dữ liệu thay đổi giữa hai lần gọi, dòng bị lặp hoặc bị sót. Keyset pagination nhớ khoá của dòng cuối trang trước:

```sql
SELECT id, created_at, total FROM orders
WHERE (created_at, id) < (:lastCreatedAt, :lastId)
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

Với index `(created_at, id)`, mỗi trang chỉ đọc 50 dòng, dù sâu tới đâu. `id` là cột phụ để thứ tự luôn duy nhất. Đổi lại, không nhảy thẳng được tới trang N.

**Đếm**: `count(*)` trong PostgreSQL và InnoDB phải quét bảng hoặc một index, vì với MVCC mỗi transaction thấy một số dòng khác nhau. Trên bảng lớn, dùng `LIMIT n + 1` để biết "còn trang sau", ước lượng từ thống kê, hoặc đếm có giới hạn ("hơn 1.000").

**Ghi hàng loạt**: gửi từng `INSERT` một tốn một vòng đi về mạng và (ở autocommit) một lần commit cho mỗi dòng. Dùng [[jdbc-batching|JDBC batch]] trong một transaction (driver chỉ gộp thật khi bật `rewriteBatchedStatements`/`reWriteBatchedInserts`, xem bài JDBC), `INSERT` nhiều dòng, hoặc `COPY` của PostgreSQL cho lượng rất lớn. Upsert:
- PostgreSQL: `INSERT ... ON CONFLICT (sku) DO UPDATE SET price = EXCLUDED.price`, cần unique index trên `sku`.
- MySQL: `INSERT ... ON DUPLICATE KEY UPDATE price = new.price` (alias `AS new` từ 8.0.19; `VALUES()` đã deprecated).

Cả hai nguyên tử, an toàn khi chạy đồng thời, khác hẳn kiểu "`SELECT` xem có chưa rồi `INSERT` hoặc `UPDATE`".

**`OR` trên các cột khác nhau**: `WHERE email = ? OR phone = ?` không dùng được một index duy nhất. PostgreSQL có thể kết hợp hai index bằng [[bitmap-scan|BitmapOr]], MySQL bằng index merge; nếu planner không chọn, viết lại thành hai query nối bằng `UNION`.

**Sửa/xoá lớn**: chia theo lô nhỏ theo khoá chính và commit sau mỗi lô.

## Deep

- **Keyset trên MySQL**: MySQL (tới 8.0) tính đúng phép so sánh hàng `(created_at, id) < (?, ?)` nhưng không dùng nó làm điều kiện truy cập index. Viết dạng mở rộng `created_at <= ? AND (created_at < ? OR (created_at = ? AND id < ?))`; vế `created_at <= ?` thừa về logic nhưng giúp optimizer lập range scan. PostgreSQL dùng index cho so sánh hàng tốt; Oracle không cho dùng toán tử khoảng trên so sánh hàng.
- **Sắp xếp khác chiều** (`created_at DESC, id ASC`) không viết được bằng một phép so sánh hàng: dùng dạng mở rộng, hoặc giữ mọi cột cùng chiều. **Cột sắp xếp nullable** làm hỏng keyset vì `NULL` không so sánh được: khai báo `NOT NULL`, hoặc xử lý riêng nhóm `NULL` với `NULLS LAST`.
- **Cursor của API** nên là một token mờ (ví dụ base64 của `created_at` và `id`) thay vì lộ tên cột; token chứa đủ thông tin để đi tiếp cả chiều trước lẫn chiều sau.
- **Thứ tự phải duy nhất**: `ORDER BY created_at` khi nhiều dòng cùng `created_at` cho thứ tự không xác định giữa các lần chạy, nên `OFFSET` lẫn keyset đều có thể lặp hoặc sót dòng ở ranh giới trang. Luôn thêm khoá chính làm cột phụ.
- **Spring Data** từ 3.1 có Scroll API: `Window<Order> findFirst50ByStatusOrderByCreatedAtDescIdDesc(String status, ScrollPosition position)` với `ScrollPosition.keyset()`.
- **Đếm ước lượng**: PostgreSQL `SELECT reltuples FROM pg_class WHERE oid = 'public.orders'::regclass` (cập nhật bởi `VACUUM`, `ANALYZE` và `CREATE INDEX`; từ PostgreSQL 14 là `-1` khi chưa từng được thống kê). Planner chính xác hơn: nó lấy `reltuples / relpages × số page hiện tại`, nên vẫn đúng khi bảng tăng nhanh, hoặc lấy `rows` từ `EXPLAIN` cho query có điều kiện. MySQL `information_schema.TABLES.TABLE_ROWS` với InnoDB chỉ là ước lượng, có thể lệch nhiều. Đếm có giới hạn: `SELECT count(*) FROM (SELECT 1 FROM orders WHERE ... LIMIT 1001) t`.
- **`EXISTS` thay `count(*) > 0`**: `EXISTS` dừng ở dòng khớp đầu tiên.
- **`count(*)` vẫn có thể nhanh**: PostgreSQL dùng Index Only Scan trên index nhỏ nhất nếu visibility map còn mới; InnoDB mặc định đếm bằng index phụ nhỏ nhất; khi phải quét clustered index cho `count(*)` không có `WHERE`, bản 8.0.14+ đọc song song theo `innodb_parallel_read_threads` (mặc định 4). Nhanh hơn, nhưng vẫn tỉ lệ với kích thước bảng.
- **Cùng một câu `INSERT ... ON CONFLICT DO UPDATE` có hai dòng cùng khoá** (nhiều `VALUES`, `INSERT ... SELECT`, hoặc JDBC batch đã được `reWriteBatchedInserts` gộp lại) báo lỗi `ON CONFLICT DO UPDATE command cannot affect row a second time`: lọc trùng trước khi gửi. JDBC batch không được gộp gồm các câu lệnh riêng, nên câu sau chỉ update lại. `DO NOTHING` không báo lỗi này; `MERGE` có lỗi tương tự. `DO NOTHING ... RETURNING` không trả gì cho dòng bị bỏ qua.
- **Upsert tiêu tốn sequence**: PostgreSQL gọi `nextval` cho mỗi dòng định insert, kể cả dòng rơi vào nhánh conflict, nên id nhảy cóc. InnoDB cũng có thể tăng `AUTO_INCREMENT` khi `ON DUPLICATE KEY UPDATE` đi vào nhánh update. Đừng dựa vào id liên tục.
- **Upsert đồng thời và deadlock**: hai batch upsert cùng tập khoá nhưng khác thứ tự có thể deadlock. Sắp xếp khoá trong batch. MySQL `ON DUPLICATE KEY UPDATE` khoá cả khoảng trên unique index (next-key lock), nên deadlock hay gặp hơn; với bảng có nhiều hơn một unique index, MySQL cảnh báo hành vi khó đoán vì dòng bị update có thể không phải dòng bạn nghĩ.
- **`MERGE`** (PostgreSQL 15+) linh hoạt hơn `ON CONFLICT` nhưng không có cơ chế chống race tương đương: chạy đồng thời vẫn có thể gặp lỗi unique violation. Với upsert theo một khoá, `ON CONFLICT` vẫn là lựa chọn đúng.
- **Bộ lọc tuỳ chọn** `WHERE (:status IS NULL OR status = :status) AND (:customerId IS NULL OR customer_id = :customerId)` buộc một plan phục vụ mọi tổ hợp. PostgreSQL với prepared statement phía server (pgjdbc dùng từ lần chạy thứ 5) có thể chuyển sang [[generic-plan|generic plan]] sau 5 lần chạy nếu ước lượng chi phí của nó không cao hơn đáng kể so với trung bình các plan riêng. Lỗi hay gặp khi 5 lần đầu không đại diện cho các lần sau: generic plan không biết giá trị thật và có thể quét rộng. Sinh SQL chỉ chứa các điều kiện có mặt (Criteria API, Specification, jOOQ, hoặc `JdbcClient` với điều kiện ghép an toàn). Chẩn đoán bằng `plan_cache_mode = force_custom_plan` (PostgreSQL 12+) hoặc `EXPLAIN (GENERIC_PLAN)` (16+); tắt prepare phía server bằng `prepareThreshold=0` khi cần. MySQL không giữ plan của prepared statement kiểu này: nó tối ưu lại mỗi lần chạy với giá trị thật.
- **`IN` với danh sách lớn**: mỗi độ dài danh sách là một câu SQL khác nhau, làm đầy plan cache. PostgreSQL dùng `= ANY(?)` với một tham số mảng; Hibernate có `hibernate.query.in_clause_parameter_padding=true` để làm tròn độ dài lên luỹ thừa của 2. MySQL chuyển từ dò index sang ước lượng bằng thống kê khi danh sách vượt `eq_range_index_dive_limit` (mặc định 200), ước lượng có thể kém đi.
- **`UNION` và `UNION ALL`**: `UNION` loại trùng (thêm sort hoặc hash); khi hai nhánh không trùng nhau thì dùng `UNION ALL`.
- **Chỉ lấy cột cần**: `SELECT *` kéo cả cột lớn (TOAST trong PostgreSQL), phá [[covering-index|covering index]], và tốn băng thông. Dùng [[dto-projection|DTO projection]] cho màn hình danh sách.
- **Xoá theo lô**: PostgreSQL không có `DELETE ... LIMIT`; dùng `DELETE FROM events WHERE id IN (SELECT id FROM events WHERE created_at < ? ORDER BY id LIMIT 5000)` trong vòng lặp, mỗi lô một transaction. MySQL có `DELETE ... ORDER BY id LIMIT 5000`. Xoá theo thời gian định kỳ trên bảng rất lớn thì [[partitioning|partition]] theo thời gian và drop partition rẻ hơn nhiều (xem bài Partitioning).
- **`UPDATE` hàng loạt trong PostgreSQL** tạo phiên bản dòng mới cho mỗi dòng (MVCC); bảng phình cho tới khi `VACUUM` dọn. Chỉ cập nhật dòng thật sự đổi (`WHERE status IS DISTINCT FROM 'ARCHIVED'`). Để được [[hot-update|HOT update]], cột bị sửa không được nằm trong index nào (trừ BRIN từ PostgreSQL 16) và page phải còn chỗ trống: đặt `fillfactor` khoảng 80–90 cho bảng hay bị update.
