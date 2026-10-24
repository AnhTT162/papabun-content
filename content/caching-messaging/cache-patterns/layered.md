## Quick

**[[cache-aside|Cache-aside]]** là pattern phổ biến nhất: đọc thì hỏi cache trước, miss thì đọc database rồi ghi vào cache; ghi thì **cập nhật database rồi xoá cache** (không cập nhật cache), và xoá **sau khi commit**. Pattern nào cũng có khoảng thời gian cache lệch với database, nên **luôn đặt TTL** làm giới hạn trên cho độ cũ. [[read-through|Read-through]] và [[write-through|write-through]] để thư viện cache tự đọc ghi nguồn; [[write-behind|write-behind]] ghi database sau, nhanh nhưng có thể mất dữ liệu.

## Interview

**Cache-aside (lazy loading)**: ứng dụng tự quản lý cache.
- Đọc: `get(key)`; miss thì đọc database, `set(key, value, ttl)`.
- Ghi: cập nhật database, rồi xoá `key`.

Chỉ dữ liệu được đọc mới vào cache, và cache sập thì hệ thống vẫn chạy (chậm hơn).

**Vì sao xoá thay vì cập nhật cache**: hai request ghi đồng thời có thể cập nhật database theo thứ tự A rồi B, nhưng cập nhật cache theo thứ tự B rồi A: cache giữ giá trị của A tới khi TTL hết, hoặc mãi nếu không đặt TTL. Xoá thì lần đọc sau luôn lấy bản mới nhất từ database. Cập nhật cache còn tốn công tính lại giá trị mà có thể không ai đọc.

**Thứ tự sai hay gặp**:
- Xoá cache trước rồi mới ghi database: trong khoảng giữa, một request đọc database cũ và ghi lại vào cache.
- Xoá cache bên trong transaction: người khác đọc database (chưa commit, vẫn bản cũ) và ghi lại cache. Phải xoá **sau commit**.
- Miss rồi đọc từ **read replica** còn trễ: bản cũ lại vào cache dù đã xoá đúng lúc. Khi miss thì đọc từ primary, hoặc đặt lần xoá thứ hai trễ hơn replica lag.

**Race còn lại của cache-aside**: request đọc lấy bản cũ từ database, bị chậm; trong lúc đó request ghi cập nhật database và xoá cache; request đọc ghi bản cũ vào cache. Hiếm nhưng có thật. Giảm bằng TTL, xoá lần hai sau vài trăm mili giây, hoặc ghi kèm phiên bản.

**Các pattern khác**:
- **Read-through**: cache tự gọi loader khi miss (Caffeine `LoadingCache`).
- **Write-through**: ghi qua cache, cache ghi đồng bộ xuống database.
- **Write-behind**: ghi vào cache rồi trả về ngay, ghi xuống database theo lô sau. Nhanh, giảm tải ghi, nhưng cache chết trước khi kịp ghi là mất dữ liệu; hợp với bộ đếm lượt xem, không hợp với đơn hàng.
- **[[refresh-ahead|Refresh-ahead]]**: làm mới mục nóng trước khi hết hạn.

## Deep

- **Xoá sau commit trong Spring**:
  - `@CacheEvict` trên method `@Transactional` xoá khi method trả về, có thể **trước** khi transaction commit, tuỳ thứ tự của hai advice.
  - Bọc cache bằng `TransactionAwareCacheDecorator` (hoặc `RedisCacheManager.builder(...).transactionAware()`) để `put` và `evict` được hoãn tới sau commit.
  - Hoặc phát event và xoá trong `@TransactionalEventListener` (pha mặc định là `AFTER_COMMIT`). Bẫy: publish khi không có transaction thì listener **không chạy** trừ khi đặt `fallbackExecution = true`; exception trong listener không rollback được gì nên phải log hoặc retry.
  - Decorator chỉ hoãn `put`, `evict`, `clear`; các thao tác tức thời (`putIfAbsent`, `evictIfPresent`, tức cả `@CacheEvict(beforeInvocation = true)`) vẫn chạy ngay.
  - Gọi method có `@CacheEvict` từ chính class đó không qua proxy nên không xoá gì ([[self-invocation|self-invocation]]). `@Cacheable` thực chất là cache-aside do framework làm hộ.
  - Ghi database rồi xoá cache bản chất là [[dual-write|dual write]]: xoá lỗi (Redis timeout) sau khi đã commit thì cache cũ tới hết TTL. Log, retry ngắn, hoặc đẩy key cần xoá vào queue.
