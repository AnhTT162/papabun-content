## Quick

[[two-phase-commit|Two-phase commit (2PC)]] làm một transaction **commit ở tất cả** hoặc **ở không ai** trong nhiều database: pha 1 coordinator hỏi mọi bên "sẵn sàng chưa" (prepare), pha 2 gửi quyết định chung. Điểm yếu cốt lõi là **blocking**: bên đã trả lời "sẵn sàng" phải **giữ khoá và chờ** coordinator, không tự commit hay rollback được. Vì vậy giữa các microservice ta tránh 2PC; nhưng bên trong database phân tán, 2PC chạy trên nền [[consensus|consensus]] vẫn có mặt ở khắp nơi.

## Interview

**Cơ chế**:
- **Pha 1, prepare**: coordinator gửi PREPARE. Mỗi participant ghi đủ dữ liệu xuống đĩa để chắc chắn commit được kể cả khi crash, giữ nguyên khoá, rồi trả lời YES. Đã YES là **hứa**: từ giờ chỉ coordinator được quyết. Lỗi thì trả lời NO.
- **Điểm commit**: đủ YES thì coordinator **ghi quyết định COMMIT vào log của nó** trước khi gửi đi. Một NO hoặc hết giờ chờ phiếu thì quyết định ABORT.
- **Pha 2**: gửi COMMIT hoặc ROLLBACK, retry tới khi mọi bên ACK. Đã quyết COMMIT thì không đổi được, kể cả khi một bên đang chết.

**Blocking**: coordinator chết sau khi participant đã YES thì participant ở trạng thái [[in-doubt-transaction|in-doubt]]: tự commit có thể sai vì bên khác đã NO, tự rollback có thể sai vì coordinator đã ghi COMMIT. Nó giữ khoá trên các dòng đó cho tới khi coordinator hồi phục, chặn mọi transaction khác chạm vào.

**Trong Java**: chuẩn [[xa|XA]] và [[jta|JTA]]. Mỗi resource (JDBC, JMS) cung cấp `XAResource` với `prepare`, `commit`, `rollback`, `recover`; transaction manager (Narayana, Atomikos, app server Jakarta EE) làm coordinator, Spring dùng qua `JtaTransactionManager`.

**Vì sao tránh giữa các service**:
- Mọi bên phải sống cùng lúc: availability bằng tích của từng bên.
- Thêm vòng mạng và lần ghi đĩa; khoá giữ suốt hai pha, kể cả khi chờ bên chậm nhất.
- REST API, Kafka, phần lớn dịch vụ cloud không phải XA resource.
- In-doubt cần người vận hành hiểu và xử lý tay.

**Thay thế, theo thứ tự nên nghĩ tới**: vẽ lại ranh giới để dữ liệu phải nhất quán chặt nằm trong **một database**; [[outbox|outbox]] khi chỉ cần "ghi và phát event" nguyên tử; [[saga|saga]] hoặc [[tcc|TCC]] cho nghiệp vụ nhiều bước; idempotency và [[reconciliation|đối soát]] làm lưới an toàn.

## Deep

