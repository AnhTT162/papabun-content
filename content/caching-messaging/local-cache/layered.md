## Quick

[[local-cache|Local cache]] (Caffeine) nằm ngay trong heap của JVM: đọc mất cỡ **trăm nano giây**, không qua mạng, nhưng **mỗi pod một bản** và các bản có thể lệch nhau. [[multi-level-cache|Cache nhiều tầng]] đặt L1 trong JVM với TTL ngắn trước L2 là Redis: L1 gánh các key cực nóng, L2 dùng chung cho mọi pod. Invalidation giữa các pod gửi qua pub/sub hoặc Kafka, nhưng **luôn kèm TTL** vì tin có thể mất; độ cũ tệ nhất xấp xỉ TTL của L1 cộng độ cũ của L2.

## Interview

**Khi nào local cache đáng dùng**:
- Dữ liệu nhỏ, đọc rất nhiều, đổi ít: cấu hình, feature flag, danh mục, bảng quyền.
- Một [[hot-key|key nóng]] trong Redis bị đọc hàng chục nghìn lần mỗi giây, làm nghẽn một shard hoặc băng thông mạng.
- Cần latency dưới mili giây ở đường đọc chính.

**Cái giá**:
- Mỗi pod giữ một bản: 50 pod × 500MB cache là 25GB heap, và GC phải duyệt nhiều object sống hơn.
- Các pod lệch nhau: người dùng tải lại trang, rơi vào pod khác, thấy giá trị cũ rồi mới, rồi lại cũ.
- Deploy hay scale thêm pod là khởi động với L1 rỗng.

**Cache hai tầng**: đọc L1, miss thì đọc L2 (Redis), miss nữa thì database; ghi ngược lên các tầng. L1 có TTL ngắn (vài giây), L2 dài hơn.

**Invalidation giữa các pod**:
- **Chỉ TTL**: đơn giản nhất, chấp nhận lệch tới hết TTL.
- **Redis pub/sub**: pod sửa dữ liệu publish tên key sau commit, mọi pod nhận và xoá L1. Pub/sub là "bắn rồi quên": pod đang mất kết nối thì không bao giờ nhận lại tin đó.
- **Kafka**: mỗi pod một consumer group riêng; bền hơn nhưng nặng hơn.
- **[[client-side-caching|Client-side caching]] của Redis** (Redis 6+): server ghi nhớ client đã đọc key nào và chủ động gửi tin invalidation khi key đổi.

**Chọn theo dữ liệu**: mô tả sản phẩm chịu được vài giây cũ thì L1 hợp; giá và tồn kho dùng để chốt đơn thì đọc từ nguồn.

## Deep

- **Caffeine cơ bản**:
  - Luôn giới hạn kích thước: `maximumSize(10_000)`, hoặc `maximumWeight` kèm `weigher` khi giá trị to nhỏ khác nhau.
  - `expireAfterWrite` (TTL), `expireAfterAccess` (gia hạn khi đọc), hoặc `expireAfter(Expiry)` để mỗi mục một thời hạn riêng.
  - `refreshAfterWrite` cần `LoadingCache`, tải lại ngầm khi có lần đọc sau mốc thời gian và trả bản cũ trong lúc chờ.
  - `recordStats()` rồi xuất qua Micrometer để thấy hit ratio, eviction, thời gian tải; thiếu `recordStats` thì metric luôn bằng 0.
  - `expireAfter(Expiry)` không dùng chung được với `expireAfterWrite`/`expireAfterAccess` (lỗi ngay lúc build).
- **Tải đồng thời trong một JVM**: `cache.get(key, k -> load(k))` chỉ cho **một** thread tải mỗi key, các thread khác cùng key chờ kết quả. Vậy 50 pod cùng miss thì vẫn có 50 lần tải xuống Redis hoặc database: chống stampede trong JVM không thay được chống stampede toàn hệ thống.
- **Bẫy của `compute`**:
  - Hàm tải chạy trong lúc khoá một phần bảng băm bên trong; hàm tải chậm (gọi mạng) làm các key khác trong cùng phần đó cũng phải chờ. Hàm tải lâu thì dùng `AsyncLoadingCache` với executor riêng.
  - Hàm tải lại gọi `get` vào **cùng cache** cho key khác có thể gây deadlock hoặc `IllegalStateException: Recursive update`.
