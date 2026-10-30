## Quick

Job scheduler phân tán chạy việc đúng giờ trên nhiều máy, theo lịch [[cron|cron]] định kỳ hoặc hẹn giờ một lần ("huỷ đơn chưa thanh toán sau 30 phút"), không chạy sót và không chạy trùng ngoài ý muốn. Tách ba vai: kho lưu định nghĩa job, phần kích hoạt biến job đến hạn thành một lần chạy, và worker thực thi. **Không có exactly-once: hệ thống cho at-least-once ([[delivery-semantics|delivery semantics]]), mỗi lần chạy mang khoá (job_id, giờ hẹn), và tác dụng phụ dùng khoá đó để chỉ áp dụng một lần.**

## Interview

Tôi hỏi trước: job định kỳ hay hẹn giờ một lần, bao nhiêu job, cần chính xác tới mức nào, một lần chạy dài bao lâu, có nhiều team dùng chung không. Giả định: 2 triệu job định kỳ, 50 triệu job hẹn giờ mỗi ngày (khoảng 580 mỗi giây), chạy trễ vài giây là chấp nhận được, mỗi lần chạy từ vài mili giây tới một giờ.

**Dữ liệu**: bảng `job` (lịch, múi giờ, `next_fire_at`, các chính sách) và bảng `job_run`, mỗi dòng là một lần chạy, có ràng buộc unique trên `(job_id, fire_at)`, cùng `status`, `attempt`, `lease_until`.

**Kích hoạt**: mỗi giây, scheduler lấy job đến hạn bằng [[skip-locked|`FOR UPDATE SKIP LOCKED`]]. Trong một transaction, nó tạo dòng `job_run` và đẩy `next_fire_at` sang lần kế tiếp, nên hai scheduler không tạo trùng. Tôi đo trên PostgreSQL 17: hai scheduler biến 100.000 job đến hạn cùng lúc thành 100.000 lần chạy trong dưới 1 giây (0,76–0,91 giây tuỳ cỡ lô), không trùng dòng nào. Database không phải nút cổ chai; hệ đích nhận 100.000 việc cùng một giây mới là vấn đề.

**Thực thi**: worker nhận một lần chạy kèm [[lease|lease]] có hạn và gia hạn bằng [[heartbeat|heartbeat]]. Worker chết thì lease hết hạn, worker khác nhận lại với `attempt` tăng. Lúc báo xong phải kèm `attempt` ([[fencing-token|fencing]]), để worker cũ tỉnh dậy không ghi đè. Tác dụng phụ (trừ tiền, gửi mail) dùng `(job_id, fire_at)` làm [[idempotency-key|idempotency key]].

**Chính sách cho từng job**: khi scheduler ngừng một lúc thì chạy bù một lần, bỏ qua, hay chạy bù mọi lần lỡ ([[misfire|misfire]]); lần trước chưa xong thì chạy chồng, bỏ, hay thay; retry có backoff rồi chuyển vào [[dead-letter-queue|dead letter queue]].

**Bẫy**: mọi job "0 0 * * *" cùng chạy lúc 00:00, nên phải rải giờ; dùng giờ của database, không dùng đồng hồ từng node; múi giờ và [[dst|DST]]. Quy trình nhiều bước chạy nhiều ngày thì dùng workflow engine ([[durable-execution|durable execution]]), không nhồi vào scheduler.

## Deep

