## Quick

Ngoài cache, Redis hay được dùng cho: **bộ đếm và [[rate-limiting|rate limit]]** (`INCR` kèm TTL), **bảng xếp hạng** (sorted set), **lock đơn giản** (`SET NX PX`), **khoá idempotency**, **session**, **hàng đợi nhẹ** (List, Stream) và **đếm phân biệt** (HyperLogLog, bitmap). Hai thứ làm các việc này đúng: mỗi lệnh chạy **nguyên tử** trên một luồng, và **[[lua-script|Lua script]]** gộp nhiều lệnh thành một bước nguyên tử. Bẫy chung: tách đọc rồi ghi thành hai lệnh từ ứng dụng, và quên rằng Redis có thể mất dữ liệu vừa ghi khi failover.

## Interview

**Rate limit**:
- Fixed window: `INCR rl:<user>:<phút>` rồi đặt TTL. Phải đặt TTL **trong cùng bước** (Lua, hoặc `SET ... EX ... NX` trước), nếu không key có thể sống mãi và chặn người dùng vĩnh viễn.
- Sliding window chính xác: sorted set lưu timestamp từng request, `ZREMRANGEBYSCORE` bỏ phần cũ, `ZCARD` để đếm; tốn bộ nhớ theo số request.
- Token bucket: Lua script giữ số token và thời điểm nạp lần cuối trong một hash. (Thuật toán: bài Rate limiting.)

**Bảng xếp hạng**: [[sorted-set|sorted set]], `ZINCRBY` khi cộng điểm và `ZREVRANK` lấy hạng của một người là O(log N); `ZRANGE lb 0 99 REV WITHSCORES` lấy top 100 là O(log N + M). Bằng điểm thì Redis xếp theo thứ tự từ điển của member, nên cần mã hoá thời gian vào score nếu muốn "ai đạt trước xếp trên".

**Lock đơn giản**: `SET lock:k <token> NX PX 30000`, nhả bằng Lua so token (Redis 8.4+ có `DELEX key IFEQ <token>`). Không có fencing token, và mất sau failover; chỉ dùng để giảm việc trùng, không dùng khi sai là mất tiền (bài Distributed lock).

**Idempotency**: `SET idem:<key> PROCESSING NX EX 60` (TTL ngắn, khoảng thời gian xử lý tối đa, để worker chết thì không chặn retry cả ngày); thắng thì xử lý rồi ghi kết quả với TTL dài (`SET idem:<key> <kết quả> EX 86400`), thua thì trả kết quả đã lưu hoặc báo đang xử lý.

**Hàng đợi**:
- List với `LMOVE`/`BLMOVE` sang list "đang xử lý" để không mất việc khi worker chết.
- [[redis-stream|Stream]] có consumer group, `XACK`, và `XAUTOCLAIM` để nhận lại message của consumer đã chết.
- Cả hai đều phụ thuộc bộ nhớ và độ bền của Redis; việc quan trọng dùng broker thật.

**Đếm**: HyperLogLog đếm người dùng phân biệt với 12KB (sai số khoảng 0,81%); bitmap theo user id đếm chính xác ai hoạt động hôm nay (`BITCOUNT`).

## Deep

- **Lua script**:
  - Script chạy nguyên tử: không lệnh nào khác chen vào. Vì vậy script dài **chặn cả Redis**; quá `busy-reply-threshold` (mặc định 5 giây, tên cũ `lua-time-limit`) Redis trả `BUSY` cho client khác, `SCRIPT KILL` chỉ dừng được script chưa ghi gì.
  - `EVALSHA` gửi hash thay vì cả script; nhận `NOSCRIPT` (Redis khởi động lại, failover) thì gửi lại bằng `EVAL`. Spring Data Redis `RedisScript` + `execute` tự làm việc này.
  - Mọi key phải được truyền qua `KEYS`, không tự ghép tên key trong script, để Redis Cluster kiểm tra cùng slot.
  - Redis 7.0 thêm Functions (`FUNCTION LOAD`, `FCALL`): thư viện lưu trên server, được replicate và persist cùng dữ liệu.
  - Script được replicate bằng hiệu ứng (lệnh ghi thật): mặc định từ 5.0, cách duy nhất từ 7.0. Nhờ vậy dùng `TIME` hay giá trị ngẫu nhiên trong script không làm replica lệch.
