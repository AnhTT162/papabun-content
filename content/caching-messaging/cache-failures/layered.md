## Quick

Cache giảm tải cho database, nên khi cache **không đỡ được** thì toàn bộ tải dội thẳng xuống database. Bốn kiểu sự cố hay gặp:
- **[[cache-stampede|Stampede]]**: một key nóng hết hạn, hàng trăm request cùng miss và cùng query một thứ.
- **[[cache-penetration|Penetration]]**: request hỏi key **không tồn tại**, cache không bao giờ có nên lần nào cũng xuống database.
- **[[cache-avalanche|Avalanche]]**: rất nhiều key hết hạn cùng lúc, hoặc cả cụm cache sập.
- **[[hot-key|Hot key]]**: một key bị đọc nhiều tới mức làm quá tải shard chứa nó.

Cách chữa tương ứng: chỉ một request tải lại và làm mới sớm; cache cả kết quả "không có" và dùng [[bloom-filter|Bloom filter]]; rải TTL ngẫu nhiên và giới hạn tải xuống database; thêm cache trong JVM cho key nóng.

## Interview

**Stampede**:
- Trong một JVM: [[single-flight|single-flight]], chỉ một thread tải mỗi key (Caffeine `get(key, loader)`, hoặc `@Cacheable(sync = true)` trên Caffeine). Với 50 pod vẫn còn 50 query. Trên `RedisCache` thì `sync = true` không chắc có tác dụng: tuỳ phiên bản Spring Data Redis.
- Giữa các pod: lock ngắn trên Redis (`SET lock:k token NX PX 5000`); bên thua chờ một chút rồi đọc lại cache, hoặc trả bản cũ.
- Tốt hơn là không để key nóng hết hạn lúc có tải: [[logical-expiration|hết hạn logic]] (lưu kèm thời điểm hết hạn mềm, một request làm mới nền, các request khác vẫn nhận bản cũ), hoặc [[probabilistic-early-expiration|làm mới sớm theo xác suất]].

**Penetration**:
- Kiểm tra định dạng đầu vào trước khi tra (id âm, sai định dạng).
- [[negative-caching|Negative caching]]: lưu "không có" với TTL ngắn, 30–60 giây.
- Kẻ tấn công gửi hàng triệu id ngẫu nhiên thì negative cache phình và vẫn miss: đặt Bloom filter chứa mọi id có thật trước cache, và [[rate-limiting|giới hạn tần suất]] theo client.

**Avalanche**:
- TTL cộng thêm phần ngẫu nhiên ([[ttl-jitter|jitter]]) 10–20%, nhất là với dữ liệu được nạp hàng loạt.
- Cụm cache sập: timeout ngắn cho Redis client, circuit breaker để không chờ Redis đã chết, giới hạn số query đồng thời xuống database ([[bulkhead|bulkhead]]), chấp nhận trả lỗi hoặc dữ liệu rút gọn cho một phần request thay vì để database sập theo.
- Làm nóng cache trước khi đưa cụm mới vào phục vụ.

**Hot key**: cache trong JVM, làm mới mỗi vài giây, trước Redis, hoặc nhân key thành nhiều bản trên nhiều shard (bài Local & multi-level cache).

**Điểm chung**: database phải được bảo vệ kể cả khi cache hỏng hoàn toàn. Đo số query xuống database theo từng loại key, không chỉ hit ratio trung bình.

## Deep

- **Lock phân tán chống stampede**:
  - `SET lock:product:42 <token> NX PX 5000`: chỉ một request thắng. Thời gian giữ lock phải dài hơn thời gian tải tệ nhất; quá ngắn thì lock hết hạn giữa chừng và request khác cũng vào tải.
  - Nhả lock bằng Lua so token (`if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) end`), để không xoá nhầm lock của request khác.
  - Bên thua: ngủ ngắn (20–50ms) rồi đọc lại cache, giới hạn số lần thử; hết lượt thì trả bản cũ hoặc lỗi, **không** tự tải, nếu không lock chẳng còn tác dụng.
  - Đây chỉ là lock để giảm tải, mất lock thì chỉ tốn thêm vài query; không dùng nó để bảo vệ tính đúng đắn của dữ liệu (bài Distributed lock).
- **Hết hạn logic**:
  - Giá trị lưu `{data, softExpireAt}`, TTL thật của Redis dài hơn nhiều (ví dụ mềm 5 phút, cứng 1 giờ).
  - Đọc thấy quá `softExpireAt`: thử lấy lock làm mới; thắng thì tải nền và ghi lại, mọi request (kể cả bên thắng) trả bản cũ ngay.
  - Không request nào phải chờ database; đổi lại dữ liệu có thể cũ thêm một chu kỳ tải. Caffeine `refreshAfterWrite` làm đúng việc này trong một JVM.
- **Làm mới sớm theo xác suất (XFetch)**:
  - Mỗi lần đọc, tính lại sớm nếu `now - delta * beta * ln(random()) >= expiry`; `delta` là thời gian tải lần trước, `beta` thường 1, `random()` trong (0, 1] nên `-ln(random())` dương. Trong Java, `Math.random()` trả về [0, 1), nên dùng `1 - Math.random()` để tránh `ln(0)`.
  - Càng gần hạn xác suất càng tăng, và key tải lâu (delta lớn) được làm mới sớm hơn. Không cần lock, nhưng không đảm bảo chỉ một request tải: phù hợp key đọc nhiều với chi phí tải vừa phải.
  - Cần lưu `delta` cùng giá trị và biết `expiry` (đọc bằng `PTTL` hoặc lưu kèm).
