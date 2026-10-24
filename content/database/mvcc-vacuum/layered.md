## Quick

[[mvcc|MVCC]] nghĩa là `UPDATE` không ghi đè mà tạo **phiên bản mới**, để người đang đọc vẫn thấy bản cũ. PostgreSQL giữ bản cũ **ngay trong bảng** và cần **[[vacuum|VACUUM]]** dọn; InnoDB giữ bản cũ trong **[[undo-log|undo log]]** và **[[innodb-purge|purge]]** dọn. Cả hai chỉ dọn được phiên bản mà **không transaction nào còn có thể thấy**, nên một transaction mở lâu (kể cả trên replica) làm bảng phình. PostgreSQL còn phải **freeze** dòng cũ để tránh **[[xid-wraparound|XID wraparound]]**.

## Interview

**PostgreSQL**: mỗi phiên bản dòng (tuple) có `xmin` là transaction tạo ra nó và `xmax` là transaction xoá hoặc thay nó. `UPDATE` = ghi tuple mới cộng đặt `xmax` cho tuple cũ; `DELETE` chỉ đặt `xmax`. Một snapshot thấy tuple khi `xmin` đã commit trước snapshot và `xmax` thì chưa. Tuple cũ thành **dòng chết** khi mọi transaction đều không còn thấy nó.

Ranh giới đó là **[[xmin-horizon|xmin horizon]]**: `xmin` nhỏ nhất của các snapshot còn sống. Nó bị giữ lùi bởi transaction dài hoặc `idle in transaction`, [[replication-slot|replication slot]] bị bỏ quên (slot logical, hoặc slot của replica gửi feedback), replica bật [[hot-standby-feedback|`hot_standby_feedback`]] đang chạy query dài, và prepared transaction treo. Khi horizon đứng yên, VACUUM chạy bao nhiêu lần cũng không dọn được, log ghi "dead but not yet removable".

**VACUUM thường** đánh dấu chỗ của dòng chết để tái sử dụng và cập nhật [[visibility-map|visibility map]]; nó không chặn đọc ghi nhưng **không trả dung lượng cho hệ điều hành**. `VACUUM FULL` ghi lại cả bảng dưới lock `ACCESS EXCLUSIVE`. Muốn thu nhỏ bảng khi đang chạy production thì dùng [[pg-repack|pg_repack]].

**[[autovacuum|Autovacuum]]** chạy khi số dòng chết vượt `50 + 20% × số dòng`. Với bảng 1 tỉ dòng là 200 triệu dòng chết (bản 18 chặn trần ở 100 triệu), nên bảng lớn phải hạ `autovacuum_vacuum_scale_factor` riêng.

**XID** là số 32 bit nên quay vòng sau khoảng 4 tỉ transaction. VACUUM **[[tuple-freezing|freeze]]** tuple cũ để chúng luôn được coi là "trong quá khứ". Không freeze kịp thì database ngừng nhận transaction ghi.

**InnoDB**: dòng trong [[clustered-index|clustered index]] luôn là bản mới nhất, có cột ẩn `DB_TRX_ID` và `DB_ROLL_PTR` trỏ về undo log. Consistent read đi ngược chuỗi undo để dựng bản cũ. Transaction dài làm [[history-list-length|history list]] tăng: read view cũ phải đi chuỗi undo dài, bản ghi bị delete-mark chưa purge làm scan index chậm, và undo tablespace to dần. InnoDB không có wraparound, nhưng rollback một transaction lớn rất đắt.

## Deep

- **Snapshot gồm gì**: PostgreSQL ghi `xmin` (mọi XID nhỏ hơn đã kết thúc), `xmax` (XID chưa cấp lúc lấy snapshot) và danh sách XID đang chạy; trạng thái commit nằm trong `pg_xact` (trước bản 10 gọi là `pg_clog`). Lần đầu đọc một tuple sau khi transaction tạo ra nó commit, PostgreSQL đặt **[[hint-bits|hint bit]]** vào tuple để lần sau khỏi tra `pg_xact`. Vì vậy một `SELECT` ngay sau đợt nạp dữ liệu lớn có thể làm bẩn page và ghi xuống đĩa; nếu bật checksum hoặc `wal_log_hints` thì lần sửa đầu tiên của mỗi page sau checkpoint còn sinh WAL.
- **Ai tốn XID**: chỉ transaction ghi mới được cấp XID; transaction chỉ đọc dùng virtual XID. Mỗi subtransaction có ghi ([[savepoint|`SAVEPOINT`]], khối `EXCEPTION` trong PL/pgSQL) tốn thêm một XID. Job xử lý từng dòng và commit từng dòng đốt XID nhanh hơn nhiều so với commit theo lô. Quá 64 subtransaction có XID trong cùng một transaction chưa kết thúc (kể cả savepoint đã `RELEASE`) thì PostgreSQL phải tra `pg_subtrans` khi kiểm tra snapshot, và hiệu năng của cả hệ thống (kể cả replica) có thể giảm mạnh.
- **Visibility map và Index Only Scan**: page chưa được VACUUM đánh dấu all-visible thì [[index-only-scan|Index Only Scan]] vẫn phải đọc bảng để kiểm tra phiên bản (dòng `Heap Fetches` trong plan). Bảng ghi nhiều mà vacuum thưa thì covering index mất tác dụng.
- **Bộ nhớ của vacuum**: `maintenance_work_mem` (hoặc `autovacuum_work_mem`) giữ danh sách dòng chết; đầy thì phải quét mọi index thêm một lượt (dòng `index scans:` trong log lớn hơn 1). Trước bản 17 bị trần 1GB; bản 17 dùng cấu trúc TidStore, gọn hơn nhiều và bỏ trần. `VACUUM (PARALLEL n)` (bản 13+, chỉ khi chạy tay) dọn index song song.
- **Tìm thứ đang giữ horizon** (PostgreSQL):
  - Transaction: `SELECT pid, state, age(backend_xmin), now() - xact_start, left(query, 60) FROM pg_stat_activity WHERE backend_xmin IS NOT NULL ORDER BY age(backend_xmin) DESC;`
  - Replication slot: `SELECT slot_name, active, xmin, catalog_xmin FROM pg_replication_slots;`. Slot vật lý có `xmin` khi replica bật `hot_standby_feedback`; slot logical (Debezium) có `catalog_xmin`, giữ lùi việc dọn bảng hệ thống.
  - Replica không dùng slot: cột `backend_xmin` trong `pg_stat_replication`.
  - Prepared transaction: `SELECT * FROM pg_prepared_xacts;`.
