## Quick

[[cache|Cache]] giữ bản sao của dữ liệu ở chỗ **gần hơn và nhanh hơn** nguồn gốc, đánh đổi **độ mới** lấy **tốc độ** và giảm tải cho nguồn. Hiệu quả đo bằng **[[cache-hit-ratio|hit ratio]]**; dữ liệu cũ được giới hạn bằng **[[ttl|TTL]]**; khi đầy thì bỏ bớt theo chính sách **[[cache-eviction|eviction]]** như [[lru|LRU]] hay [[lfu|LFU]]. Một request có thể đi qua nhiều tầng cache: trình duyệt, CDN, gateway, ứng dụng, Redis, rồi buffer pool của database.

## Interview

**Cache là gì**: bản sao dữ liệu đặt ở nơi đọc nhanh hơn: RAM thay vì đĩa, cùng process thay vì qua mạng, gần người dùng thay vì ở data center. Nó có ích khi dữ liệu **được đọc nhiều hơn ghi** và **chấp nhận được việc hơi cũ**.

**Hit ratio** là tỉ lệ lần đọc tìm thấy trong cache. Latency trung bình xấp xỉ `hit × t_cache + miss × t_nguồn`. Cache 1ms, database 50ms:
- 90% hit: 0,9 + 5 = 5,9ms.
- 99% hit: 0,99 + 0,5 ≈ 1,5ms, nhanh gấp 4 lần, và tải xuống database giảm 10 lần.

**TTL** là thời gian sống của một mục: hết hạn thì lần đọc sau lấy lại từ nguồn. TTL ngắn thì dữ liệu mới hơn nhưng miss nhiều hơn. Muốn dữ liệu đổi là thấy ngay thì phải chủ động xoá hoặc cập nhật cache (bài Cache patterns).

**Eviction** khi cache đầy:
- LRU bỏ mục lâu nhất chưa được dùng.
- LFU bỏ mục ít được dùng nhất.
- Caffeine dùng W-TinyLFU, kết hợp cả hai, nên chịu được một đợt quét lớn mà không xoá hết mục nóng.

**Các tầng cache**:
- Trình duyệt và CDN: theo header HTTP `Cache-Control`, `ETag`.
- Gateway, reverse proxy: cache response.
- [[local-cache|Local cache]] trong JVM (Caffeine): nhanh nhất, nhưng mỗi instance một bản riêng.
- [[distributed-cache|Distributed cache]] (Redis): dùng chung, tốn một vòng mạng.
- Buffer pool của database: cache page.

**Bẫy hay gặp**:
- [[cache-key|Cache key]] thiếu tenant hay ngôn ngữ làm lộ dữ liệu.
- Cache dữ liệu cá nhân ở CDN.
- Không cache kết quả rỗng nên id không tồn tại lần nào cũng đi xuống database.
- Cache to dần trong heap gây GC.

## Deep

- **HTTP caching** ([[http-caching|RFC 9111]]):
  - `Cache-Control: max-age=60` cho phép mọi cache dùng lại response 60 giây; `s-maxage` ghi đè `max-age` cho cache dùng chung (CDN, proxy).
  - `private` cấm cache dùng chung giữ response (dữ liệu của riêng người dùng); `public` cho phép.
  - `no-cache` **vẫn lưu** nhưng phải hỏi lại server trước khi dùng; `no-store` mới là không lưu.
  - Hỏi lại có điều kiện: server trả [[etag|`ETag`]], lần sau client gửi `If-None-Match`; không đổi thì server trả `304 Not Modified` không kèm body.
  - `stale-while-revalidate=30` (phần mở rộng, RFC 5861): sau khi hết `max-age`, cho dùng bản cũ thêm 30 giây trong lúc cập nhật ngầm, nên người dùng không phải chờ. Không phải cache nào cũng hỗ trợ.
  - `Vary: Accept-Language` báo cache rằng response khác nhau theo header đó. Vary theo header có quá nhiều giá trị (`User-Agent`, `Cookie`) làm hit ratio gần như bằng 0. Nhiều CDN mặc định bỏ qua `Vary` (trừ `Accept-Encoding`) và dùng cache key theo cấu hình riêng, thường chỉ gồm host, đường dẫn và có thể cả query; cookie không nằm trong key. Đừng dựa vào `Vary` để tách dữ liệu ở CDN.