- **Đã có sẵn những gì**: chạy `@Scheduled` trên nhiều pod là job chạy nhiều lần (bài @Async, @Scheduled & event). ShedLock giải quyết việc này cho vài job nội bộ (bài Distributed lock & fencing token). Bài này nói về nền tảng chung cho hàng triệu job của nhiều team. Hàng đợi bằng `SKIP LOCKED` có ở bài Optimistic & pessimistic locking, cron gặp DST có ở bài Thời gian & encoding.
- **Định nghĩa và lần chạy là hai thứ**: `job` là định nghĩa (biểu thức cron, múi giờ, đích gọi, timeout, số lần retry, chính sách misfire và chạy chồng). `job_run` là lịch sử, mỗi dòng ứng với một giờ hẹn. Unique trên `(job_id, fire_at)` làm phần kích hoạt idempotent: scheduler chết giữa chừng rồi node khác chạy lại cùng đoạn thì `INSERT ... ON CONFLICT DO NOTHING` bỏ qua dòng đã có. Lab chạy hai scheduler song song trên 100.000 job đến hạn, ra đúng 100.000 dòng khác nhau.
- **Số đo trên PostgreSQL 17** (localhost, M4, cấu hình mặc định, mỗi transaction lấy một lô `LIMIT n FOR UPDATE SKIP LOCKED`, tạo run và cập nhật `next_fire_at` bằng JDBC batch): lô 100 mất 0,91 giây cho 100.000 job, lô 1.000 mất 0,76 giây. Database thật có mạng, replica đồng bộ và tải khác nên chậm hơn, nhưng vẫn cho thấy tầng kích hoạt hiếm khi là nút cổ chai.
- **Chia việc kích hoạt**:
  - Ít node: mọi scheduler cùng quét bảng, `SKIP LOCKED` tự chia.
  - Nhiều node: chia job thành vài chục partition theo hash của `job_id`. Mỗi scheduler giữ lease trên một số partition (bảng lease có `owner`, `lease_until`, `epoch`), giống [[consumer-group|consumer group]] của Kafka. Mất node thì partition về tay node khác sau khi lease hết hạn.
  - Hai node cùng tưởng mình giữ một partition trong vài giây thì unique `(job_id, fire_at)` vẫn chặn tạo trùng.
- **Hẹn giờ một lần ở quy mô lớn**: 50 triệu dòng mỗi ngày, phần lớn chạy một lần rồi thôi. Partition bảng theo giờ hẹn (mỗi giờ một partition), xoá cả partition cũ thay vì `DELETE`. Muốn chính xác dưới một giây thì scheduler nạp các job của 60 giây tới vào bộ nhớ, đặt vào một [[timing-wheel|timing wheel]] (Kafka dùng cấu trúc này cho các thao tác có hẹn giờ), rồi phát đúng lúc. Job đã nạp vào wheel vẫn nằm trong database, nên node chết thì node nhận lại partition nạp lại từ đó, không mất job. Redis [[sorted-set|sorted set]] (score là giờ hẹn, lấy bằng `ZRANGE ... BYSCORE` từ Redis 6.2, rồi `ZREM` trong một script Lua) cũng dùng được, nhưng phải tự lo độ bền và việc chuyển dữ liệu khi failover.
- **Huỷ job hẹn giờ**: đơn đã thanh toán thì đánh dấu job "huỷ đơn sau 30 phút" là `CANCELLED`. Huỷ và kích hoạt có thể chạy đua nhau, nên tác vụ phải tự kiểm lại trạng thái lúc chạy: `UPDATE orders SET status = 'CANCELLED' WHERE id = ? AND status = 'UNPAID'`. Đơn đã trả tiền thì câu lệnh không đổi dòng nào, nên đúng dù job vẫn được kích hoạt.
- **Từ lần chạy tới worker**:
  - Ở quy mô vừa, worker lấy thẳng từ `job_run` bằng `SKIP LOCKED`, và bảng này là hàng đợi.
  - Ở quy mô lớn, hoặc khi đích là service của team khác, phần kích hoạt ghi kèm một dòng [[outbox|outbox]] trong cùng transaction. Relay đẩy sang Kafka hoặc SQS, theo topic riêng cho từng team hay từng mức ưu tiên, để một tenant chạy 100.000 job không làm tenant khác trễ.
  - Ghi thẳng vào queue sau khi commit là [[dual-write|dual write]]: commit xong mà chết trước khi gửi thì mất lần chạy.
