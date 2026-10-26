## Quick

[[rate-limiting|Rate limiting]] giới hạn **số request trong một khoảng thời gian** theo một khoá (user, API key, IP, tenant), vượt thì trả `429 Too Many Requests` kèm `Retry-After`. Bốn thuật toán chính khác nhau ở cách **cho phép burst** và **độ chính xác ở ranh giới cửa sổ**: [[token-bucket|token bucket]] (mặc định tốt), [[leaky-bucket|leaky bucket]], fixed window, sliding window. Khi có nhiều instance, **bộ đếm phải dùng chung** hoặc hạn mức phải chia cho từng instance, và phải quyết trước khi kho bộ đếm lỗi thì **cho qua hay chặn**.

## Interview

**Thuật toán**:
- **Token bucket**: thùng chứa tối đa `capacity` token, nạp `rate` token mỗi giây; mỗi request lấy một token, hết thì từ chối. Cho phép burst bằng `capacity`, trung bình không quá `rate`. Không cần thread nạp: lưu số token và thời điểm nạp cuối, tính bù khi có request. Spring Cloud Gateway (`replenishRate`, `burstCapacity`), Bucket4j, Envoy local rate limit dùng nó.
- **Leaky bucket**: request vào hàng đợi, thoát ra với tốc độ đều; hàng đầy thì từ chối. Làm mượt đầu ra, đổi lại thêm độ trễ. Nginx `limit_req` dùng kiểu này: `burst` là độ dài hàng, `nodelay` cho phần burst đi ngay; mặc định nó từ chối bằng `503`, muốn `429` phải đặt `limit_req_status 429`.
- **[[fixed-window|Fixed window]]**: đếm theo phút (`INCR` key `user:42:12:05`, đặt TTL khi `INCR` trả về 1, gộp trong một Lua script). Rẻ, nhưng 100 request lúc 12:05:59 và 100 request lúc 12:06:00 đều lọt: **gấp đôi** hạn mức trong một giây.
- **[[sliding-window|Sliding window]]**: log từng timestamp (chính xác, tốn bộ nhớ theo số request) hoặc ước lượng từ hai cửa sổ: `trước × phần còn lại + hiện tại`. Ví dụ cửa sổ trước 100, đã qua 25% cửa sổ hiện tại có 30: 100 × 0,75 + 30 = 105.

**Phân tán**: 3 instance gateway, mỗi cái đếm cục bộ 100/phút thì hạn mức thật là 300. Cách làm:
- Bộ đếm chung trong Redis, cập nhật **nguyên tử** bằng `INCR` hoặc [[lua-script|Lua script]]; đọc rồi ghi hai lệnh thì hai instance cùng thấy 99 và cùng cho qua.
- Hoặc chia hạn mức theo số instance khi lưu lượng đã được cân bằng đều; không cần lời gọi mạng nhưng lệch khi instance thay đổi.

**Bẫy**: không trả `Retry-After` khiến client retry ngay và dồn thêm tải; rate limit theo IP chặn cả văn phòng sau NAT; Redis chậm làm mọi request chậm theo. Rate limit **không** thay được [[load-shedding|load shedding]]: nó bảo vệ công bằng giữa client, còn server quá tải vì tổng lưu lượng hợp lệ thì vẫn phải từ chối bớt.

## Deep

- **Code tối giản** (Java 21, đã chạy thử, thời gian truyền vào để test được):
  ```java
  synchronized boolean tryAcquire(long nowNanos) {
      tokens = Math.min(capacity, tokens + (nowNanos - lastRefill) * refillPerNano);
      lastRefill = nowNanos;
      if (tokens >= 1) { tokens -= 1; return true; }
      return false;
  }
  ```
  `capacity = 10`, 5 token mỗi giây: 15 request ở t = 0 thì nhận 10; t = 0,1 s bị từ chối (mới có 0,5 token); t = 0,2 s được; ở t = 3 s, 15 request chỉ nhận 10 vì thùng không chứa quá `capacity` dù đã nghỉ đủ lâu để nạp 14 token. Fixed window 100/phút cho qua đủ 200 request trong 0,2 giây quanh ranh giới phút.
