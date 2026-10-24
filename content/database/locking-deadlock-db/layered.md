## Quick

Database khoá ở hai mức: **[[table-lock|lock cấp bảng]]** (DDL như `ALTER TABLE` cần lock mạnh nhất) và **lock cấp dòng** (`UPDATE`, `FOR UPDATE`). Lock được cấp theo **[[lock-queue|hàng đợi]]**: một `ALTER TABLE` đang chờ sẽ chặn cả các `SELECT` đến sau, nên một migration chờ sau một query dài có thể làm treo cả bảng. **[[deadlock|Deadlock]]** là vòng chờ giữa các transaction; database tự phát hiện và huỷ một bên, ứng dụng phải retry. Khi deadlock nhiều lên, **đọc deadlock log** để tìm cặp câu lệnh gây ra nó.

## Interview

**Lock cấp bảng trong PostgreSQL** có 8 mức. Ba mức hay gặp:
- `SELECT` lấy `ACCESS SHARE`.
- `INSERT`/`UPDATE`/`DELETE` lấy `ROW EXCLUSIVE`.
- Phần lớn `ALTER TABLE`, `DROP`, `TRUNCATE`, `VACUUM FULL` lấy `ACCESS EXCLUSIVE`, xung đột với **mọi** mức khác, kể cả `SELECT`.

Lock giữ tới hết transaction.

**Hàng đợi lock**: yêu cầu lock xung đột với yêu cầu đang chờ phía trước thì phải xếp sau. Một báo cáo chạy 40 phút giữ `ACCESS SHARE`; migration `ALTER TABLE` xin `ACCESS EXCLUSIVE` phải chờ; mọi `SELECT` mới lại xếp sau `ALTER`. Bảng coi như ngừng phục vụ, [[connection-pool|connection pool]] của ứng dụng cạn trong vài giây. Cách phòng: chạy DDL với [[lock-timeout|`lock_timeout`]] ngắn (vài giây) rồi retry, và không để transaction dài trên bảng cần migration.

**MySQL** có cơ chế tương tự là [[metadata-lock|metadata lock]] (MDL): DDL cần MDL độc quyền và phải chờ mọi transaction **đang mở** đã chạm vào bảng, kể cả transaction chỉ `SELECT` rồi chưa commit. Trạng thái `Waiting for table metadata lock` trong `SHOW PROCESSLIST` là dấu hiệu.

**Lock cấp dòng trong InnoDB** nằm trên bản ghi index:
- Record lock: khoá đúng một bản ghi.
- [[gap-lock|Gap lock]]: khoá khoảng trống giữa hai bản ghi, chặn insert vào khoảng đó.
- [[next-key-lock|Next-key lock]]: record cộng khoảng trước nó, mặc định ở REPEATABLE READ.
- [[insert-intention-lock|Insert intention lock]]: lock mà `INSERT` xin vào một khoảng.

Gap lock của các transaction không chặn nhau, nhưng chặn insert intention: đó là nguồn gốc của nhiều deadlock khi "kiểm tra rồi insert".

**Nguyên nhân deadlock hay gặp**:
- Hai transaction khoá cùng các dòng theo thứ tự khác nhau.
- Gap lock cộng insert.
- InnoDB: kiểm tra foreign key (shared lock trên dòng cha) đan xen với `UPDATE` dòng cha. PostgreSQL chỉ gặp khi sửa cột khoá của dòng cha hoặc khoá nó bằng `FOR UPDATE`.
- Batch update đi theo thứ tự index khác nhau.

Cách sửa gốc: thống nhất thứ tự khoá ([[lock-ordering|lock ordering]]), có index phù hợp để khoá ít dòng, transaction ngắn, và [[retry-backoff|retry]] khi bị chọn huỷ.

## Deep