- **Response cho request có `Authorization`** không được cache dùng chung lưu và dùng lại, trừ khi response có `public`, `s-maxage` hoặc `must-revalidate`. Nhưng nhiều CDN cho phép cấu hình ghi đè quy tắc này, và cookie phiên không phải `Authorization`: đường dẫn trả dữ liệu cá nhân phải luôn gửi `private` hoặc `no-store`.
- **Cache trong database**: buffer pool của InnoDB và `shared_buffers` của PostgreSQL cache page. PostgreSQL dựa thêm vào page cache của hệ điều hành (dữ liệu được đệm hai lần), nên `shared_buffers` thường chỉ khoảng 25% RAM; InnoDB từ 8.4 mặc định `O_DIRECT` trên Linux, tự quản lý gần hết, nên buffer pool thường đặt 50–75% RAM. MySQL từng có query cache (cache theo nguyên văn câu SQL), đã bỏ ở 8.0 vì mọi lần ghi vào bảng đều xoá cache của bảng đó và nó trở thành điểm tranh chấp lock.
- **Local cache trong JVM**:
  - Caffeine giới hạn theo số mục (`maximumSize`) hoặc theo trọng số (`maximumWeight` kèm `weigher`, ví dụ theo byte). Không giới hạn là memory leak có chủ đích.
  - Cache lớn trong heap làm GC phải duyệt nhiều object sống hơn; hàng triệu mục nhỏ đắt hơn ít mục lớn.
  - `expireAfterWrite` là TTL tính từ lúc ghi; `expireAfterAccess` gia hạn mỗi lần đọc, nên mục được đọc liên tục có thể không bao giờ được làm mới; `refreshAfterWrite` (cần `LoadingCache`) tải lại ngầm khi có lần đọc sau mốc thời gian, không chạy định kỳ, trong lúc đó vẫn trả bản cũ; thường kết hợp với `expireAfterWrite` dài hơn để mục ít được đọc vẫn hết hạn.
  - Mỗi instance có bản riêng: 20 pod là 20 bản có thể lệch nhau. Chi tiết ở bài Local & multi-level cache.
- **W-TinyLFU** của Caffeine: mục mới phải "thắng" mục sắp bị bỏ theo tần suất ước lượng mới được vào vùng chính, nên một đợt quét đọc hàng triệu id một lần không đẩy được mục nóng ra như với LRU thuần.
- **Eviction của Redis**: `maxmemory-policy` mặc định là `noeviction`, tức đầy thì lệnh ghi báo lỗi `OOM command not allowed`. Dùng làm cache thì đặt `allkeys-lru` hoặc `allkeys-lfu`; `volatile-*` chỉ bỏ key có TTL. LRU và LFU của Redis là **xấp xỉ** theo mẫu vài key (bài Redis bên trong).
- **[[negative-caching|Negative caching]]**: cache cả kết quả "không tồn tại" với TTL ngắn, để id sai hay bị tấn công dò không đi thẳng xuống database. Phải xoá mục này khi dữ liệu được tạo.
- **Thiết kế cache key**:
  - Chứa mọi chiều làm kết quả khác đi (tenant, ngôn ngữ, quyền nếu kết quả lọc theo quyền).
  - Có tiền tố theo loại và phiên bản, ví dụ `v3:product:{tenant}:{id}`: đổi cấu trúc object thì tăng phiên bản, không phải đọc nhầm dữ liệu kiểu cũ đã serialize.
  - Key dài tốn bộ nhớ ở Redis; giá trị lớn (vài MB) làm chậm mọi lệnh khác vì Redis xử lý lệnh tuần tự.
- **Spring Cache**: `@Cacheable("products")` dùng tham số làm key mặc định. Nó chạy qua proxy, nên gọi method có `@Cacheable` từ chính class đó không đi qua cache ([[self-invocation|self-invocation]]), giống `@Transactional`. `@CacheEvict` khi sửa; `sync = true` để nhiều thread cùng miss một key chỉ một thread tải, nhưng với Caffeine chỉ trong **một instance**: 20 pod cùng miss vẫn là 20 lần tải; với Redis, tác dụng tuỳ phiên bản Spring Data Redis (bài Stampede, penetration, avalanche, hot key). Key mặc định chỉ dựa trên tham số, không có tên method: `findById(Long id)` và `findPriceById(Long id)` cùng cache `products` sẽ đè key của nhau và trả nhầm kiểu; dùng tên cache riêng hoặc `key = "'price:' + #id"`.
- **Khi nào không nên cache**:
  - Dữ liệu ghi nhiều hơn đọc, hoặc mỗi giá trị chỉ được đọc một lần.
  - Dữ liệu phải luôn chính xác tuyệt đối tại thời điểm đọc (số dư khi trừ tiền, tồn kho khi chốt đơn): đọc từ nguồn, cache chỉ dùng để hiển thị.
  - Khi chậm là do query thiếu index: sửa query trước, cache sau.
- **Đo**: hit ratio theo từng cache (không chỉ tổng), số lần eviction, bộ nhớ dùng, latency của lần miss. Caffeine bật `recordStats()`; Spring Boot Actuator xuất các số này qua Micrometer.