- **Lease và fencing, đã chạy bằng lab**: worker A nhận run với lease 2 giây rồi dừng 3 giây (GC dài, mạng chập chờn). Worker B thử nhận ngay thì không được vì lease còn hiệu lực. Sau khi lease hết hạn, B nhận lại với `attempt` 2, áp dụng tác dụng phụ và báo xong. A tỉnh dậy: lệnh ghi tác dụng phụ trả "trùng, bỏ qua" nhờ khoá chính `(job_id, fire_at)` ở bảng đích, và lệnh `UPDATE job_run SET status = 'DONE' WHERE id = ? AND attempt = 1` không đổi dòng nào. Fencing chỉ bảo vệ trạng thái của lần chạy; tác dụng phụ bên ngoài phải tự idempotent. Gọi API bên thứ ba thì gửi kèm idempotency key (bài Idempotency).
- **Gia hạn lease**: job chạy một giờ không nên giữ lease một giờ, vì worker chết thì phải chờ một giờ mới chạy lại. Lease ngắn (ví dụ 30 giây), worker gia hạn mỗi 10 giây. Không gia hạn được (mất kết nối) thì worker tự dừng việc, vì một worker khác sắp nhận lại.
- **Misfire, đo bằng Quartz 2.5.2**: trigger cron chạy mỗi giây, `misfireThreshold` 1 giây, scheduler ngừng 8,5 giây rồi chạy lại.
  - Mặc định (smart policy, với cron là "fire once now"): chạy bù đúng một lần ngay lúc chạy lại, rồi tiếp tục theo lịch.
  - `withMisfireHandlingInstructionDoNothing()`: không chạy bù, chờ lượt kế tiếp.
  - `withMisfireHandlingInstructionIgnoreMisfires()`: chạy liền 8 lần ứng với 8 giờ hẹn đã lỡ, cùng một thời điểm. Với job "gửi báo cáo" thì người nhận nhận 8 báo cáo; với job tính lãi theo ngày thì có khi đó lại là điều cần.
  - `misfireThreshold` mặc định của Quartz 2.5.2 là 60 giây với JDBC JobStore và 5 giây với `RAMJobStore` (đã in ra từ code): trễ ít hơn mức đó thì không coi là misfire, cứ chạy muộn.
  - Nền tảng chung nên bắt mỗi job chọn rõ chính sách, và mặc định là chạy bù một lần.
- **Chạy chồng, đo bằng Quartz**: job mất 2,5 giây, trigger mỗi giây, pool 3 thread, chạy 10 giây. Không có `@DisallowConcurrentExecution` thì có 11 lần chạy, tối đa 3 lần chồng nhau (bị chặn bởi số thread, không phải bởi Quartz). Có annotation thì 4 lần, nối tiếp nhau: Quartz không bỏ lần mới mà hoãn nó tới khi lần cũ xong, rồi áp chính sách misfire nếu trễ quá ngưỡng. Kubernetes CronJob có `concurrencyPolicy`: `Allow` (mặc định), `Forbid` (bỏ lần mới), `Replace` (dừng lần cũ). Nền tảng tự viết thì kiểm lúc kích hoạt: còn run `RUNNING` của job đó thì áp dụng chính sách.
- **Retry**: phân biệt lỗi tạm thời (timeout, 503) với lỗi vĩnh viễn (400, dữ liệu sai). Retry có [[retry-backoff|backoff]] và [[jitter|jitter]], có số lần tối đa và tuổi tối đa (lần chạy trễ quá lâu thì không còn ý nghĩa), rồi chuyển sang trạng thái `FAILED` hoặc dead letter queue và báo cho team sở hữu. Retry của một lần chạy khác với lần chạy kế tiếp theo lịch, phải hiện riêng trên giao diện.
- **00:00 là giờ cao điểm**: người dùng hay viết `0 0 * * *` và `0 * * * *`. 500.000 job cùng gọi hệ đích trong một giây làm chính các hệ đó sập. Cách rải:
  - Cho job khai báo "cửa sổ linh hoạt" (chạy trong khoảng 00:00–00:15) rồi lệch mỗi job một khoảng cố định theo hash của `job_id`, để mỗi ngày job vẫn chạy cùng giờ. EventBridge Scheduler của AWS gọi tính năng này là flexible time window.
  - [[rate-limiting|Rate limit]] theo đích và theo tenant ở bước gửi đi.