- **Coordinator phải có log bền**: quyết định ghi xuống đĩa trước khi gửi pha 2; khởi động lại thì đọc log và gửi tiếp. Phần lớn triển khai dùng [[presumed-abort|presumed abort]]: không tìm thấy quyết định cho một transaction thì coi là ABORT, nên không cần ghi log cho các transaction bị huỷ.
- **Recovery trong XA**: khởi động lại, transaction manager gọi `XAResource.recover()` trên từng resource để lấy danh sách Xid đang prepared, đối chiếu với log của mình, rồi commit hoặc rollback từng cái.
- **PostgreSQL**: `PREPARE TRANSACTION 'gid'`, sau đó `COMMIT PREPARED` hoặc `ROLLBACK PREPARED` từ bất kỳ session nào. `max_prepared_transactions` mặc định 0, tức tắt; bật thì standby phải đặt không nhỏ hơn primary. Transaction đã prepare sống qua restart, vẫn giữ khoá, và **chặn [[vacuum|VACUUM]] dọn dòng chết**; bị bỏ quên lâu có thể dẫn tới nguy cơ [[xid-wraparound|wraparound]]. Theo dõi `pg_prepared_xacts`, cảnh báo khi có dòng cũ hơn vài phút. Tài liệu PostgreSQL nói rõ lệnh này dành cho transaction manager, không phải để ứng dụng gọi.
- **MySQL**: `XA START`, `XA END`, `XA PREPARE`, `XA COMMIT`. Trước 5.7.7, XA đã prepare bị rollback khi client ngắt kết nối và không an toàn với replication; từ 5.7.7 nó tồn tại tới khi có lệnh commit hoặc rollback và được ghi binlog thành hai phần. `XA RECOVER` liệt kê transaction đang prepared.
- **[[heuristic-decision|Heuristic decision]]**: DBA mất kiên nhẫn, chạy `ROLLBACK PREPARED` tay cho transaction in-doubt, trong khi coordinator đã ghi COMMIT và commit các bên còn lại. Kết quả là dữ liệu lệch, JTA báo `HeuristicMixedException`. Chỉ quyết tay sau khi đã đọc log của coordinator, và ghi lại để đối soát.
- **Tối ưu một pha**: transaction chỉ chạm một resource thì transaction manager bỏ pha prepare và commit thẳng. Last resource commit: một resource không hỗ trợ XA được đặt cuối và commit thay cho bước quyết định; giảm an toàn khi chính lần commit đó mất phản hồi.
- **3PC không cứu được**: thêm pha pre-commit để không block khi coordinator chết, nhưng chỉ đúng khi mạng có độ trễ giới hạn; có network partition thì hai phía có thể quyết khác nhau. Gần như không ai dùng trong thực tế.
- **2PC khác consensus**: 2PC cần **mọi** bên đồng ý (một NO là huỷ) và block khi coordinator chết; consensus (Paxos, Raft) cần **đa số** và chịu được thiểu số chết (bài Consensus & leader election).
- **2PC trên nền consensus**: Google Spanner chạy 2PC giữa các nhóm Paxos; mỗi participant và coordinator là một nhóm nhân bản, nên một máy chết thì leader khác thay và đọc tiếp log, không còn block lâu. CockroachDB dùng một biến thể của atomic commit trên Raft (transaction record, write intent, parallel commits); YugabyteDB cũng commit nhiều tablet trên nền Raft. Vì vậy "tránh 2PC" là lời khuyên cho tầng ứng dụng, không phải cho 2PC chạy trên nhóm nhân bản bằng consensus.
- **2PC không có consensus vẫn còn ở nhiều nơi**: Citus dùng 2PC cho lệnh ghi nhiều shard; coordinator và worker không nhân bản bằng consensus, nên vẫn có transaction in-doubt và một tiến trình nền định kỳ đối chiếu, dọn chúng (`citus.recover_2pc_interval`).
- **Kafka transaction là 2PC nội bộ**: transaction coordinator ghi trạng thái vào log nội bộ rồi ghi marker commit hoặc abort vào từng partition. Nó nguyên tử trong Kafka, không bao được database bên ngoài (bài Nhất quán dữ liệu giữa các service).
- **`ChainedTransactionManager` không phải 2PC** (deprecated từ Spring Data Commons 2.5, bị gỡ ở 3.0): chỉ commit lần lượt; commit thứ hai lỗi thì thứ nhất đã commit (bài @Transactional chuyên sâu).
- **Spring Boot**: Spring Boot 2 có auto-config JTA cho Atomikos; Spring Boot 3 đã gỡ starter đó; dùng starter do Atomikos tự phát hành (`transactions-spring-boot3-starter`, Atomikos 6.0 trở lên) hoặc starter Narayana của dự án Snowdrop. Cần cả JDBC driver hỗ trợ `XADataSource` và connection pool hiểu XA.
- **Timeout chỉ bảo vệ trước prepare**: transaction timeout của transaction manager huỷ được transaction chưa prepare. Đã prepare thì participant giữ khoá vô thời hạn cho tới khi có quyết định; không có cơ chế timeout nào an toàn ở bước này.
- **Heuristic phải được dọn**: resource tự quyết (heuristic) thì ghi nhớ kết quả và báo `XA_HEURCOM`, `XA_HEURRB` hoặc `XA_HEURMIX` cho transaction manager; nó giữ thông tin đó cho tới khi transaction manager gọi `XAResource.forget()`.
- **Đổi lại, 2PC có isolation**: khoá giữ tới lúc commit nên không ai thấy trạng thái dở dang. Saga thì không có isolation, phải che bằng semantic lock và các countermeasure (bài Saga). Khi nghiệp vụ không chịu được dirty read giữa các bước và mọi bên đều là database hỗ trợ XA, đó là lý do thật để cân nhắc 2PC.
- **Khi 2PC vẫn hợp lý**: hai database cùng một đội quản lý, lưu lượng thấp, cần nguyên tử tuyệt đối (chuyển dữ liệu giữa hai schema của một hệ thống cũ, hệ thống tài chính chạy trên app server có sẵn transaction manager). Đo độ trễ và có runbook cho in-doubt trước khi lên production.