- **Soft và weak reference**: `softValues()` để GC tự dọn khi thiếu bộ nhớ nghe hấp dẫn, nhưng HotSpot chỉ dọn soft reference theo thời gian chưa truy cập so với heap còn trống (`-XX:SoftRefLRUPolicyMSPerMB`), tức khi heap đã căng, gây GC dài và hành vi khó đoán. Giới hạn kích thước tường minh luôn tốt hơn. `weakKeys()` đổi cách so sánh key thành `==`.
- **Spring Boot**: `spring.cache.type=caffeine` và `spring.cache.caffeine.spec=maximumSize=10000,expireAfterWrite=5m` áp cùng cấu hình cho mọi cache; cần cấu hình riêng từng cache thì tự khai báo `CaffeineCacheManager` hoặc nhiều bean. `refreshAfterWrite` trong spec cần một bean `CacheLoader`. Qua `@Cacheable` mà không có `sync = true` thì Spring đọc rồi `put` riêng, nên không có cơ chế một thread tải như `cache.get(key, loader)`. Spring không có sẵn cache hai tầng: tự viết một `Cache` bọc L1 và L2, hoặc dùng thư viện riêng.
- **Invalidation bằng Redis pub/sub chi tiết**:
  - Publish **sau commit** (bài Cache patterns), nội dung là key hoặc id, không phải giá trị.
  - Pod gửi tin cũng nhận lại tin của chính nó; xoá lại L1 của mình là vô hại.
  - Mất kết nối pub/sub thì sau khi kết nối lại nên xoá **toàn bộ** L1, vì không biết đã lỡ những tin nào.
  - Mỗi tin được gửi tới mọi pod: 100 pod × 1.000 lần sửa mỗi giây là 100.000 tin mỗi giây trên Redis. Gom tin theo lô, hoặc chỉ dùng L1 cho dữ liệu ít đổi.
  - Trong Redis Cluster, `PUBLISH` được lan tới mọi node qua cluster bus, chi phí tăng theo số node; Redis 7 có sharded pub/sub (`SPUBLISH`/`SSUBSCRIBE`) giới hạn tin trong một shard.
- **Kafka cho invalidation**: mỗi pod phải nhận mọi tin. Cách gọn là không dùng consumer group: `assign()` mọi partition, không commit offset, `seekToEnd` lúc khởi động (L1 vừa khởi động đã rỗng nên không cần tin cũ). Dùng `group.id` riêng theo tên pod cũng chạy, nhưng với Deployment mỗi lần khởi động lại sinh một group mới bị bỏ lại trong `__consumer_offsets`, còn với StatefulSet thì group đã có offset nên `auto.offset.reset=latest` không có tác dụng. Kafka không mất tin khi pod chập chờn trong thời gian retention, nhưng thêm độ trễ và một hệ thống phải vận hành.
- **Client-side caching của Redis**:
  - Bật bằng `CLIENT TRACKING ON`, cần RESP3 để nhận tin invalidation trên cùng connection (RESP2 thì chuyển hướng sang một connection pub/sub).
  - Chế độ mặc định: server nhớ key mà mỗi client đã đọc, tốn bộ nhớ phía server, giới hạn bởi `tracking-table-max-keys`. Bảng đầy thì server **giả như key bị sửa** và gửi invalidation để lấy lại chỗ: client mất cache mà không có lỗi nào. `OPTIN` kèm `CLIENT CACHING YES` chỉ theo dõi key client thật sự cache; `NOLOOP` không gửi lại tin cho thay đổi của chính client đó.
  - Chế độ `BCAST`: client đăng ký theo tiền tố key, server không cần nhớ từng key nhưng gửi nhiều tin hơn.
  - Client nhận tin rồi mới xoá, nên vẫn có khoảng lệch ngắn. Với chế độ hai connection (RESP2), tin invalidation có thể tới **trước** reply của `GET`, và client giữ giá trị cũ mãi; tài liệu Redis khuyên đặt giá trị tạm "đang tải" trước khi gửi lệnh. Dùng một connection RESP3 thì không có race này.
  - Vẫn đặt TTL tối đa cho mọi key phía client, PING định kỳ connection nhận invalidation, mất kết nối thì xoá toàn bộ cache cục bộ.
  - Client Java: Lettuce 6+ (`ClientSideCaching`, cần RESP3); Jedis 5.2+ (cần RESP3 và Redis 7.4+).
- **[[near-cache|Near cache]]** của data grid (Hazelcast, Ignite, Coherence) làm sẵn việc này: bản cục bộ cộng invalidation từ cluster.
- **Hibernate second-level cache** (qua JCache với Caffeine hay Ehcache) là một local cache cho entity: mỗi node một bản, không có invalidation giữa node nếu không dùng provider có cluster. Nó lưu trạng thái đã tách thành mảng giá trị chứ không lưu chính object entity, nên bẫy sửa object trong cache không áp dụng ở đây. Bulk update bằng HQL xoá cả region của entity liên quan; SQL native không khai báo bảng bị ảnh hưởng (`addSynchronizedEntityClass`) có thể làm xoá toàn bộ second-level cache. Query cache còn bị xoá mỗi khi bảng liên quan có ghi, nên thường hại nhiều hơn lợi với bảng ghi thường xuyên.
- **Giới hạn độ cũ**: với L1 TTL 5 giây và L2 TTL 60 giây (không có invalidation), một pod có thể trả dữ liệu cũ tới khoảng 65 giây: L2 giữ bản cũ 60 giây, rồi L1 vừa lấy bản cũ đó ở giây cuối giữ thêm 5 giây. Có invalidation cho L2 thì còn khoảng TTL của L1 cộng độ trễ của tin.
- **Khởi động và deploy**: rolling deploy 50 pod là 50 lần L1 rỗng; nếu L1 đang chặn một key cực nóng khỏi Redis, mỗi pod mới dội vào Redis. Làm nóng L1 cho các key quan trọng trước khi pod báo ready (readiness probe).
- **Sticky session** (gắn người dùng với một pod) giảm hiện tượng thấy dữ liệu đi lùi, nhưng làm phân phối tải lệch và mất tác dụng khi pod bị thay.