- **Đồng hồ**: so `next_fire_at <= now()` bằng giờ của database, không dùng giờ của từng node. Quartz chạy cluster yêu cầu đồng hồ các node lệch nhau dưới 1 giây. Lịch theo giờ địa phương thì lưu biểu thức cron kèm múi giờ (`Asia/Ho_Chi_Minh`, `America/New_York`) và tính `next_fire_at` theo múi giờ đó; ngày đổi giờ có giờ bị bỏ qua và giờ lặp hai lần (bài Thời gian & encoding).
- **Kubernetes CronJob**:
  - Docs nói rõ nó tạo Job "khoảng một lần" mỗi giờ hẹn, có lúc tạo hai, có lúc không tạo, nên Job phải idempotent.
  - Controller ngừng lâu, hơn 100 lần lỡ, mà không đặt `startingDeadlineSeconds`: docs vẫn viết là không tạo Job, nhưng đó là hành vi của controller cũ. Controller v2 (mặc định từ 1.21, controller cũ đã bị xoá) phát event cảnh báo `TooManyMissedTimes` rồi vẫn tạo một Job cho giờ hẹn gần nhất. Muốn bỏ hẳn lần chạy quá muộn thì đặt `startingDeadlineSeconds`: lần lỡ quá hạn đó bị bỏ qua.
  - Lịch tính theo múi giờ của kube-controller-manager nếu không đặt `.spec.timeZone`.
  - Giữ lại 3 Job thành công và 1 Job lỗi theo mặc định.
  - Mỗi lần chạy là một pod, mất vài giây khởi động: hợp cho job nặng vài phút trở lên, không hợp cho hàng triệu job nhỏ.
- **Quartz cluster**: các node dùng chung JDBC JobStore và một lock toàn cụm trên database. Docs khuyên dùng khi job dài hoặc nặng CPU; tranh chấp lock tăng khi quá khoảng 3 node; hàng nghìn job ngắn thì nên chia ra nhiều scheduler. Job có `requestsRecovery` được chạy lại khi node đang chạy nó chết. Đừng bao giờ khởi động một instance không cluster trỏ vào cùng bộ bảng.
- **Khi nào không tự viết**: vài trăm job nội bộ thì ShedLock hoặc Quartz cluster là đủ. Job nặng chạy theo giờ thì dùng Kubernetes CronJob. Nhiều job hẹn giờ gọi dịch vụ cloud thì dùng scheduler managed (EventBridge Scheduler: at-least-once, có retry và dead letter queue). Quy trình nhiều bước, chờ con người, chạy nhiều ngày thì dùng [[durable-execution|durable execution]] (Temporal và các engine tương tự), vì scheduler chỉ biết "chạy lúc mấy giờ", không giữ trạng thái giữa các bước.
- **Quan sát**:
  - Độ trễ kích hoạt: giờ bắt đầu thật trừ `fire_at`, theo p50, p99 và theo tenant.
  - Số job đã đến hạn mà chưa có run (tăng dần nghĩa là tầng kích hoạt không theo kịp), số run `RUNNING` có lease đã hết hạn, tỉ lệ thành công theo job.
  - Job không chạy là lỗi khó thấy nhất: nên có cảnh báo "job X đã quá giờ mà chưa có lần chạy thành công", gọi là [[dead-mans-switch|dead man's switch]].
