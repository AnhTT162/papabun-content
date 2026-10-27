## Quick

"Database chậm" có ba dạng cần ba cách xử lý khác nhau: **một câu chậm đi** ([[execution-plan|plan]] đổi, dữ liệu lớn lên), **nhiều câu hơn** (traffic, [[n-plus-one|N+1]], cache miss) và **câu chờ chứ không chạy** (lock, đĩa, connection). Đừng đoán: nhìn [[pg-stat-activity|`pg_stat_activity`]] để biết các session đang chạy trên CPU hay đang chờ, rồi nhìn [[pg-stat-statements|`pg_stat_statements`]] **xếp theo tổng thời gian** để biết câu nào đang ăn tài nguyên.

## Interview

Tôi đi từ database ra, theo ba câu hỏi.

**1. Các session đang làm gì?** Gom `pg_stat_activity` theo `state`, `wait_event_type`, `wait_event`:
- `active` không có [[wait-event|wait event]]: đang chạy trên CPU. Nhiều session như vậy kèm CPU cao là có câu tốn CPU.
- `Lock`: chờ khoá. `pg_blocking_pids(pid)` cho biết ai chặn; đi theo chuỗi tới session gốc, thường là một session [[idle-in-transaction|`idle in transaction`]].
- `IO` (`DataFileRead`): đọc đĩa, dữ liệu không nằm trong cache.
- `Client` (`ClientRead`) ở trạng thái `idle in transaction`: ứng dụng mở transaction rồi làm việc khác trong khi vẫn giữ khoá và connection.

**2. Câu nào tốn nhiều nhất?** `pg_stat_statements` gom mọi câu cùng dạng (tham số thành `$1`), cộng dồn `calls`, `total_exec_time`, `rows`, số block đọc. Xếp theo **tổng** thời gian: câu 2ms gọi 5.000 lần mỗi giây tốn hơn câu 3 giây chạy mỗi phút. Số liệu cộng dồn từ lần reset, nên phải so hai snapshot để thấy khoảng đang có sự cố, và so với cùng giờ hôm qua: `calls` tăng là thêm tải, `mean` tăng là câu chậm đi.

**3. Vì sao câu đó chậm?** `EXPLAIN (ANALYZE, BUFFERS)` **với đúng tham số của lần chạy chậm**, lấy từ [[auto-explain|auto_explain]] hoặc log; cách đọc plan ở bài Index & Execution Plan.

**Cạn [[connection-pool|connection pool]]** thường chỉ là triệu chứng: query chậm hoặc chờ khoá thì connection bị giữ lâu hơn. Tăng pool khi database đã hết CPU chỉ làm mọi câu chậm thêm (bài Connection pool).

**[[replica-lag|Replica lag]]**: đọc từ replica thấy dữ liệu cũ. Đo bằng `replay_lag` trong `pg_stat_replication` trên primary; nguyên nhân và cách xử lý ở bài Replication & high availability.

**MySQL** có công cụ tương ứng: `performance_schema.events_statements_summary_by_digest` (hoặc view `sys.statement_analysis`), slow query log, `sys.innodb_lock_waits`.

**Phòng ngừa**: lưu snapshot pg_stat_statements định kỳ, bật auto_explain với ngưỡng vài trăm ms, đặt `statement_timeout`, [[lock-timeout|`lock_timeout`]] và `idle_in_transaction_session_timeout` cho role của ứng dụng.

## Deep

