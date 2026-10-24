## Quick

Redis giữ toàn bộ dữ liệu trong RAM và thực thi lệnh trên **[[redis-single-thread|một luồng chính]]**: mỗi lệnh là nguyên tử, nhưng **một lệnh chậm chặn mọi client**. Vì vậy tránh lệnh O(N) trên [[redis-big-key|key lớn]] (`KEYS`, `SMEMBERS` một set triệu phần tử, `DEL` một hash khổng lồ). Độ bền đến từ **[[rdb-snapshot|RDB]]** (snapshot bằng `fork`) và **[[aof|AOF]]** (log mọi lệnh ghi); khi dùng làm cache thì đặt `maxmemory` và chính sách eviction.

## Interview

**Kiểu dữ liệu và việc nên dùng**:
- String: giá trị, bộ đếm `INCR`.
- Hash: object nhiều trường.
- List: hàng đợi đơn giản.
- Set: tập không trùng.
- Sorted set: bảng xếp hạng, dữ liệu theo thời gian.
- Stream: log có consumer group.
- Bitmap: cờ theo vị trí bit, đếm chính xác.
- HyperLogLog: đếm phân biệt ước lượng (sai số khoảng 0,81%) với tối đa 12KB.
- Geo: tìm theo vị trí.

Collection nhỏ được lưu gọn (listpack, intset), vượt ngưỡng thì chuyển sang cấu trúc lớn hơn: hash table cho hash và set, skip list cho sorted set, quicklist cho list.

**Mô hình luồng**: luồng chính chạy event loop, thực thi lệnh tuần tự. Từ bản 6, nếu bật `io-threads` (mặc định tắt), I/O thread đảm nhận ghi response, và đọc request khi bật thêm (bản 8 làm cả hai), nhưng **thực thi** vẫn trên một luồng. Ngoài ra có luồng nền cho fsync AOF, giải phóng bộ nhớ (`UNLINK`), và process con khi fork.

**Lệnh nguy hiểm**: `KEYS *` duyệt mọi key (dùng `SCAN`); `HGETALL`, `SMEMBERS`, `LRANGE 0 -1` trên key lớn; `DEL` key lớn (dùng `UNLINK` để giải phóng ở nền); Lua script chạy lâu.

**Hết hạn và eviction**:
- Key có TTL bị xoá khi được truy cập, hoặc khi chu kỳ nền lấy mẫu trúng nó, nên key hết hạn có thể còn chiếm RAM một lúc.
- `maxmemory-policy` quyết định bỏ gì khi đầy. Mặc định `noeviction`: lệnh ghi báo lỗi.

**Độ bền**:
- **RDB**: `fork` một process con ghi snapshot. Nhờ [[copy-on-write|copy-on-write]] nên nhanh, nhưng ghi nhiều trong lúc snapshot làm RAM tăng, và fork trên bộ nhớ lớn có thể dừng Redis hàng trăm mili giây.
- **AOF**: log lệnh ghi với `appendfsync everysec`, có thể mất khoảng 1–2 giây dữ liệu khi sập.

**Phía Java**: Spring Boot mặc định dùng Lettuce, một connection dùng chung. Đặt timeout ngắn: mặc định của Lettuce là 60 giây.

## Deep

- **Mã hoá trong bộ nhớ**:
  - Hash, list, sorted set nhỏ dùng listpack (trước 7.0 là ziplist): một mảng byte liền nhau, rất gọn nhưng tìm kiếm O(N). Ngưỡng ví dụ `hash-max-listpack-entries 128` và `hash-max-listpack-value 64` (byte).
  - Set nhỏ (tối đa `set-max-intset-entries`, mặc định 512) chỉ chứa số nguyên dùng intset; từ 7.2 set nhỏ chứa chuỗi dùng listpack.
  - List dùng quicklist: danh sách liên kết các listpack.
  - Sorted set lớn dùng skip list cộng hash table: `ZADD`, `ZRANK` là O(log N), lấy theo khoảng điểm rất nhanh.
  - `OBJECT ENCODING key` cho biết mã hoá hiện tại; `MEMORY USAGE key` cho biết số byte.
  - Mỗi key tốn thêm vài chục byte chi phí quản lý. Hàng trăm triệu key nhỏ có thể tốn nhiều RAM cho chi phí hơn là cho dữ liệu; gom vào hash theo nhóm là một cách tiết kiệm.
- **Lazyfree**: bật `lazyfree-lazy-user-del yes` để `DEL` chạy như `UNLINK` khi không sửa được code; Redis vẫn để mặc định `no` cho mọi tuỳ chọn `lazyfree-*`, còn Valkey 8 đổi sang `yes`.
- **Tìm lệnh chậm và key lớn**:
  - `SLOWLOG GET` ghi các lệnh chạy lâu hơn `slowlog-log-slower-than` (mặc định 10.000 micro giây). Slowlog chỉ đo thời gian thực thi, không gồm thời gian chờ trong hàng đợi hay đọc ghi mạng.
  - `LATENCY DOCTOR` và `LATENCY LATEST` (bật `latency-monitor-threshold`) ghi cả các sự kiện không phải lệnh như fork, fsync, eviction, hết hạn key.
  - `redis-cli --bigkeys` và `--memkeys` quét tìm key lớn bằng `SCAN`.
  - `INFO commandstats` cho số lần gọi và thời gian trung bình của từng lệnh.
