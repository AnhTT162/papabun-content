## Quick

Database lưu dữ liệu thành các [[page]] cố định (PostgreSQL 8KB, InnoDB 16KB) và làm việc với chúng trong [[buffer-pool|buffer pool]] ở RAM. Mọi thay đổi được ghi vào [[wal|WAL]] (ghi tuần tự) trước, **commit chỉ thành công khi WAL đã được [[fsync]] xuống đĩa**, còn page bị sửa được ghi ra file sau, khi [[checkpoint]]. Hầu hết database quan hệ dùng [[b-tree|B+tree]] sửa tại chỗ; các hệ thiên về ghi (RocksDB, Cassandra) dùng [[lsm-tree|LSM-tree]] chỉ ghi nối tiếp.

## Interview

**Đường đi của một lần ghi** (PostgreSQL và InnoDB giống nhau về ý tưởng):
1. Tìm page chứa dòng trong buffer pool; chưa có thì đọc từ đĩa vào.
2. Sửa page trong RAM. Page thành "bẩn" (dirty).
3. Ghi một bản ghi mô tả thay đổi vào WAL (InnoDB gọi là redo log).
4. `COMMIT`: flush WAL và fsync, rồi mới báo thành công.
5. Về sau, background writer và checkpoint ghi các page bẩn ra file dữ liệu. Quy tắc "write-ahead": trước khi ghi một page bẩn, WAL tới vị trí (LSN) của page đó phải được flush trước.

Nhờ vậy, commit chỉ cần một lần ghi tuần tự, còn hàng nghìn lần ghi ngẫu nhiên vào page được gom lại. Sập máy thì phát lại WAL từ checkpoint gần nhất (redo).

**Chi phí của fsync** quyết định số commit mỗi giây: NVMe server có tụ chống mất điện mất vài chục micro giây, NVMe laptop vài trăm micro giây, ổ mạng trên cloud thường 1–3ms. Vì vậy mười nghìn `INSERT` tự commit chậm hơn nhiều so với một transaction mười nghìn dòng. Database gom fsync của nhiều transaction đồng thời ([[group-commit|group commit]]), nhưng một luồng ghi tuần tự vẫn phải chờ fsync cho từng commit.

**B+tree và LSM-tree**:
- **B+tree** sửa page tại chỗ: đọc một key mất vài lần đọc page; ghi là ghi ngẫu nhiên, page có thể bị tách.
- **LSM-tree** ghi vào bảng trong RAM (memtable) cùng một log, đầy thì ghi ra file đã sắp xếp không bao giờ sửa (SSTable). Các file được gộp dần ở nền ([[compaction]]). Ghi rất nhanh và tuần tự, nhưng đọc một key có thể phải xem nhiều file; [[bloom-filter|Bloom filter]] giúp bỏ qua file chắc chắn không chứa key.

Đánh đổi được đo bằng ba loại amplification: ghi ([[write-amplification|write amplification]], một byte dữ liệu thành bao nhiêu byte ghi xuống đĩa), đọc, và dung lượng. B+tree tối ưu đọc, LSM tối ưu ghi.

## Deep