- **Rate limit chi tiết**:
  - Gộp `INCR` và `EXPIRE` trong Lua: `local c = redis.call('INCR', KEYS[1]); if c == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end; return c`.
  - Hoặc Redis 7: `EXPIRE key 60 NX` sau mỗi `INCR` (pipeline để không thêm round-trip): chỉ đặt TTL khi key chưa có TTL, nên key mất TTL vì lỗi giữa chừng sẽ được đặt lại ở request sau.
  - Fixed window cho phép gấp đôi giới hạn quanh ranh giới cửa sổ (cuối phút này và đầu phút sau). Sliding window ước lượng (hai cửa sổ có trọng số) khắc phục mà chỉ tốn hai key.
  - Mỗi request thêm một round-trip Redis: đặt rate limit ở gateway hoặc gộp kiểm tra, và quyết định khi Redis lỗi thì cho qua (fail open) hay chặn (fail closed).
- **Bảng xếp hạng chi tiết**:
  - Score là số thực 64 bit, chính xác tuyệt đối tới 2^53. Ghép điểm và thời gian: `score = điểm * 2^20 + (2^20 - 1 - giây_tính_từ_đầu_tuần)` (một tuần có 604.800 giây, nhỏ hơn 2^20); điểm tới khoảng 2^33 vẫn chính xác, và cùng điểm thì ai đạt trước có score lớn hơn. Khi đó không dùng `ZINCRBY` được nữa, vì phần thời gian phải tính lại.
  - Một bảng xếp hạng là **một key**, nằm trên một shard; hàng triệu thành viên tốn vài trăm MB và mọi lệnh ghi dồn vào một node. Chia theo vùng hay theo giải đấu nếu vượt sức một node.
  - Bảng theo tuần: một key mỗi tuần (`lb:2026-w43`), dọn key tuần cũ bằng `UNLINK` (giải phóng ở nền). `DEL` một sorted set lớn chặn Redis; key lớn hết hạn qua `EXPIREAT` cũng được giải phóng đồng bộ, trừ khi bật `lazyfree-lazy-expire yes` (mặc định `no`).
  - `ZREVRANGE` bị đánh dấu deprecated từ 6.2, thay bằng `ZRANGE ... REV`; vẫn chạy được trên Redis 8.
  - Hạng của bạn bè: `ZMSCORE lb id1 id2 ...` (6.2+) rồi sắp xếp ở ứng dụng.
  - Redis không phải nguồn sự thật: lưu điểm ở database hoặc log sự kiện để dựng lại khi mất dữ liệu.
- **Đếm và thống kê**:
  - Bộ đếm ghi rất nhiều trên một key (lượt xem bài hot) thành hot key: gộp trong ứng dụng rồi `INCRBY` định kỳ, hoặc chia thành nhiều key.
  - `PFADD`/`PFCOUNT`/`PFMERGE`: gộp HyperLogLog theo ngày thành theo tuần mà không lưu danh sách người dùng.
  - Bitmap theo user id chỉ tiết kiệm khi id dày đặc; id thưa (UUID băm) làm bitmap phình.
- **Session**: hash `session:{id}` với TTL trượt (gia hạn mỗi request). Từ Spring Session 3.0 (vẫn vậy ở 4.x) mặc định dùng `RedisSessionRepository`, chỉ dựa vào TTL; bản có index (`spring.session.redis.repository-type=indexed`, cần cho tìm session theo user) lưu thêm key phụ và cần keyspace notification. Nó tự chạy `CONFIG SET notify-keyspace-events` khi khởi động, lỗi trên Redis managed chặn `CONFIG`: khai báo bean `ConfigureRedisAction.NO_OP` và bật cấu hình phía server. Session mất khi failover nghĩa là người dùng đăng nhập lại; chấp nhận được với đa số hệ thống.
- **Stream chi tiết**:
  - `XREADGROUP` giao message cho một consumer trong group; chưa `XACK` thì message nằm trong pending entries list (`XPENDING`).
  - Consumer chết: consumer khác dùng `XAUTOCLAIM` nhận lại message chờ quá N giây; đếm số lần giao để đưa message lỗi mãi sang stream DLQ.
  - Giới hạn độ dài bằng `XADD ... MAXLEN ~ 1000000`, nếu không stream phình tới hết RAM. Mặc định việc cắt xoá cả entry còn pending trong group, tức có thể mất message chưa xử lý; Redis 8.2 thêm tuỳ chọn `ACKED` để chỉ cắt entry mọi group đã ack.
  - Số lần giao của từng message đọc bằng dạng mở rộng của `XPENDING`.
- **Khi nào không dùng Redis**: dữ liệu không được mất (đơn hàng, số dư), cần truy vấn phức tạp, hay dữ liệu lớn hơn RAM nhiều lần. Redis làm phần nóng và tạm thời, database giữ sự thật.