- **Đọc log autovacuum**: `log_autovacuum_min_duration` mặc định 10 phút từ bản 15 (bản cũ tắt). Dòng `tuples: 1200 removed, 412000000 remain, 380000000 are dead but not yet removable` cùng `removable cutoff: 88123004, which was 61200000 XIDs old` (bản 15+; bản cũ ghi `oldest xmin`) cho biết horizon đứng ở đâu và đã cũ bao nhiêu. `pg_stat_user_tables` có `n_dead_tup`, `last_autovacuum`, `autovacuum_count`; `pg_stat_progress_vacuum` xem lần chạy hiện tại.
- **Tinh chỉnh autovacuum**:
  - Ngưỡng theo bảng: `ALTER TABLE orders SET (autovacuum_vacuum_scale_factor = 0.01, autovacuum_vacuum_threshold = 10000);`. Bản 18 thêm `autovacuum_vacuum_max_threshold` (mặc định 100 triệu) để chặn trần ngưỡng.
  - Bảng chỉ insert: từ bản 13 có ngưỡng theo số dòng insert (`autovacuum_vacuum_insert_threshold` 1.000, scale 0.2), để visibility map được cập nhật và dòng được freeze sớm. Trước bản 13, bảng chỉ insert gần như chỉ được vacuum khi tới hạn wraparound.
  - Tốc độ: autovacuum bị hãm theo "cost" (`autovacuum_vacuum_cost_limit` mặc định lấy `vacuum_cost_limit` = 200, chia cho các worker đang chạy; `autovacuum_vacuum_cost_delay` 2ms từ bản 12, trước đó 20ms). Ổ SSD và cloud chịu được giới hạn cao hơn nhiều.
  - Số worker: `autovacuum_max_workers` mặc định 3. Thêm worker mà không tăng cost limit thì mỗi worker chạy chậm hơn, vì giới hạn chia đều.
- **Autovacuum tự nhường**: autovacuum thường tự huỷ khi có ai xin lock xung đột (ví dụ `ALTER TABLE`). Bản chống wraparound (`autovacuum: VACUUM public.orders (to prevent wraparound)` trong `pg_stat_activity`) thì **không** nhường, nên một migration có thể bị kẹt sau nó, và mọi query đến sau kẹt theo hàng đợi lock (bài Lock & deadlock).
- **[[table-bloat|Bảng phình]] và [[index-bloat|index phình]]**: VACUUM thường chỉ cắt được các page trống ở **cuối** file (cần lock mạnh trong chốc lát; tắt bằng `vacuum_truncate = false`). Chỗ trống ở giữa được dùng lại cho dòng mới. Đo chính xác bằng extension `pgstattuple`; ước lượng nhanh bằng câu truy vấn bloat phổ biến dựa trên thống kê. Thu hồi:
  - `pg_repack`: tạo bảng mới, chép dữ liệu và áp thay đổi qua trigger, chỉ cần lock mạnh trong chốc lát lúc đầu và lúc đổi bảng; tài liệu khuyên chừa chỗ trống khoảng gấp đôi bảng cộng index (bảng mới chỉ chứa dòng sống nên bảng phình nặng thực tế cần ít hơn); bảng phải có primary key hoặc unique index trên cột NOT NULL; cần superuser (hoặc chủ bảng với `--no-superuser-check`). Trong lúc chép, chính pg_repack giữ một snapshot nên cũng giữ lùi xmin horizon.
  - `REINDEX INDEX CONCURRENTLY` (bản 12+) cho index phình.
  - `VACUUM FULL` và `CLUSTER` khoá cả đọc lẫn ghi trong suốt thời gian chạy.