- **Đánh đổi độ bền**: PostgreSQL `synchronous_commit = off` báo commit trước khi fsync. Sập máy có thể mất các commit trong khoảng tối đa 3 × `wal_writer_delay` (mặc định 200ms, tức tới 600ms), nhưng không làm hỏng dữ liệu. Đặt được cho từng transaction (`SET LOCAL synchronous_commit = off`) cho dữ liệu có thể nạp lại. InnoDB `innodb_flush_log_at_trx_commit = 2` ghi log ra OS mỗi commit và fsync mỗi giây: mất tới khoảng 1 giây khi OS hoặc máy sập, không mất khi chỉ `mysqld` sập; `= 0` mất cả khi `mysqld` sập. Muốn binlog cũng bền thì cần `sync_binlog = 1`.
- **Nhờ quy tắc write-ahead**, database được ghi page bẩn ra đĩa bất cứ lúc nào, kể cả page của transaction chưa commit (steal), và không phải ghi page lúc commit (no-force). Cái giá: cần redo để phát lại thay đổi đã commit mà page chưa kịp ghi, và cần cách huỷ thay đổi chưa commit đã nằm trên đĩa (InnoDB dùng undo log; PostgreSQL chỉ cần đánh dấu transaction bị huỷ vì dòng cũ vẫn nằm trong heap).
- **Laptop nhanh "giả"**: trên macOS, `fsync` không buộc ổ flush cache của nó; muốn flush thật PostgreSQL cần `wal_sync_method = fsync_writethrough`. Trên Linux, PostgreSQL mặc định dùng `fdatasync`. Đo hiệu năng ghi trên laptop vì vậy thường lạc quan hơn production.
- **Không bao giờ đặt `fsync = off`** trên PostgreSQL production: sập máy có thể làm hỏng dữ liệu, không chỉ mất vài commit.
- **fsync báo lỗi** ("fsyncgate", 2018): trên Linux, lỗi ghi có thể chỉ được báo một lần rồi page bị coi là sạch, nên retry fsync báo thành công giả. Từ các bản minor tháng 2/2019 (11.2, 10.7, 9.6.12 và tương đương), PostgreSQL PANIC khi fsync lỗi rồi phục hồi từ WAL thay vì retry (tham số `data_sync_retry`, mặc định `off`).
- **[[full-page-write|Full page write]]**: lần đầu một page bị sửa sau checkpoint, PostgreSQL ghi nguyên page vào WAL để chống page bị ghi dở (torn page) khi mất điện. Hậu quả: lượng WAL tăng vọt ngay sau mỗi checkpoint, và checkpoint càng dày WAL càng nhiều. InnoDB giải quyết bằng doublewrite buffer.
- **Checkpoint**: PostgreSQL chạy theo `checkpoint_timeout` (mặc định 5 phút) hoặc khi WAL vượt `max_wal_size` (mặc định 1GB). Log `checkpoints are occurring too frequently` nghĩa là nên tăng `max_wal_size`. Checkpoint được rải đều theo `checkpoint_completion_target` (0.9 từ PostgreSQL 14; bản cũ là 0.5 và hệ thống nâng cấp thường vẫn giữ 0.5) để tránh một đợt I/O dồn. `wal_compression` (lz4/zstd từ bản 15) giảm kích thước full page write. InnoDB dùng fuzzy checkpoint liên tục; dung lượng redo log đặt bằng `innodb_redo_log_capacity` (8.0.30+, mặc định 100MB), redo log quá nhỏ buộc flush page sớm.
- **Phát hiện sớm**: so `checkpoints_req` với `checkpoints_timed` trong `pg_stat_bgwriter` (từ PostgreSQL 17 là `num_requested`/`num_timed` trong `pg_stat_checkpointer`); checkpoint do yêu cầu chiếm đa số nghĩa là WAL chạm `max_wal_size`. `log_checkpoints` bật mặc định từ bản 15. `pg_stat_wal.wal_fpi` đếm số full page write. Từ PostgreSQL 18, các cột I/O như `wal_sync`, `wal_sync_time` chuyển sang `pg_stat_io`.
- **Buffer pool**: InnoDB `innodb_buffer_pool_size` (mặc định 128MB; máy chỉ chạy database thường đặt 50–75% RAM). `innodb_flush_method = O_DIRECT` bỏ qua page cache của OS: mặc định từ MySQL 8.4 trên Linux; bản 8.0 mặc định `fsync` và thường được đặt tay thành `O_DIRECT`. PostgreSQL `shared_buffers` (mặc định 128MB, thường đặt khoảng 25% RAM) và **dựa thêm vào page cache của OS** (đọc có thể được đệm hai lần); `effective_cache_size` chỉ là gợi ý cho planner, không cấp phát gì.
- **Cách lưu dòng**: PostgreSQL lưu bảng dạng heap, không theo thứ tự; khi một dòng vượt khoảng 2KB, các cột lớn nhất được nén và/hoặc đẩy ra bảng phụ TOAST tới khi dòng nhỏ lại (mặc định `pglz`; `lz4` từ bản 14 qua `default_toast_compression`, nếu PostgreSQL được build kèm lz4). InnoDB lưu bảng chính là [[clustered-index|clustered index]] theo primary key; cột `TEXT`/`BLOB` lớn nằm ở page riêng (row format `DYNAMIC`).
- **Phiên bản cũ của dòng** ([[mvcc|MVCC]]): PostgreSQL giữ bản cũ ngay trong heap, cần VACUUM dọn; InnoDB giữ bản cũ trong [[undo-log|undo log]], dòng trong bảng luôn là bản mới nhất. Bài MVCC, VACUUM & undo log đi sâu.
- **WAL còn dùng cho** replication (gửi WAL sang replica) và khôi phục về một thời điểm (PITR): xem các bài Replication và Backup.
- **Đĩa cloud**: ổ mạng có giới hạn IOPS và throughput theo cấu hình (ví dụ AWS gp3 mặc định 3.000 IOPS), và latency fsync cao hơn ổ cục bộ. Ổ NVMe cục bộ nhanh nhưng mất dữ liệu khi máy bị thay, nên chỉ hợp khi có replication.
- **LSM chi tiết**: compaction kiểu leveled (RocksDB mặc định) ít tốn dung lượng và đọc nhanh hơn, ghi nhiều hơn; kiểu size-tiered (STCS, vẫn là mặc định của Cassandra; từ Cassandra 5.0 tài liệu khuyên dùng Unified Compaction Strategy, gộp được cả hai kiểu bằng tham số) ghi ít hơn nhưng tốn dung lượng tạm thời. Xoá là ghi một tombstone, và compaction chỉ được bỏ tombstone sau `gc_grace_seconds` (mặc định 10 ngày) để dữ liệu đã xoá không "sống lại" từ replica chưa nhận lệnh xoá; trong thời gian đó mọi lần đọc phải duyệt qua chúng, nên bảng Cassandra bị xoá nhiều sẽ đọc chậm dần, kể cả khi chạy compaction tay. Dấu hiệu: warning khi một query đọc quá `tombstone_warn_threshold` (1.000) tombstone, và `TombstoneOverwhelmingException` khi vượt `tombstone_failure_threshold` (100.000). Compaction không theo kịp thì database chủ động chặn ghi (write stall). MyRocks đưa RocksDB vào MySQL cho bảng ghi nhiều.
- **Lưu theo cột** (ClickHouse, Parquet, Redshift): lưu từng cột riêng và nén mạnh, hợp với báo cáo quét vài cột trên hàng tỉ dòng, kém với cập nhật từng dòng.
