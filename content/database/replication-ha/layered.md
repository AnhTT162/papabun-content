## Quick

Replication chép thay đổi từ **primary** sang **replica** bằng cách gửi log ([[wal|WAL]] của PostgreSQL, [[binlog|binlog]] của MySQL). **Async**: commit không chờ replica, nên replica trễ và failover có thể **mất các commit cuối**. **Sync**: commit chờ replica xác nhận, không mất dữ liệu nhưng chậm hơn và có thể treo khi replica chết. Đọc từ replica thì phải xử lý **[[read-your-writes|read-your-writes]]**. Failover tự động phải có cơ chế chống **[[split-brain|split brain]]** (hai primary cùng nhận ghi).

## Interview

**Hai kiểu replication**:
- **Physical** ([[streaming-replication|streaming replication]] của PostgreSQL): gửi WAL dạng byte, replica là bản sao y hệt cả cluster, cùng major version, chỉ đọc.
- **Logical**: gửi thay đổi theo dòng, chép được một phần bảng và qua các phiên bản khác nhau. PostgreSQL có publication/subscription, nhưng không chép DDL và sequence. MySQL replication dựa trên binlog dạng ROW cũng thuộc loại này, và DDL được ghi dạng câu lệnh nên replica chạy lại.

**Async, sync, semi-sync**:
- PostgreSQL [[synchronous-replication|sync]] qua `synchronous_standby_names`. `synchronous_commit = on` chờ replica flush WAL; `remote_apply` chờ replica áp xong.
- MySQL [[semi-sync-replication|semi-sync]] chờ replica ghi vào [[relay-log|relay log]], nhưng sau `rpl_semi_sync_source_timeout` (mặc định 10 giây) thì **lặng lẽ chuyển về async**.
- Lợi ích: không mất commit khi primary chết. Giá: mỗi commit thêm một vòng mạng, nên replica sync thường ở cùng region.

**[[replica-lag|Replica lag]]** đến từ transaction lớn, replica áp thay đổi bằng một luồng, query trên replica xung đột với việc áp WAL, hoặc replica yếu hơn primary. Khi đọc từ replica:
- Ghi xong rồi đọc lại có thể thấy dữ liệu cũ. Cách xử lý: đọc từ primary trong vài giây sau khi ghi, hoặc chờ replica áp tới LSN hay [[gtid|GTID]] của lần ghi.
- Mỗi request rơi vào một replica trễ khác nhau thì dữ liệu "đi lùi". Cách xử lý: gắn người dùng với một replica ([[monotonic-reads|monotonic reads]]).

**[[failover|Failover]]** gồm bốn bước: phát hiện primary chết, chọn replica mới nhất, promote nó, chuyển ứng dụng sang. Nguy hiểm nhất là primary cũ chỉ bị cô lập mạng, vẫn nhận ghi. Cách chống là [[fencing|fencing]]: primary phải giữ một lease trong hệ đồng thuận (etcd, Consul); [[patroni|Patroni]] tự hạ primary xuống read-only khi không gia hạn được lease. Với async, các commit chưa kịp sang replica sẽ mất: đó là RPO lớn hơn 0.

## Deep

- **Đường đi của MySQL replication**: dump thread trên source gửi binlog → luồng receiver (IO thread) trên replica ghi relay log → các luồng applier (SQL thread) áp vào. `replica_parallel_workers` mặc định 4 từ 8.0.27 (trước đó 0, tức một luồng), song song theo phụ thuộc mà source ghi vào binlog: ở 8.0 mặc định là `COMMIT_ORDER` (chỉ song song các transaction commit cùng nhóm), muốn song song rộng hơn thì đặt `binlog_transaction_dependency_tracking = WRITESET` trên source; từ 8.4 WRITESET là cách duy nhất. **Một transaction luôn chỉ do một worker áp**: một `DELETE` 30 triệu dòng chạy 10 phút trên source thì replica cũng mất cỡ đó, cộng thời gian chờ ghi xong binlog.
- **Bảng không có primary key trên MySQL**: với binlog ROW, replica phải tìm từng dòng để áp. Không có primary key hay unique index thì mỗi event (vài chục dòng) phải quét cả bảng, và một lệnh chạy vài giây trên source có thể làm replica trễ hàng giờ. Bật `sql_require_primary_key`, hoặc `sql_generate_invisible_primary_key` (8.0.30+) để MySQL tự thêm khoá ẩn. Group Replication bắt buộc mỗi bảng có primary key hoặc unique key NOT NULL tương đương.
- **Đo lag cho đúng**:
  - PostgreSQL: `pg_stat_replication` trên primary có `write_lag`, `flush_lag`, `replay_lag` và các LSN; trên replica, `now() - pg_last_xact_replay_timestamp()` sẽ tăng mãi khi primary không có ghi gì, nên đừng cảnh báo chỉ dựa vào nó.
  - MySQL: `Seconds_Behind_Source` so thời điểm event được ghi trên source với giờ hiện tại của replica. Nó chỉ đo phần applier: receiver tụt hậu vì mạng thì vẫn có thể báo 0; luồng SQL dừng thì báo `NULL`. Cách tin cậy là bảng heartbeat (`pt-heartbeat`) được ghi mỗi giây trên source.