- **[[hot-update|HOT update]] và [[fillfactor|fillfactor]]**: `UPDATE` không đổi cột có index và page còn chỗ thì tuple mới nằm cùng page, không cần entry index mới (tuple cũ trỏ sang bằng [[tid|ctid]]); các lần đọc sau tự dọn (prune) chuỗi HOT trong page mà không chờ VACUUM. Bảng update nhiều đặt `fillfactor = 80–90` để chừa chỗ. Theo dõi `n_tup_hot_upd / n_tup_upd`. Thêm một index lên cột hay đổi có thể làm mất HOT và làm bảng phình nhanh hơn hẳn.
- **Freeze và wraparound**:
  - XID so sánh theo vòng tròn: mỗi XID thấy khoảng 2 tỉ XID là quá khứ, 2 tỉ là tương lai. Tuple đã freeze được coi là cũ hơn mọi XID.
  - VACUUM freeze tuple cũ hơn `vacuum_freeze_min_age` (50 triệu); khi tuổi bảng (`age(relfrozenxid)`) vượt `vacuum_freeze_table_age` (150 triệu) thì vacuum quét mọi page chưa all-frozen; vượt `autovacuum_freeze_max_age` (200 triệu) thì autovacuum bị ép chạy kể cả khi đã tắt.
  - Bản 14+ có `vacuum_failsafe_age` (1,6 tỉ): vacuum bỏ qua dọn index và bỏ hãm tốc độ để freeze cho kịp.
  - Từ bản 14: cảnh báo `must be vacuumed within N transactions` khi còn 40 triệu XID, ngừng cấp XID mới khi còn 3 triệu (chỉ còn đọc được). Gỡ mà không cần dừng server: xử lý prepared transaction cũ, kết thúc transaction dài, xoá slot không dùng, rồi chạy `VACUUM` thường cho cả database (không dùng `VACUUM FULL` hay `VACUUM FREEZE`), cuối cùng xem lại cấu hình autovacuum. Bản 12–13: cảnh báo khi còn 11 triệu, ngừng khi còn 1 triệu, và phải dừng server để vacuum ở chế độ single-user.
  - Theo dõi: `SELECT datname, age(datfrozenxid) FROM pg_database;` và cảnh báo khi vượt khoảng 500 triệu–1 tỉ.
  - MultiXact (dùng khi nhiều transaction cùng khoá một dòng, như `FOR SHARE` hay kiểm tra foreign key) cũng quay vòng như XID, ngưỡng `autovacuum_multixact_freeze_max_age` 400 triệu.
- **InnoDB đi sâu**:
  - Clustered index được sửa tại chỗ khi kích thước dòng không đổi nhiều; index phụ không có cột phiên bản, nên sửa cột của index phụ là delete-mark entry cũ rồi insert entry mới.
  - [[read-view|Read view]] ghi danh sách transaction đang chạy lúc tạo; dòng có `DB_TRX_ID` chưa nằm trong snapshot thì đi theo `DB_ROLL_PTR` để dựng bản cũ. Đọc qua index phụ có thể phải tra thêm clustered index để kiểm tra phiên bản, nên covering index mất bớt tác dụng khi dữ liệu đang bị sửa nhiều.
  - Purge thread (`innodb_purge_threads`, mặc định 4 ở 8.0; 8.4 dùng 1 khi máy có từ 16 vCPU trở xuống) xoá undo không còn cần và xoá hẳn các bản ghi bị delete-mark. Theo dõi `History list length` trong `SHOW ENGINE INNODB STATUS` hoặc `trx_rseg_history_len` trong `information_schema.INNODB_METRICS`; vài nghìn là bình thường, hàng triệu là có transaction cũ. Tìm nó bằng `SELECT trx_id, trx_started, trx_mysql_thread_id FROM information_schema.innodb_trx ORDER BY trx_started LIMIT 5;`.
  - Undo nằm trong undo tablespace riêng (mặc định từ 8.0, tự cắt khi vượt `innodb_max_undo_log_size` 1GB vì `innodb_undo_log_truncate` bật). Ở bản rất cũ undo nằm trong `ibdata1`, phình rồi không bao giờ nhỏ lại.
  - `innodb_max_purge_lag` (mặc định 0, tắt) làm chậm DML khi history list quá dài, để purge theo kịp.
  - Thu hồi chỗ sau khi xoá nhiều: `OPTIMIZE TABLE` (với InnoDB là ghi lại bảng, chạy online), hoặc gh-ost/pt-online-schema-change.
- **Rollback**: PostgreSQL rollback gần như tức thì (chỉ đánh dấu aborted trong `pg_xact`, tuple của nó thành dòng chết); InnoDB phải áp ngược từng thay đổi từ undo, kể cả khi khởi động lại sau sự cố, nên huỷ một `DELETE` 50 triệu dòng có thể mất hàng giờ.
- **Oracle** cũng giữ bản cũ trong undo tablespace; khi undo cần đã bị ghi đè thì query dài báo `ORA-01555 snapshot too old` thay vì làm bảng phình. PostgreSQL từng có `old_snapshot_threshold` theo cách tương tự (9.6–16), đã bỏ ở bản 17.