- **Hết hạn chi tiết**: chu kỳ nền chạy theo `hz` (mặc định 10 lần mỗi giây), mỗi lần lấy mẫu một số key có TTL và xoá key hết hạn; nếu tỉ lệ hết hạn trong mẫu cao thì chạy tiếp. Hàng triệu key được đặt **cùng một TTL** cùng hết hạn một lúc, làm chu kỳ này chạy dài và tăng latency. Thêm jitter vào TTL (bài Stampede, penetration, avalanche, hot key).
- **Eviction chi tiết**: `allkeys-lru`, `allkeys-lfu`, `allkeys-random`, các bản `volatile-*` chỉ xét key có TTL, `volatile-ttl` bỏ key sắp hết hạn trước. LRU và LFU là xấp xỉ theo mẫu `maxmemory-samples` (mặc định 5) key. Dùng `volatile-*` mà không key nào có TTL thì hoạt động như `noeviction`.
- **Fork, copy-on-write và hệ điều hành**:
  - Fork phải sao chép bảng trang bộ nhớ; với 24GB dữ liệu thì có thể mất hàng trăm mili giây, trên một số máy ảo còn lâu hơn, và Redis dừng trong lúc đó. Xem `latest_fork_usec` trong `INFO stats`.
  - Mỗi page bị ghi trong lúc snapshot được sao chép, nên workload ghi nhiều có thể cần gần gấp đôi RAM.
  - Tài liệu Redis khuyên tắt Transparent Huge Pages (THP làm mỗi lần copy-on-write sao chép 2MB thay vì 4KB) và đặt `vm.overcommit_memory = 1`; nếu không, fork có thể lỗi `Can't save in background: fork: Cannot allocate memory`.
  - Giảm tác động: snapshot trên replica thay vì primary, giữ mỗi instance nhỏ (nhiều shard), hoặc tắt RDB với Redis chỉ làm cache.
- **AOF chi tiết**:
  - `appendfsync always` (fsync mỗi lệnh, rất chậm), `everysec` (mặc định, thường mất tối đa khoảng 1–2 giây), `no` (để hệ điều hành quyết định).
  - AOF lớn dần, được viết lại (rewrite) bằng fork như RDB. Từ 7.0 AOF gồm nhiều file (một file nền cộng các file tăng thêm) quản lý qua manifest.
  - Đĩa chậm làm fsync chậm; với `everysec`, nếu fsync trước còn chưa xong thì luồng chính có thể phải chờ (`aof_delayed_fsync` trong `INFO persistence`).
  - Kết hợp: `aof-use-rdb-preamble` (mặc định bật) cho file nền của AOF ở dạng RDB, các file tăng thêm ở dạng AOF, nên khởi động nhanh hơn.
- **Bộ nhớ**: `used_memory` là phần Redis cấp phát, `used_memory_rss` là phần hệ điều hành thấy. `mem_fragmentation_ratio` cao (trên 1,5) sau khi xoá nhiều key là phân mảnh; dưới 1 là đang bị swap; tỉ lệ này vô nghĩa khi dữ liệu còn nhỏ. `activedefrag yes` dồn lại dần. Đặt `maxmemory` thấp hơn RAM máy để chừa chỗ cho fork, buffer của client và replication; buffer của client pub/sub hay replica chậm có thể phình (`client-output-buffer-limit`).
- **Pipelining, transaction, Lua**:
  - [[redis-pipelining|Pipelining]]: gửi nhiều lệnh không chờ từng phản hồi, giảm số vòng mạng; không nguyên tử.
  - `MULTI/EXEC`: các lệnh được xếp hàng rồi thực thi liền một mạch, không lệnh của client khác chen vào, nhưng **không rollback**: lệnh lỗi khi chạy thì các lệnh khác vẫn được áp. `WATCH` cho kiểu optimistic locking.
  - Lua script (`EVAL`) và Functions (7.0+) chạy nguyên tử. Script chạy quá `busy-reply-threshold` (trước 7.0 là `lua-time-limit`, mặc định 5 giây) thì Redis trả `BUSY` cho các client khác; script đã ghi dữ liệu thì chỉ dừng được bằng `SHUTDOWN NOSAVE`.
- **Client Java**:
  - Lettuce dùng một connection dùng chung (Netty) và tự xếp lệnh. Dùng Lettuce trực tiếp thì lệnh chặn như `BLPOP` hay pub/sub phải có connection riêng, nếu không chặn mọi lệnh khác. `LettuceConnectionFactory` của Spring tự tách connection riêng cho lệnh chặn, `MULTI` và pub/sub; dùng nhiều thì cấu hình pool (commons-pool2) cho các connection đó.
  - Timeout mặc định của Lettuce là 60 giây; đặt `spring.data.redis.timeout` ngắn (vài trăm mili giây tới 1 giây) để Redis chậm không kéo cả thread pool của ứng dụng theo.
  - Jedis dùng pool connection (`JedisPool`), cần sizing như connection pool của database.
- **Giấy phép**: từ 7.4 (2024), Redis đổi sang RSALv2/SSPL; cộng đồng tách nhánh Valkey (Linux Foundation) từ 7.2.4, tương thích giao thức và được nhiều dịch vụ cloud dùng. Redis 8 (2025) thêm lựa chọn giấy phép AGPLv3. Dịch vụ managed (ElastiCache, MemoryDB, Memorystore) giúp né phần vận hành nhưng giới hạn một số lệnh và cấu hình.