- **Bẫy `ORDER BY ... LIMIT`**: `WHERE merchant_id = $1 ORDER BY created_at DESC LIMIT 50` khi chỉ có index một cột trên từng cột. Với merchant có nhiều đơn, planner chọn đi lùi trên index `created_at` và lọc theo merchant, vì nó giả định các dòng khớp rải đều nên sẽ gặp đủ 50 dòng rất sớm. Với merchant có toàn đơn cũ, cùng plan đó lướt qua hàng triệu dòng: trên PostgreSQL 17, một bảng 4 triệu dòng, `Rows Removed by Filter: 2304998` và 147ms cho 50 dòng, so với 0,02ms sau khi có index `(merchant_id, created_at)`. Ước lượng số dòng có thể hoàn toàn đúng; cái sai là giả định phân bố, nên `ANALYZE` không cứu được.
- **Mean che giấu phân bố hai đỉnh**: câu nhanh với hầu hết tham số và rất chậm với vài tham số có mean vài ms nhưng `max_exec_time` hàng trăm ms. Nhìn thêm `max_exec_time`, `stddev_exec_time`, và `(shared_blks_hit + shared_blks_read) / calls`: số block mỗi lần gọi tăng vọt là dấu hiệu plan đang đọc nhiều hơn hẳn.
- **Chi tiết của pg_stat_statements**: phải nạp qua `shared_preload_libraries` (cần restart) rồi `CREATE EXTENSION`. Mọi hằng số đều thành tham số, kể cả `'DONE'` hay `LIMIT 50`. Mặc định `track = top` (không tính câu bên trong function) và `track_planning = off`. Từ PostgreSQL 17 có `stats_since` và `minmax_stats_since` để biết số liệu được tính từ lúc nào; `pg_stat_statements_reset()` xoá về 0. Số câu khác nhau có giới hạn (`pg_stat_statements.max`, mặc định 5000); câu sinh động (danh sách `IN` dài khác nhau) đẩy các câu khác ra.
- **Chuỗi chờ khoá**: nhiều session cùng `UPDATE` một dòng đang bị khoá thì session đầu tiên chờ `transactionid` của người giữ khoá, các session sau chờ `tuple` và bị chặn bởi session đầu tiên. `pg_blocking_pids` của chúng trỏ vào nhau chứ không trỏ thẳng tới gốc; phải đi tiếp tới session không bị ai chặn. Cơ chế khoá ở bài Lock & deadlock trong database.
- **Session gốc thường là `idle in transaction`**: ứng dụng mở transaction, cập nhật một dòng, rồi gọi API ngoài hoặc chờ người dùng. Cắt nó bằng `pg_terminate_backend(pid)` để cầm máu; phòng bằng `idle_in_transaction_session_timeout`, và từ PostgreSQL 17 có thêm `transaction_timeout` giới hạn cả transaction. Cả hai đều mặc định tắt.
- **auto_explain**: ghi plan của câu chạy lâu hơn `auto_explain.log_min_duration`, kèm tham số (`log_parameter_max_length`, PostgreSQL 16+). `log_analyze` cho số liệu thật nhưng đo thời gian từng node tốn chi phí cho mọi câu; đặt `log_timing = off` nếu chỉ cần số dòng, và `log_buffers` để thấy số block.
- **Plan đổi mà không ai deploy**: [[autovacuum|autovacuum]] chạy `ANALYZE` (cập nhật [[planner-statistics|thống kê]]) sau khi dữ liệu thay đổi đủ nhiều, dữ liệu vượt một ngưỡng chi phí, một tenant có dữ liệu khác thường bắt đầu dùng hệ thống, hoặc [[prepared-statement|prepared statement]] chuyển sang [[generic-plan|generic plan]] sau 5 lần chạy (bài Các mẫu query hiệu năng). PostgreSQL không có cơ chế ghim plan sẵn (có extension `pg_hint_plan`); MySQL có optimizer hint và index hint; Oracle có SQL plan baseline.
- **Sửa bằng [[composite-index|index ghép]], rồi dọn index thừa**: `(merchant_id, created_at)` cho phép đi thẳng vào phần của một merchant theo đúng thứ tự. Index một cột `(merchant_id)` khi đó là tiền tố thừa; xác nhận bằng `idx_scan` trong `pg_stat_user_indexes` không tăng sau vài ngày (kể cả trên replica, vì số liệu tính riêng từng server) rồi mới xoá. Tạo bằng `CREATE INDEX CONCURRENTLY`: không chặn ghi nhưng không chạy được trong transaction, và nếu lỗi giữa chừng để lại index `INVALID` phải xoá. Nó còn phải chờ mọi transaction đang mở kết thúc, nên một session `idle in transaction` làm nó treo.
- **Đừng chữa CPU bằng thao tác nặng**: `VACUUM FULL` giữ `ACCESS EXCLUSIVE` (chặn cả đọc lẫn ghi) suốt lúc ghi lại bảng; `CREATE INDEX` thường giữ `SHARE` (chặn ghi, đọc vẫn chạy). [[table-bloat|Bloat]] thật thì kiểm bằng `pgstattuple` trước, xử lý bằng [[pg-repack|`pg_repack`]] (bài MVCC, VACUUM & undo log).
- **Cache và đĩa**: `shared_blks_read` (đọc ngoài shared buffers, có thể vẫn trúng page cache của hệ điều hành) tăng cùng `IO: DataFileRead` là dữ liệu nóng không còn vừa bộ nhớ, thường sau một job quét bảng lớn. PostgreSQL 16 thêm `pg_stat_io` để xem I/O theo loại backend.
- **Database bão hoà CPU tuân theo [[littles-law|Little's law]]**: số session active vượt xa số core thì mỗi câu chờ CPU lâu hơn, connection bị giữ lâu hơn, pool cạn. Giảm việc (index, [[rate-limiting|rate limit]], cache) chứ không thêm connection.
- **Replica lag**: `pg_stat_replication` có `write_lag`, `flush_lag`, `replay_lag` (PostgreSQL 10+). Trên replica, `now() - pg_last_xact_replay_timestamp()` tăng cả khi primary không có gì để ghi, nên dễ báo động nhầm. MySQL `Seconds_Behind_Source` (tên từ 8.0.22) cũng không tin được hoàn toàn; dùng bảng heartbeat như `pt-heartbeat`.
- **MySQL**: `long_query_time` mặc định 10 giây nên slow query log gần như không bắt được gì; đặt khoảng 0,2–1 giây. Digest của performance_schema gom câu theo dạng như pg_stat_statements; `sys.statements_with_runtimes_in_95th_percentile` lọc câu thuộc nhóm chậm nhất. Chờ khoá InnoDB xem ở `performance_schema.data_lock_waits` (8.0) hoặc `sys.innodb_lock_waits`.
- **Database managed**: RDS/Aurora Performance Insights và Cloud SQL Query Insights vẽ "DB load" theo wait event và theo câu, về bản chất là lấy mẫu `pg_stat_activity` liên tục cộng với pg_stat_statements.
