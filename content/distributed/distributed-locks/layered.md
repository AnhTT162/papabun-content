## Quick

[[distributed-lock|Distributed lock]] cho một process trong cả cụm quyền làm một việc tại một thời điểm. Lock phân tán luôn phải có thời hạn ([[lease]]), vì người giữ có thể chết mà không nhả; nhưng có thời hạn thì người giữ có thể **mất lock mà không biết** (GC pause, mạng chậm) và vẫn ghi tiếp. Vì vậy **lock chỉ đủ để giảm việc làm trùng; muốn đúng tuyệt đối thì tài nguyên được bảo vệ phải tự kiểm tra [[fencing-token|fencing token]]** (số tăng dần mỗi lần cấp lock, ghi mang token cũ bị từ chối).

## Interview

**Hai mục đích khác nhau**: lock để *hiệu quả* (không gửi email nhắc hai lần, không chạy job nặng hai lần; thỉnh thoảng trùng vẫn chấp nhận được) và lock để *đúng* (hai người cùng ghi là hỏng dữ liệu, mất tiền). Câu đầu tiên nên hỏi lại người phỏng vấn là cái nào, vì lời giải khác hẳn nhau.

**Vì sao lease không đủ**: client A lấy lock TTL 10 giây, rồi bị [[stop-the-world|stop-the-world]] GC 15 giây. Lock hết hạn, B lấy lock và ghi. A tỉnh dậy, không hề biết mình đã mất lock, và ghi đè. Kiểm tra "mình còn giữ lock không" ngay trước khi ghi cũng không cứu được: pause có thể rơi đúng vào giữa kiểm tra và ghi ([[check-then-act|check-then-act]]).

**Fencing token**: dịch vụ lock cấp kèm mỗi lần lấy lock một số tăng dần (33, rồi 34). Client gửi token cùng mỗi lần ghi; storage nhớ token lớn nhất đã thấy và từ chối token nhỏ hơn. Lần ghi muộn của A mang 33 bị chặn vì storage đã thấy 34. Điểm mấu chốt: **người kiểm tra là storage, không phải client**.

**Chọn công cụ**:
- Redis `SET key token NX PX`: nhanh, đủ cho mục đích hiệu quả. Không có fencing token và có thể mất lock khi failover.
- etcd hoặc ZooKeeper: hệ [[consensus|đồng thuận]], lock sống theo session/lease, và có số tăng dần (revision của etcd, `czxid` của ZooKeeper) dùng làm fencing token. Session và lease vẫn hết hạn theo thời gian, nên client bị pause vẫn mất lock mà không biết: số tăng dần chỉ có ích khi storage kiểm tra nó.
- Database: khi tài nguyên chính là một dòng trong database, thường **không cần distributed lock**: unique constraint, `UPDATE ... WHERE status = 'PENDING'`, hay [[optimistic-locking|optimistic locking]] đã là cơ chế kiểm tra ở storage.

**Bẫy hay gặp**: TTL ngắn hơn thời gian chạy dài nhất; nhả lock bằng `DEL` không so token nên xoá mất lock của người khác; giữ lock trong lúc gọi mạng lâu.

## Deep