- **Sync replication có thể treo**: PostgreSQL với một replica sync duy nhất mà replica đó chết thì mọi commit chờ vô hạn. Dùng quorum `ANY 1 (s1, s2)` với hai replica, hoặc chế độ synchronous của Patroni (tự bỏ sync khi không còn replica khoẻ, trừ khi bật `synchronous_mode_strict`). Commit đang chờ mà bị huỷ thì transaction **đã commit ở primary**, chỉ là chưa được xác nhận trên replica.
- **Semi-sync của MySQL**: `rpl_semi_sync_source_wait_point = AFTER_SYNC` (mặc định, "lossless") chờ replica xác nhận trước khi commit trong InnoDB, nên client khác chưa thấy dữ liệu chưa được bảo vệ. `AFTER_COMMIT` cho người khác thấy dữ liệu trước khi replica nhận, và failover lúc đó có thể làm mất dữ liệu người ta đã đọc. Theo dõi `Rpl_semi_sync_source_status` để biết khi nó đã rơi về async. Tên biến dùng `source` từ 8.0.26; bản cũ dùng `master`.
- **Read-your-writes trong Spring**: `AbstractRoutingDataSource` định tuyến theo `@Transactional(readOnly = true)` phải đi kèm `LazyConnectionDataSourceProxy`, nếu không connection được lấy trước khi biết transaction có chỉ đọc hay không. Spring 6.1.2+ có `LazyConnectionDataSourceProxy.setReadOnlyDataSource`, gọn hơn tự viết routing. Chờ replica theo vị trí log: MySQL lấy GTID của lần ghi (bật `session_track_gtids = OWN_GTID` để driver nhận về sau commit) rồi chạy `SELECT WAIT_FOR_EXECUTED_GTID_SET('<gtid>', 1)` trên replica; PostgreSQL gọi `pg_current_wal_lsn()` ngay sau commit, lưu lại, và trên replica kiểm tra `pg_last_wal_replay_lsn() >= lsn`. `synchronous_commit = remote_apply` cho read-your-writes trên replica sync, đổi lại commit chậm hơn; với quorum `ANY 1 (s1, s2)` thì chỉ **một** replica chắc chắn đã áp, đọc từ replica kia vẫn có thể thấy dữ liệu cũ.
- **Xung đột trên replica PostgreSQL**: replay WAL cần dọn một phiên bản mà query trên replica đang đọc, thì replica chờ tối đa `max_standby_streaming_delay` (30 giây) rồi huỷ query (`canceling statement due to conflict with recovery`). Bật `hot_standby_feedback` thì loại được phần lớn xung đột do dọn phiên bản, nhưng query dài trên replica làm bảng trên primary phình (bài MVCC, VACUUM & undo log); xung đột lock (`DROP`, `TRUNCATE`, `ALTER`, VACUUM cắt page cuối bảng) vẫn huỷ query. Đếm các lần huỷ bằng `pg_stat_database_conflicts`.
- **Logical replication của PostgreSQL**: không chép DDL và giá trị sequence; `UPDATE`/`DELETE` cần replica identity (thường là primary key). Slot logical (Debezium) trước bản 17 không đi theo failover: replica mới không có slot, CDC phải chụp lại dữ liệu từ đầu. Patroni giải quyết từ trước bằng permanent slot. Bản 17 có failover slot (`failover = true`, `sync_replication_slots` trên replica, kèm `hot_standby_feedback`, `primary_slot_name`, `dbname` trong `primary_conninfo`, và `synchronized_standby_slots` trên primary).
- **Phát hiện và quyết định failover**: timeout ngắn thì phát hiện nhanh nhưng dễ failover nhầm khi mạng chập chờn; Patroni mặc định `ttl` 30 giây, `loop_wait` 10 giây. Chọn replica có LSN/GTID mới nhất; Patroni không promote replica trễ hơn `maximum_lag_on_failover` (mặc định 1MB WAL).
- **Fencing và STONITH**: lease chỉ an toàn khi primary cũ tự dừng ghi trước khi lease hết hạn. Lớp bảo vệ thêm: watchdog phần cứng hoặc Linux watchdog khởi động lại máy nếu Patroni treo; STONITH ("shoot the other node in the head") tắt nguồn hoặc cắt mạng node cũ. MySQL: replica nên bật `super_read_only` để không ai vô tình ghi vào.
- **Đưa primary cũ quay lại**: PostgreSQL dùng `pg_rewind` để tua primary cũ về điểm rẽ nhánh rồi theo primary mới (cần `wal_log_hints` hoặc data checksum; từ bản 18 `initdb` bật checksum mặc định). MySQL với GTID: transaction có trên node cũ mà primary mới không có (errant transaction) phải xử lý trước khi cho nó làm replica.
- **Phía ứng dụng Java**:
  - Endpoint ổn định: VIP, DNS (chú ý TTL và cache DNS của JVM), proxy (HAProxy, PgBouncer, ProxySQL, MySQL Router).
  - PostgreSQL JDBC nhận nhiều host: `jdbc:postgresql://db1,db2,db3/shop?targetServerType=primary`.
  - [[hikaricp|HikariCP]] kiểm tra connection khi mượn ra và ping connection rảnh theo `keepaliveTime` (mặc định 2 phút), nhưng không cứu được connection **đang được mượn** và treo giữa query trên primary đã mất: đặt `socketTimeout` của driver hoặc TCP keepalive.
  - Ghi lỗi trong lúc failover cần retry có idempotency, vì commit có thể đã thành công trước khi mất kết nối.
- **Dịch vụ cloud**:
  - RDS Multi-AZ kiểu instance (một standby) chép đồng bộ ở tầng lưu trữ và không cho đọc từ standby; failover thường 1–2 phút. Kiểu Multi-AZ DB cluster có hai standby đọc được, chép bằng semi-sync.
  - Aurora ghi 6 bản qua 3 AZ, commit khi 4 bản xác nhận; replica đọc chung lớp lưu trữ, lag thường dưới 100ms.
  - Read replica của RDS là async.
- **[[rpo-rto|RPO và RTO]]** được định nghĩa ở bài High availability & disaster recovery: async thì RPO bằng lag lúc sự cố; RTO gồm thời gian phát hiện, áp nốt relay log/WAL còn tồn, và thời gian ứng dụng kết nối lại.