- **Xoá hai lần (delayed double delete)**: xoá ngay sau commit, rồi xoá thêm một lần sau khoảng bằng thời gian một lần đọc database chậm (vài trăm mili giây), để bắt race của request đọc chậm. Giảm khả năng chứ không loại bỏ hẳn.
- **Ghi kèm phiên bản**: giá trị trong cache mang `version` (cột `@Version` hoặc LSN; tránh `updated_at` vì lệch đồng hồ và độ phân giải thấp). Khi ghi database xong, thay vì xoá hẳn thì ghi một tombstone ngắn hạn "đã đổi ở version N". Lua script khi điền cache chỉ `SET` nếu version mang theo **lớn hơn hoặc bằng** N của tombstone và lớn hơn version đang có. Request đọc chậm mang bản cũ hơn N bị chặn, còn request đọc đúng bản N vẫn điền lại được.
- **Lease**: khi miss, cache cấp cho request một token; chỉ request giữ token mới được ghi, và lệnh xoá huỷ mọi token đang có. Request đọc chậm mang token đã bị huỷ thì không ghi được. Đây là cách các hệ thống memcache rất lớn chặn cả race lẫn stampede; Redis không có sẵn, phải tự làm bằng Lua.
- **Invalidation qua [[cdc|CDC]]**: thay vì code ứng dụng tự xoá, một consumer đọc [[wal|WAL]] hoặc [[binlog|binlog]] (Debezium) và xoá key tương ứng với mỗi dòng đổi. Không bỏ sót đường ghi nào (script tay, service khác, migration), và luôn xảy ra sau commit. Đổi lại: trễ thêm cỡ trăm mili giây tới vài giây, và phải ánh xạ được từ dòng database sang mọi cache key liên quan. Race của request đọc chậm vẫn có thể xảy ra, chỉ hiếm hơn, vì độ trễ của CDC hoạt động như một lần xoá trễ.
- **[[cache-invalidation|Invalidation]] cho danh sách và trang tổng hợp**: một sản phẩm đổi giá ảnh hưởng tới trang danh mục, kết quả tìm kiếm, trang khuyến mãi... không thể liệt kê hết key.
  - TTL ngắn cho các key tổng hợp và chấp nhận độ cũ.
  - Namespace có phiên bản: key là `catalog:{categoryId}:v{n}:page:3`; đổi dữ liệu của danh mục thì tăng `n` của danh mục đó (một lệnh `INCR`), toàn bộ key cũ tự thành rác và hết hạn theo TTL. Cái giá: mỗi request thêm một lần đọc `n`, và key phiên bản trở thành key nóng; một `n` chung cho mọi danh mục thì đổi một sản phẩm là mất cache của tất cả.
  - Cache theo id, còn danh sách chỉ cache danh sách id; lấy chi tiết từng id qua cache theo id (`MGET`).
- **Write-through chi tiết**: lần ghi đi qua cache, cache ghi xuống database rồi mới trả về; dữ liệu trong cache luôn mới nhưng mọi lần ghi chậm thêm, và cache phải nằm trên đường ghi của mọi bên ghi. Thường gặp trong data grid (Hazelcast với `MapStore`, Ignite với `CacheStore`) hơn là với Redis. Với Hazelcast, `write-delay-seconds = 0` (mặc định) là write-through, lớn hơn 0 là write-behind.
- **Write-behind chi tiết**: ghi gộp cho các giá trị đổi liên tục (lượt xem, vị trí xe), xả xuống database mỗi vài giây theo lô. Phải chấp nhận mất phần chưa xả khi node chết, và database không phải nguồn sự thật trong khoảng đó; đọc trực tiếp từ database sẽ thấy số cũ.
- **Refresh-ahead**: Caffeine `refreshAfterWrite` tải lại ngầm khi mục được đọc sau mốc thời gian, trả bản cũ trong lúc chờ; với Redis thì một job làm mới các key nóng trước khi TTL hết. Chỉ đáng làm cho key được đọc rất nhiều; làm cho mọi key là tốn tải vô ích.
- **Cache khởi động lạnh**: deploy cụm Redis mới hoặc xoá toàn bộ cache làm miss 100%, database có thể không chịu nổi. Làm nóng trước (warm-up) cho key nóng, hoặc chuyển dần lưu lượng. Bài Stampede, penetration, avalanche, hot key đi sâu.
- **Serialize**: với value của cache và `RedisTemplate`, Spring Data Redis mặc định dùng serialization của JDK (key là String): chậm, khó đọc bằng `redis-cli`, và hỏng khi đổi class. Dùng JSON (`GenericJackson2JsonRedisSerializer` ở Boot 3, `GenericJacksonJsonRedisSerializer` ở Boot 4) hoặc định dạng nhị phân có schema, kèm phiên bản trong key. Serializer "Generic" nhúng tên class vào dữ liệu, nên đổi tên hay chuyển package class là đọc lỗi, và kiểu được phép deserialize phải giới hạn để tránh lỗ hổng.
- **Cái giá của sự đúng**: không pattern nào cho cache luôn khớp database nếu không có transaction chung. Nếu một luồng nghiệp vụ không chịu được dữ liệu cũ (kiểm tra tồn kho khi chốt đơn, số dư khi trừ tiền), nó phải đọc từ database, không qua cache.
