## Quick

Redis có ba mức sẵn sàng cao:
- **Replication**: primary chép dữ liệu sang replica **bất đồng bộ**.
- **[[redis-sentinel|Sentinel]]**: theo dõi một primary và tự đưa replica lên khi primary chết. Không chia dữ liệu.
- **[[redis-cluster|Redis Cluster]]**: chia key vào **16.384 [[hash-slot|hash slot]]** trên nhiều master, mỗi master có replica, và tự failover.

Vì replication bất đồng bộ, **lệnh ghi đã được xác nhận vẫn có thể mất khi failover**. Redis là cache hoặc kho dữ liệu chấp nhận mất vài giây gần nhất, không phải database ghi sổ.

## Interview

**Replication**:
- Replica kết nối, nhận bản RDB (full sync), rồi nhận luồng lệnh ghi.
- Mất kết nối ngắn thì nối tiếp từ [[replication-backlog|replication backlog]] (partial resync); backlog không đủ thì full sync lại.
- Primary trả lời client **trước** khi replica nhận lệnh.

**Sentinel**:
- Ít nhất 3 Sentinel trên các máy khác nhau.
- `quorum` Sentinel đồng ý thì primary bị coi là chết; cần **đa số** Sentinel bầu thì mới được failover.
- Client hỏi Sentinel địa chỉ primary hiện tại, nên phải dùng client hiểu Sentinel.

**Cluster**:
- Slot của key là `CRC16(key) mod 16384`. Client giữ bảng slot → node; gửi nhầm node thì nhận `MOVED` kèm địa chỉ đúng.
- Lệnh nhiều key, transaction và Lua chỉ chạy khi mọi key khai báo cùng slot (lỗi `CROSSSLOT`). Dùng [[hash-tag|hash tag]] `{user:42}` để ép các key liên quan vào một slot.
- Failover: master bị đa số master khác coi là chết sau `cluster-node-timeout` (mặc định 15 giây), replica được bầu lên. Cần ít nhất 3 master.

**Mất dữ liệu khi nào**:
- Primary nhận ghi, chết trước khi replica có lệnh đó.
- Mạng chia đôi: phía kia đã bầu primary mới, còn primary cũ ở phía thiểu số vẫn nhận ghi ([[split-brain|split-brain]]). Cluster: nó ngừng nhận ghi sau `cluster-node-timeout`. Sentinel: nó nhận ghi tới khi mạng lành và bị hạ thành replica, trừ khi có `min-replicas-to-write`. Các ghi đó đều mất.
- `WAIT` (và `WAITAOF` từ 7.2) giảm khả năng mất, không biến Redis thành hệ nhất quán mạnh.

**Chọn**: dữ liệu vừa một máy và cần HA thì Sentinel hoặc dịch vụ managed. Dữ liệu hay throughput vượt một máy thì Cluster. Managed (ElastiCache, MemoryDB, Azure Managed Redis) xử lý failover cho bạn, nhưng ứng dụng vẫn phải chịu được vài giây lỗi.

## Deep

- **Full sync lặp mãi**: full sync gửi RDB rồi gửi phần lệnh ghi trong lúc đó qua output buffer của replica. Ghi nhiều làm buffer vượt `client-output-buffer-limit replica` (mặc định `256mb 64mb 60`), primary ngắt kết nối, replica full sync lại từ đầu, và cứ thế. Tăng giới hạn buffer và `repl-backlog-size` (mặc định chỉ 1MB) theo tốc độ ghi nhân thời gian đồng bộ.
- **Partial resync sau failover**: từ Redis 4.0 (PSYNC2), replica còn lại có thể nối tiếp với primary mới mà không full sync, nhờ primary mới nhớ replication ID cũ.
- **Primary tắt persistence và tự khởi động lại**: primary chết, được systemd hay Kubernetes khởi động lại ngay với dữ liệu **rỗng**, replica đồng bộ theo và xoá sạch bản của chúng. Nếu primary không bật persistence thì không cho tự khởi động lại nhanh hơn thời gian failover, hoặc bật persistence.
- **Chặn ghi khi mất replica**: `min-replicas-to-write 1` cùng `min-replicas-max-lag 10`: primary từ chối ghi khi không có replica nào theo kịp trong 10 giây. Thu hẹp khoảng mất dữ liệu khi split-brain, đổi lại mất khả năng ghi khi replica chết.
- **Đọc từ replica**:
  - Dữ liệu có thể cũ theo độ trễ replication; không đọc lại ngay sau khi ghi ([[read-your-writes|read-your-writes]]).
  - Replica không tự xoá key hết hạn, chờ primary gửi lệnh xoá; từ 3.2, đọc key đã quá hạn trên replica trả về rỗng.
  - Lettuce: `ReadFrom.REPLICA_PREFERRED`, hoặc `spring.data.redis.lettuce.read-from`.