- **`@Cacheable(sync = true)` phụ thuộc cache provider**:
  - Caffeine: một thread tải mỗi key, trong một JVM.
  - Spring Data Redis tới 3.3: một khoá JVM cho **cả cache** (không theo key): một lần tải chậm chặn mọi lần miss khác của cache đó, và không khoá giữa các pod.
  - Spring Data Redis 3.4+: việc khoá giao cho `RedisCacheWriter`. Writer mặc định (`nonLockingRedisCacheWriter`) **không khoá gì**, nên mọi request miss vẫn tải. `lockingRedisCacheWriter` dùng một khoá trên Redis cho cả cache (`<tên cache>~lock`): chặn được stampede giữa các pod nhưng tuần tự hoá mọi lần miss của cache đó.
  - Kết luận: đừng tin `sync = true` trên Redis; chống stampede bằng L1 Caffeine, lock theo key tự viết, hoặc hết hạn logic.
  - Không kết hợp được với `unless`. Spring Framework 6.1 thêm hỗ trợ cache bất đồng bộ (`CompletableFuture`, Reactor) cho cùng thuộc tính này.
- **Bloom filter**:
  - Trả lời "chắc chắn không có" hoặc "có thể có"; tỉ lệ dương tính giả 1% tốn khoảng 9,6 bit mỗi phần tử: 10 triệu id khoảng 12MB.
  - Redis 8 có sẵn kiểu dữ liệu xác suất (`BF.RESERVE`, `BF.ADD`, `BF.EXISTS`); bản cũ hơn cần module RedisBloom. Trong JVM có Guava `BloomFilter`, nhưng mỗi pod phải tự nạp và cập nhật.
  - **Thứ tự cập nhật**: id mới phải được thêm vào filter **trước** khi trả về cho người dùng; nếu không, đọc ngay sau khi tạo sẽ bị filter chặn là "không có" (âm tính giả do chưa cập nhật).
  - Trên Redis Cluster, một filter là **một key** nằm trên một shard, và mọi request đều gọi `BF.EXISTS` vào nó: chính nó thành hot key. Chia filter thành nhiều key theo hash của id, hoặc giữ bản sao trong JVM.
  - Bloom filter không xoá được phần tử: id bị xoá vẫn "có thể có" và rơi xuống negative cache. Dựng lại định kỳ từ database, hoặc dùng cuckoo filter (`CF.*`) nếu cần xoá.
- **Negative caching cẩn thận**:
  - TTL ngắn, và **xoá entry "không có" khi tạo bản ghi**, nếu không bản ghi mới bị coi là không tồn tại tới hết TTL.
  - Phân biệt "không tồn tại" với "lỗi khi tra": không cache kết quả lỗi hoặc timeout như là "không có".
- **Jitter và nạp hàng loạt**:
  - `ttl = base + random(0, base * 0.2)`. Job nạp 2 triệu key trong 5 phút với cùng TTL thì đúng chu kỳ sau 2 triệu key hết hạn trong 5 phút.
  - Job làm mới định kỳ nên **ghi đè** giá trị mới trước khi key cũ hết hạn, thay vì xoá rồi chờ request tải lại.
  - Đổi định dạng key (`product:v2:`) trong một lần deploy cũng tạo cache lạnh toàn bộ: deploy ngoài giờ cao điểm hoặc ghi song song cả hai phiên bản trước.
- **Cache sập hoặc chậm**:
  - Timeout của Redis client khoảng 50–200ms. Timeout mặc định dài (Jedis 2 giây, Lettuce 60 giây) làm thread Tomcat bị giữ hết, và sự cố cache lan thành sự cố toàn hệ thống.
  - Lettuce mặc định tự kết nối lại và **xếp hàng lệnh** trong lúc mất kết nối (`disconnectedBehavior=DEFAULT`), nên mỗi lệnh chờ tới hết timeout thay vì lỗi ngay. Đặt `ClientOptions.disconnectedBehavior(REJECT_COMMANDS)` cùng timeout ngắn để lỗi nhanh.
  - `SimpleCacheErrorHandler` mặc định của Spring **ném lại** lỗi cache, nên Redis lỗi là request trả 5xx chứ không đi xuống database. Muốn coi lỗi Redis như miss thì cấu hình `CachingConfigurer.errorHandler()` để log và bỏ qua.
  - Circuit breaker (Resilience4j) mở khi Redis lỗi nhiều, bỏ qua Redis và đi thẳng tới lớp bảo vệ database.
  - Lớp bảo vệ database: semaphore hoặc rate limiter cho đường tải lại cache, nhỏ hơn connection pool. Phần vượt quá trả lỗi nhanh (503) hoặc dữ liệu rút gọn (bỏ phần gợi ý sản phẩm), để database vẫn phục vụ được đường ghi và thanh toán.
  - L1 Caffeine với `refreshAfterWrite` ngắn và `expireAfterWrite` dài: khi làm mới lỗi, Caffeine giữ bản cũ, nên key nóng vẫn phục vụ được vài phút khi Redis sập.
- **Hot key ghi nhiều** (bộ đếm lượt xem): chia thành nhiều key `views:42:{0..15}`, `INCR` vào một key ngẫu nhiên và cộng lại khi đọc; hoặc gộp trong JVM rồi `INCRBY` mỗi giây.
- **Phát hiện**: `redis-cli --hotkeys` (cần policy LFU), `--bigkeys`, thống kê phía client theo tiền tố key; `MONITOR` làm Redis chậm đáng kể, không chạy lâu trên production. Cảnh báo theo số query tải lại cache mỗi giây và CPU, mạng của **từng** shard.