- **Nhả lock đúng cách**: chỉ xoá khi giá trị vẫn là token của mình, gộp trong một bước nguyên tử bằng [[lua-script|Lua script]] (`if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) end return 0`), hoặc `DELEX key IFEQ token` từ Redis 8.4. Spring Data Redis `setIfAbsent(key, value, Duration)` đã gửi một lệnh `SET ... NX` kèm `EX` hoặc `PX`, không còn bẫy `SETNX` rồi `EXPIRE` của code cũ.
- **Watchdog gia hạn (Redisson)**: không truyền `leaseTime` thì Redisson đặt TTL theo `lockWatchdogTimeout` (mặc định 30 giây) và gia hạn mỗi 10 giây khi process còn sống. Giảm được lỗi TTL ngắn, nhưng: GC pause dừng cả thread watchdog nên lock vẫn hết hạn; còn nếu thread nghiệp vụ treo mà process vẫn sống, watchdog gia hạn mãi và lock bị giữ vô thời hạn.
- **[[redlock|Redlock]]**: lấy lock trên đa số trong 5 master Redis độc lập, trong thời gian ngắn hơn TTL. Tranh luận nổi tiếng (Martin Kleppmann và antirez, 2016): Redlock giả định pause, độ trễ mạng và lệch đồng hồ có giới hạn, và không cấp fencing token. Kết luận thực dụng: cho mục đích hiệu quả thì một Redis là đủ, Redlock là thừa; cho mục đích đúng thì Redlock vẫn chưa đủ, cần hệ đồng thuận cộng fencing.
- **Công thức lock của ZooKeeper**: mỗi client tạo một [[ephemeral-node|ephemeral]] sequential znode dưới `/locks/job`; node có số nhỏ nhất giữ lock; các client khác chỉ watch node **ngay trước** mình (tránh herd effect: cả trăm client cùng thức dậy khi lock được nhả). Session hết hạn thì znode tự bị xoá: đó là lease. Java dùng Curator `InterProcessMutex`.
- **etcd**: lock gắn với một lease có TTL, client gửi keepalive để giữ lease. Revision lúc tạo key lock tăng dần toàn cụm, dùng được làm fencing token; transaction của etcd so sánh được revision trước khi ghi.
- **Storage không hỗ trợ fencing**: tự làm bằng ghi có điều kiện. Ví dụ lưu `last_token` trong dòng và `UPDATE ... SET last_token = :token WHERE id = :id AND last_token <= :token`, kiểm tra số dòng đổi. S3 từ 2024 có ghi có điều kiện (`If-None-Match`, rồi `If-Match` theo ETag, sai thì trả `412`), dùng được làm compare-and-set. Với tác dụng phụ không có điều kiện nào để kiểm tra (gửi email, gọi API bên thứ ba) thì không fencing được; phải làm thao tác idempotent (truyền idempotency key).
- **Lock bằng database**: PostgreSQL [[advisory-lock|advisory lock]] mức session (`pg_advisory_lock`) gắn với connection: PgBouncer chế độ transaction pooling làm nó hỏng, vì lần nhả có thể đi trên connection khác. `pg_advisory_xact_lock` thì giữ một transaction mở suốt thời gian làm việc. `SELECT ... FOR UPDATE` trên một dòng "lock" cũng vậy. Cả hai ổn cho việc ngắn, không ổn cho job vài phút. `pg_try_advisory_lock` không chờ, trả `false` nếu người khác giữ. Với hàng việc như email nhắc trong lab, `SELECT ... FOR UPDATE [[skip-locked|SKIP LOCKED]]` cho mỗi worker nhận một phần riêng, không cần lock toàn cục.
- **ShedLock cho `@Scheduled`**: bảng `shedlock` lưu `lock_until`. `lockAtMostFor` phải lớn hơn lần chạy dài nhất (nó là TTL), `lockAtLeastFor` ngăn node khác chạy lại ngay khi job xong quá nhanh. Bật `usingDbTime()` để mọi node dùng giờ của database, không phụ thuộc đồng hồ từng node lệch nhau.
- **Phạm vi lock**: lock toàn cục (`lock:billing`) tuần tự hoá cả hệ thống; lock theo khoá nghiệp vụ (`lock:order:42`) cho phép song song. Đừng giữ lock khi gọi dịch vụ ngoài chậm nếu tránh được.
- **Leader election là một lock dài hạn** (một node làm việc định kỳ cho cả cụm), và có cùng rủi ro [[split-brain|split brain]] như failover database; cách chặn cũng là [[fencing]] ở phía tài nguyên. Kubernetes có đối tượng `Lease` (`coordination.k8s.io`) dùng cho leader election của controller. Cơ chế Raft và quorum: bài Consensus & leader election.
- **Kiểm thử**: mô phỏng pause bằng cách dừng process (`kill -STOP`, rồi `kill -CONT` sau quá TTL) trong môi trường test, rồi kiểm tra dữ liệu có bị ghi trùng không. Đây là cách nhanh nhất để biết lock của bạn thuộc loại "hiệu quả" hay "đúng".
