## Quick

Spring Cache là một lớp trừu tượng: `@Cacheable`, `@CachePut`, `@CacheEvict` chạy qua **proxy** (nên dính [[self-invocation]]) và gọi `CacheManager` của provider thật (Caffeine, Redis). **Key mặc định chỉ dựa trên tham số**, [[ttl|TTL]] và cách serialize nằm ở provider chứ không ở annotation. Và **[[local-cache|cache trong JVM]] trả về chính object đang nằm trong cache**: sửa nó là sửa dữ liệu của mọi người, nên giá trị cache phải [[immutable|bất biến]].

## Interview

**Các annotation**:
- `@Cacheable("products")`: có trong cache thì trả luôn, không thì chạy method rồi lưu kết quả.
- `@CachePut`: luôn chạy method rồi ghi đè cache, dùng sau khi cập nhật.
- `@CacheEvict`: xoá một key, hoặc `allEntries = true`.
- `@Caching` gom nhiều thao tác; `@CacheConfig` đặt tên cache chung cho class.
- Cần `@EnableCaching`. Boot chọn `CacheManager` theo thư viện trên classpath, hoặc theo `spring.cache.type`.

**Key**:
- Một tham số thì key là chính tham số đó; nhiều tham số thì là `SimpleKey(a, b)`; không tham số thì là `SimpleKey.EMPTY`.
- Hai method khác nhau dùng chung tên cache và cùng kiểu tham số sẽ đè key của nhau.
- Viết key rõ bằng SpEL: `key = "#tenantId + ':' + #id"`. Key phải chứa mọi thứ làm kết quả khác đi (bài Cache là gì & cache ở đâu).

**`condition` và `unless`**: `condition` xét **trước** khi gọi, chỉ dùng tham số; `unless` xét **sau**, dùng được `#result`, ví dụ `unless = "#result == null"` để không cache kết quả rỗng.

**TTL và serialize**:
- Annotation không có TTL. Đặt ở provider: `RedisCacheConfiguration.entryTtl(...)` hay `spring.cache.redis.time-to-live`, `expireAfterWrite` của Caffeine.
- Với Redis ([[distributed-cache|cache dùng chung]]), serializer mặc định của `RedisCacheManager` là Java serialization: đổi class là đọc lỗi sau khi deploy. Nên cấu hình serializer JSON.

**Bẫy hay gặp**:
- Cache trong JVM (Caffeine, `ConcurrentMapCache`) giữ **tham chiếu**. Caller sửa object nhận được là sửa luôn bản trong cache (xem lab). Redis luôn trả bản sao mới deserialize, nên lỗi này hay lộ ra khi chuyển từ Redis sang Caffeine.
- Redis lỗi thì mặc định exception bay ra và request lỗi theo, dù database vẫn khoẻ; không đặt `spring.data.redis.timeout` thì Lettuce chờ tới 60 giây mỗi lệnh. Đặt timeout ngắn và khai báo `CacheErrorHandler` để chỉ log và đọc thẳng từ nguồn.

## Deep

- **`sync = true`**: chỉ một thread trong JVM tải key đang miss, các thread khác chờ (giúp chống stampede trong một instance). Không dùng chung được với `unless`, chỉ cho phép một cache trong annotation, và không kết hợp với thao tác cache khác trên cùng method.
- **Giá trị `null`**: Caffeine và Redis trong Spring mặc định cache cả `null`, nên id không tồn tại cũng được cache (tốt cho chống [[cache-penetration|penetration]], xem bài Stampede, penetration, avalanche, hot key). Tắt bằng `disableCachingNullValues()` với Redis hay `allowNullValues = false` với Caffeine thì phải kèm `unless = "#result == null"`; nếu không, method trả `null` sẽ ném `IllegalArgumentException` vì cache từ chối lưu `null`. `Optional` được mở ra: cache lưu giá trị bên trong hoặc `null`.
- **Kiểu trả về bất đồng bộ**: từ Spring 6.1, `@Cacheable` hỗ trợ `CompletableFuture` và kiểu reactive (`Mono`, `Flux`) với provider có API bất đồng bộ: Caffeine cần `CaffeineCacheManager.setAsyncCacheMode(true)`. Kết quả `Flux` được gom thành `List` rồi mới lưu. Bản cũ hơn sẽ cache chính object `CompletableFuture` hoặc `Mono`, không phải kết quả.
- **Mỗi cache một cấu hình**: `spring.cache.caffeine.spec` áp chung cho mọi cache. Cache khác TTL, khác kích thước thì khai báo bằng `RedisCacheManagerBuilderCustomizer` hoặc `CaffeineCacheManager.registerCustomCache`.
- **Key trong Redis**: mặc định dạng `tên-cache::key`. Thêm tiền tố theo service (`prefixCacheNameWith("svc:")` hoặc `computePrefixWith(...)`) để hai ứng dụng dùng chung Redis không đè key của nhau. `@CacheEvict(allEntries = true)` mặc định dùng `KEYS` theo pattern, lệnh chặn cả Redis khi có nhiều key; chuyển sang `RedisCacheWriter.nonLockingRedisCacheWriter(factory, BatchStrategies.scan(1000))`.
- **Metric**: Boot gắn metric `cache.gets` (tag `result=hit/miss`) cho các cache biết lúc khởi động. Caffeine cần `recordStats` trong spec, Redis cần `spring.cache.redis.enable-statistics=true`, mới có số liệu. Cache tạo động lúc chạy không có metric trừ khi tự đăng ký.
- **Thứ tự với transaction**: `@CacheEvict` trên method `@Transactional` có thể xoá cache trước khi commit, để request khác nạp lại dữ liệu cũ. Dùng `TransactionAwareCacheManagerProxy`, hoặc evict sau commit (bài Cache patterns).
- **Tên tham số trong SpEL**: `#id` cần biên dịch với `-parameters` (từ Spring 6.1, áp cho mọi class; Boot bật sẵn); nếu không thì dùng `#p0` hay `#a0`.
- **Không dùng Spring Cache khi**: cần đọc-ghi theo kiểu riêng (hot key, giá trị lớn chia nhỏ, cache nhiều tầng có invalidation qua pub/sub), hoặc cần biết chính xác hit/miss trong code. Khi đó gọi thẳng API của Caffeine hoặc Redis rõ ràng hơn là ép vào annotation.