- **Sentinel chi tiết**:
  - `down-after-milliseconds` là thời gian không phản hồi trước khi một Sentinel coi primary là chết (SDOWN); đủ `quorum` thì thành ODOWN; một Sentinel được đa số bầu làm leader để failover.
  - Đặt Sentinel cạnh ứng dụng hoặc ở vùng thứ ba, không đặt cả 3 cùng máy với Redis.
  - Failover thường mất vài giây tới vài chục giây; client phải retry, và connection cũ trỏ tới primary cũ phải được đóng.
- **Cluster chi tiết**:
  - Node nói chuyện qua cluster bus (mặc định cổng dữ liệu + 10000, từ 7.0 đặt bằng `cluster-port`) bằng gossip.
  - Chuyển slot (resharding): slot ở trạng thái MIGRATING/IMPORTING; key đã chuyển thì client nhận `ASK`, gửi `ASKING` rồi lệnh tới node mới **một lần**, không cập nhật bảng.
  - `cluster-require-full-coverage yes` (mặc định): một slot không có master nào phục vụ là **cả cluster** từ chối lệnh. Đặt `no` để các slot còn lại vẫn chạy.
  - Redis Cluster chỉ có database 0, `SELECT` không dùng được; Valkey 9.0+ hỗ trợ nhiều database trong cluster (namespace logic, slot vẫn tính theo tên key).
  - Pub/Sub thường phát tới mọi node; từ 7.0 có sharded pub/sub (`SPUBLISH`, `SSUBSCRIBE`) theo slot.
  - Hash tag quá rộng (`{tenant}` cho tenant lớn) dồn dữ liệu vào một slot: lại thành [[hot-key|hot key]] và một shard đầy trước.
- **Client Java với Cluster**:
  - Lettuce 6.x (Spring Boot 3.5/4.0) mặc định không làm mới bảng slot, kể cả theo sự kiện (`MOVED`, mất kết nối) lẫn định kỳ: bật `spring.data.redis.lettuce.cluster.refresh.adaptive=true` và đặt `spring.data.redis.lettuce.cluster.refresh.period`, nếu không client có thể lỗi mãi với node đã chết.
  - Lettuce 7.x (Spring Boot 4.1+) bật sẵn mọi adaptive trigger và property `adaptive` đã bị bỏ; refresh định kỳ vẫn tắt, nên vẫn nên đặt `refresh.period`.
  - `MGET` qua nhiều slot được Lettuce tách theo slot và gộp kết quả (không còn atomic), nhưng `MULTI`/`EXEC` và Lua thì không.
  - Lua có flag `allow-cross-slot-keys` (7.0+) cho key không khai báo qua `KEYS`, vẫn giới hạn trong một node và không được khuyến khích.
- **Thời gian failover**: Cluster cần khoảng `cluster-node-timeout` cộng thời gian bầu, tức thường 15–20 giây với mặc định. Giảm timeout thì failover nhanh hơn nhưng dễ failover nhầm khi mạng chậm hoặc Redis dừng vì fork.
- **Managed**:
  - ElastiCache: Multi-AZ với tự failover, có chế độ cluster mode enabled (Redis Cluster) và disabled (một primary).
  - MemoryDB ghi mọi lệnh vào transaction log nhiều AZ trước khi xác nhận, nên không mất lệnh đã xác nhận khi failover; đổi lại ghi chậm hơn ElastiCache.
- **Nhánh và giấy phép**: Redis 7.4 đổi giấy phép sang RSALv2/SSPL, Redis 8 thêm lựa chọn AGPLv3. Valkey (nhánh từ 7.2.4) giữ giấy phép BSD và tương thích giao thức, được AWS, Google Cloud hỗ trợ; khi chọn dịch vụ managed, kiểm tra engine là Redis hay Valkey.