- **Dùng `System.nanoTime()`, không dùng `currentTimeMillis()`**: đồng hồ hệ thống có thể bị NTP chỉnh lùi, làm phép trừ ra số âm. Trong Redis, lấy giờ bằng lệnh `TIME` bên trong script (Redis 5 trở lên, khi script được nhân bản theo kết quả thay vì chạy lại trên replica) thay vì giờ của từng instance gateway, để các máy lệch giờ không đếm khác nhau.
- **[[gcra|GCRA]]** (Generic Cell Rate Algorithm): tương đương leaky bucket dạng đo, chỉ lưu một mốc thời gian "lúc được phép tiếp theo" mỗi khoá; một phép so sánh và một lần ghi. Mô-đun `redis-cell` (`CL.THROTTLE`) dùng nó; đây là module ngoài, nhiều dịch vụ Redis managed không cho cài, khi đó viết GCRA bằng Lua.
- **Resilience4j và Guava trong một JVM**: `RateLimiter` của Resilience4j chia thời gian thành chu kỳ `limitRefreshPeriod`, mỗi chu kỳ cấp lại `limitForPeriod` quyền, thread chờ tối đa `timeoutDuration`; Guava `RateLimiter.acquire()` làm thread **ngủ** cho tới lượt, còn `tryAcquire()` (có hoặc không có timeout) trả `false` để từ chối. Cả hai chỉ giới hạn trong một tiến trình. Giới hạn số lời gọi đồng thời trong một JVM: bài CountDownLatch, Semaphore, CyclicBarrier, Phaser. Script Redis cho từng thuật toán: bài Redis cho lock, rate limit, leaderboard.
- **Envoy**: local rate limit (token bucket mỗi instance) và global rate limit gọi sang dịch vụ rate limit riêng qua gRPC; bản tham khảo của dịch vụ đó lưu bộ đếm fixed window trong Redis. Kết hợp hai lớp: local chặn đột biến rẻ, global giữ hạn mức chính xác theo khách hàng.
- **`INCR` rồi `EXPIRE` là hai lệnh**: client chết giữa hai lệnh thì key không có TTL và bộ đếm không bao giờ đặt lại. Đặt TTL trong cùng Lua script khi `INCR` trả về 1, hoặc dùng `EXPIRE key 60 NX` (Redis 7.0 trở lên) chạy mỗi lần.
- **Redis lỗi thì sao**: fail open (cho qua) giữ dịch vụ sống nhưng mất bảo vệ đúng lúc có thể đang bị tấn công; fail closed (chặn) thì Redis trở thành điểm chết của cả API. Phổ biến: fail open kèm hạn mức cục bộ dự phòng rộng hơn, và cảnh báo. Đặt timeout ngắn (vài ms) cho lời gọi Redis và bọc nó bằng circuit breaker: Redis đã chết thì mạch mở, request bỏ qua Redis ngay để dùng hạn mức cục bộ, không phải chờ hết timeout mỗi lần.
- **Giảm lời gọi Redis**: mỗi instance xin trước một lô token (ví dụ 10) và tiêu dần cục bộ; chính xác kém hơn một chút, đổi lại số lời gọi giảm 10 lần. Key nóng (một khách hàng cực lớn) dồn vào một node Redis Cluster: tách key theo instance.
- **Header**: `429` kèm `Retry-After` (số giây hoặc ngày giờ HTTP). Nhiều API trả thêm `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`; IETF đang chuẩn hoá `RateLimit` và `RateLimit-Policy` (bản nháp, chưa thành RFC). Spring Cloud Gateway trả `429` kèm `X-RateLimit-Remaining`, `X-RateLimit-Replenish-Rate`, `X-RateLimit-Burst-Capacity` nhưng không có `Retry-After`: muốn có thì tự thêm. Client tốt đọc các header này và backoff có [[jitter|jitter]] (bài Timeout, retry, circuit breaker, bulkhead).
- **Chọn khoá**: theo API key hoặc tenant cho API thương mại (gắn với gói cước); theo user cho app; theo IP chỉ ở lớp chống lạm dụng trước khi xác thực, và lấy IP thật từ `X-Forwarded-For` của proxy tin cậy chứ không tin header từ client. Endpoint đắt (xuất báo cáo, tìm kiếm) có hạn mức riêng hoặc tính nhiều token mỗi request (`requestedTokens` của Spring Cloud Gateway).
- **Giới hạn đồng thời khác giới hạn tốc độ**: 10 request mỗi giây nhưng mỗi cái chạy 30 giây vẫn chiếm 300 luồng. Endpoint chạy lâu cần thêm giới hạn số request đang chạy (concurrency limiter); nhiều API thương mại lớn chạy hai loại này song song.
- **Giới hạn phía mình khi gọi đối tác**: đối tác cho 100 request mỗi giây cho cả công ty thì mọi pod phải chia nhau một bộ đếm chung, và hàng đợi phía mình (leaky bucket) mượt hơn là để đối tác trả `429` rồi retry.
- **Kiểm thử**: truyền đồng hồ vào thay vì gọi giờ hệ thống, để test burst, nạp lại và ranh giới cửa sổ không cần `sleep`. Theo dõi số `429` theo khoá: một khách hàng bị chặn liên tục là chuyện kinh doanh, không chỉ là kỹ thuật.