- **Phát hiện deadlock**: PostgreSQL chỉ kiểm tra vòng chờ sau khi chờ quá `deadlock_timeout` (mặc định 1 giây), rồi huỷ một transaction với `deadlock detected` (`40P01`). InnoDB phát hiện ngay khi xin lock (`innodb_deadlock_detect`, mặc định bật) và rollback transaction "nhỏ hơn" (tính theo số dòng đã insert, update, delete), lỗi `1213`. Hệ thống có rất nhiều luồng cùng chờ một dòng đôi khi tắt phát hiện để đỡ tốn CPU; khi đó deadlock thành lỗi `1205` sau `innodb_lock_wait_timeout` (50 giây), và `1205` mặc định chỉ rollback câu lệnh, nên code retry phải tự rollback cả transaction.
- **Đọc deadlock log của PostgreSQL**: log ghi `Process 5120 waits for ShareLock on transaction 9012; blocked by process 5133. Process 5133 waits for ShareLock on transaction 9008; blocked by process 5120.` kèm câu lệnh của từng process. "ShareLock on transaction" nghĩa là đang chờ transaction kia kết thúc, vì nó giữ lock trên dòng cần sửa. Bật `log_lock_waits = on` để log cả các lần chờ lâu hơn `deadlock_timeout` dù không thành deadlock. Lưu ý cả log của PostgreSQL lẫn InnoDB chỉ in câu lệnh **hiện tại** của mỗi transaction, không in câu đã lấy lock trước đó; muốn biết câu đó phải đối chiếu code hoặc log ứng dụng theo transaction.
- **Đọc deadlock log của InnoDB**: `SHOW ENGINE INNODB STATUS` chỉ giữ deadlock **gần nhất** (mục `LATEST DETECTED DEADLOCK`); bật `innodb_print_all_deadlocks = ON` để ghi mọi deadlock vào error log. Mỗi transaction có phần `HOLDS THE LOCK(S)` và `WAITING FOR THIS LOCK TO BE GRANTED`, ghi rõ index và kiểu lock: `lock_mode X locks rec but not gap` (record lock), `lock_mode X locks gap before rec` (gap lock), `lock_mode X` (next-key), `insert intention`. Cuối cùng là `WE ROLL BACK TRANSACTION (2)`.
- **Deadlock vì unique key**: ba session cùng `INSERT` một giá trị unique. Session đầu giữ lock độc quyền; hai session sau gặp trùng nên xin **shared** lock trên bản ghi đó và chờ. Session đầu rollback: hai session kia đều có shared lock và cùng xin exclusive để insert, thành deadlock. Upsert theo một câu lệnh, hoặc retry, xử lý được trường hợp này.
- **READ COMMITTED trong InnoDB** tắt gap lock cho tìm kiếm và quét index (vẫn giữ cho kiểm tra foreign key và trùng khoá), và nhả lock trên các dòng không khớp `WHERE` sau khi đánh giá. Với `UPDATE`, InnoDB còn dùng semi-consistent read: đọc bản đã commit mới nhất để xét `WHERE` và chỉ chờ lock nếu dòng khớp. Nhiều hệ thống chuyển sang READ COMMITTED chính vì giảm deadlock; đổi lại phải chấp nhận phantom, và READ COMMITTED bắt buộc `binlog_format = ROW`.
- **Không có index phù hợp**: `UPDATE orders SET ... WHERE status = 'NEW'` không có index trên `status` sẽ quét và khoá (ở REPEATABLE READ) mọi bản ghi của clustered index, gần như khoá cả bảng.
- **Tìm ai đang chặn ai**:
  - PostgreSQL: `SELECT pid, pg_blocking_pids(pid), wait_event_type, wait_event, now() - xact_start, query FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid)) > 0;`, và `pg_locks` để xem chi tiết. `pg_blocking_pids` tính cả process đứng trước trong hàng đợi; gọi nó liên tục có thể ảnh hưởng hiệu năng, nên đừng đặt trong probe giám sát chạy mỗi giây.
  - MySQL 8.0: `performance_schema.data_locks` và `data_lock_waits`, gọn hơn là view `sys.innodb_lock_waits`; metadata lock xem ở `sys.schema_table_lock_waits`.
- **Transaction mở mà không làm gì** (`idle in transaction`) vẫn giữ mọi lock đã lấy. PostgreSQL có `idle_in_transaction_session_timeout` để tự đóng chúng; nguyên nhân thường là code mở transaction rồi gọi HTTP, hoặc công cụ SQL quên commit.
- **Timeout của DDL trên MySQL**: `lock_wait_timeout` (cho metadata lock) mặc định là 31.536.000 giây, tức **một năm**. Đặt nó vài giây trong session chạy migration. Online DDL vẫn cần MDL độc quyền trong chốc lát: `INPLACE` ở pha chuẩn bị và pha commit, `INSTANT` lúc sửa metadata. Vì vậy vẫn có thể bị kẹt sau một transaction dài. Các công cụ gh-ost và pt-online-schema-change tránh DDL dài bằng bảng bóng (shadow table), nhưng vẫn cần MDL: pt-osc ngay từ đầu khi tạo trigger, cả hai ở bước đổi tên cuối (gh-ost có `--cut-over-lock-timeout-seconds`, mặc định 3, và tự thử lại).
- **DDL an toàn trên PostgreSQL**: `SET lock_timeout = '3s'` trước mỗi DDL và retry vài lần; `ADD COLUMN` không có default, hoặc default là hằng số (từ bản 11), chỉ sửa metadata nên giữ `ACCESS EXCLUSIVE` rất ngắn; `CREATE INDEX CONCURRENTLY`; ràng buộc `NOT VALID` rồi `VALIDATE`. Chi tiết ở bài Migration không downtime.
- **[[advisory-lock|Advisory lock]] đi sâu**: PostgreSQL có bản theo session (`pg_advisory_lock`, phải tự `pg_advisory_unlock`) và theo transaction (`pg_advisory_xact_lock`, tự nhả khi commit hoặc rollback), bản `try` trả về ngay `true`/`false`. Lock theo session cộng dồn: lấy hai lần thì phải nhả hai lần. Key là một số 64 bit hoặc hai số 32 bit (ví dụ namespace và id). Đừng dùng `hashtext(...)`: nó trả về số 32 bit nên dễ trùng hơn, và là hàm nội bộ không cam kết ổn định giữa các phiên bản; cần băm chuỗi thì dùng hàm băm 64 bit của chính ứng dụng. MySQL `GET_LOCK(name, timeout)` theo session, tên tối đa 64 ký tự, giữ được nhiều lock cùng lúc từ 5.7, và nằm trong hệ thống metadata lock nên có phát hiện deadlock giữa các user lock (`ER_USER_LOCK_DEADLOCK`). Advisory lock không đi qua replica. Bản theo session hỏng khi đi qua proxy dùng chung connection: PgBouncer chế độ transaction với PostgreSQL; với MySQL, ProxySQL tự tắt việc dùng chung connection cho session đã gọi `GET_LOCK`.
- **`LOCK TABLE` tường minh** hiếm khi cần; nếu dùng, chọn mức yếu nhất đủ dùng (ví dụ `SHARE ROW EXCLUSIVE` để chặn ghi đồng thời mà vẫn cho đọc), vì `ACCESS EXCLUSIVE` chặn cả đọc.
