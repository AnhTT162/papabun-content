## Quick

[[cqrs|CQRS]] tách **mô hình ghi** (nhận lệnh, giữ bất biến nghiệp vụ) khỏi **mô hình đọc** (dữ liệu đã dàn sẵn cho từng màn hình); nó **không bắt buộc** hai database hay event sourcing. [[event-sourcing|Event sourcing]] lưu **chuỗi event bất biến làm nguồn sự thật**: trạng thái hiện tại có được bằng cách phát lại event, còn [[projection|projection]] dựng [[read-model|read model]] từ chính các event đó. Cái giá: read model **trễ** so với lệnh ghi, schema event phải sống **mãi mãi**, và độ phức tạp chỉ đáng bỏ ra cho phần domain thật sự cần lịch sử.

## Interview

**CQRS có ba mức**, chọn mức thấp nhất đủ dùng:
- Cùng database, hai mô hình: lệnh đi qua entity và [[aggregate-root|aggregate]], truy vấn đọc thẳng ra DTO bằng SQL. Không trễ, không hạ tầng mới.
- Bảng đọc riêng (`order_summary`) cập nhật trong cùng transaction với lệnh ghi.
- Kho đọc riêng (Elasticsearch, Redis, bảng ở service khác) cập nhật bằng event: đọc nhanh và co giãn riêng, đổi lại [[eventual-consistency|nhất quán sau một lúc]].

**Event sourcing chạy thế nào**: mỗi aggregate là một stream (`wallet-42`). Xử lý lệnh: đọc stream, phát lại để có trạng thái và version, kiểm tra bất biến, sinh event mới, rồi **append có điều kiện** "stream đang ở version 7". Hai request cùng sửa một ví thì request sau thấy version đã là 8 và bị từ chối: đó là [[optimistic-locking|optimistic locking]] của [[event-store|event store]].

**Projection** đọc event theo thứ tự, cập nhật read model và lưu checkpoint (vị trí đã xử lý). Nó phải [[idempotency|idempotent]] vì sẽ gặp lại event sau khi crash. Lợi thế lớn: muốn màn hình mới thì viết projection mới và **phát lại từ đầu**.

**[[es-snapshot|Snapshot]]**: stream dài hàng nghìn event thì lưu trạng thái ở version N, lần sau chỉ phát lại event sau N. Snapshot là cache, xoá đi vẫn dựng lại được.

**Khi nào không dùng**: CRUD đơn giản; chỉ cần audit (bảng audit hoặc [[cdc|CDC]] là đủ); đội chưa từng vận hành; dữ liệu cá nhân phải xoá được. Dùng event sourcing cho **một [[bounded-context|bounded context]]** cần lịch sử (sổ cái, đặt chỗ), không cho cả hệ thống.

**Bẫy hay gặp**: người dùng ghi xong tải lại trang không thấy thay đổi vì projection chưa chạy tới; event đặt tên kiểu CRUD (`CartUpdated`) làm mất ý nghĩa nghiệp vụ; coi event store là message broker cho các service khác.

## Deep

- **Code tối giản** (Java 21, đã chạy thử): trạng thái là phép gộp event, append kiểm tra version.
  ```java
  record State(long balance, long version) {
      State apply(WalletEvent e) {
          return switch (e) {
              case Deposited d -> new State(balance + d.amount(), version + 1);
              case Withdrawn w -> new State(balance - w.amount(), version + 1);
          };
      }
  }
  // append(streamId, expectedVersion, events): stream.size() != expectedVersion thì ném ConcurrencyException
  ```
  Ví có `Deposited(100)`, `Withdrawn(30)`; hai request cùng đọc được `State[balance=70, version=2]` rồi cùng rút 50. Request đầu append thành công; request sau nhận `conflict: expected 2, actual 3`, phải đọc lại và lúc đó thấy số dư 20 không đủ. Không kiểm tra version thì cả hai rút được và số dư thành -30.
- **Event store trên PostgreSQL**: bảng `events(stream_id, version, type, data jsonb, global_position bigserial)` với khoá chính `(stream_id, version)`; insert trùng version thì vi phạm khoá, đó chính là phát hiện xung đột. Projection đọc theo `global_position` gặp đúng lỗi của outbox polling: số được cấp lúc insert, không theo thứ tự commit, nên đọc `global_position > checkpoint` có thể bỏ sót event của transaction commit muộn (bài Transactional outbox & CDC). Cách xử lý: một writer duy nhất (advisory lock khi append), chỉ đọc tới vị trí mà mọi transaction trước nó đã xong, hoặc đọc qua CDC.
- **Kafka không phải event store cho aggregate**: không có append có điều kiện theo version của từng stream, và đọc lại một aggregate phải quét cả partition chứa hàng triệu aggregate khác. Kafka hợp để **phân phối** event ra ngoài; event store chuyên dụng (EventStoreDB, nay là KurrentDB; Axon Server) hoặc bảng PostgreSQL giữ nguồn sự thật.
- **Bất biến giữa nhiều aggregate**: "email không trùng" không kiểm được trong một stream. Dùng bảng giữ chỗ có unique constraint (insert email trước, rồi mới append `UserRegistered`), hoặc chấp nhận trùng hiếm gặp và xử lý bằng bù trừ.
- **Command khác event**: command (`Withdraw`) là yêu cầu, có thể bị từ chối; event (`Withdrawn`) là việc đã xảy ra, không ai từ chối được. Chỉ event được lưu vào stream.
- **Retry lệnh không được ghi hai lần**: expected version chỉ chặn hai lệnh ghi **đồng thời**. Client timeout rồi gửi lại `Withdraw` thì lần gửi lại đọc version mới, kiểm tra lại, và rút tiền lần hai. Gắn `commandId` vào lệnh, lưu nó trong metadata của event (hoặc bảng khử trùng cùng transaction với append); gặp lại `commandId` đã xử lý thì trả kết quả cũ (bài Idempotency).
- **Projection idempotent thế nào**: read model cùng database với checkpoint thì cập nhật cả hai trong một transaction; khác hệ (Elasticsearch, Redis) thì ghi kèm version hoặc position của event và bỏ qua bản cũ hơn, để giao ít nhất một lần vẫn ra đúng kết quả. Một event làm projection lỗi mãi (poison event) sẽ chặn mọi event sau nó: quyết định trước là dừng và cảnh báo (read model đúng nhưng cũ dần) hay ghi vào hàng lỗi và đi tiếp (read model mới nhưng thiếu), và đo độ trễ projection so với event store.
- **Read your writes**: trả về version mới trong response của lệnh; trang đọc kèm version đó và chờ ngắn cho tới khi projection đạt version, hoặc giao diện cập nhật lạc quan từ chính dữ liệu đã gửi.
- **Phát lại không được gây side effect**: projection chỉ ghi read model. Việc gửi email, gọi thanh toán thuộc về process manager hay [[saga|saga]] có lưu trạng thái đã làm; nếu đặt trong projection thì lần rebuild sẽ gửi lại email cho mọi khách hàng.
- **Rebuild projection**: hàng chục triệu event có thể mất hàng giờ. Dựng vào bảng mới song song với bảng cũ, đuổi kịp hiện tại rồi chuyển truy vấn sang (kiểu blue/green), thay vì xoá bảng đang phục vụ.
- **Schema event là vĩnh viễn**: event cũ không sửa được. Đổi cấu trúc thì thêm phiên bản và [[upcasting|upcaster]] chuyển event cũ sang dạng mới lúc đọc (bài Event schema evolution). Snapshot cũng có schema: đổi class trạng thái thì bỏ snapshot cũ và dựng lại từ event.
- **Xoá dữ liệu cá nhân**: không xoá được event giữa stream. [[crypto-shredding|Crypto-shredding]]: mã hoá trường cá nhân bằng khoá riêng của từng người, xoá khoá khi có yêu cầu xoá; event còn đó nhưng không đọc được phần cá nhân.
- **Khi nào snapshot**: đo trước. Stream vài chục event thì phát lại nhanh hơn đọc snapshot. Stream dài vô hạn (tài khoản mở nhiều năm) thì cân nhắc thiết kế lại: "đóng sổ" theo kỳ, mở stream mới với số dư đầu kỳ.
- **Truy vấn theo thời gian**: số dư lúc 23:59 ngày 31/12 là phát lại tới mốc đó; tìm lỗi bằng cách phát lại event vào code đã sửa và so sánh. Đây là lợi ích mà bảng chỉ lưu trạng thái hiện tại không có.
- **Phương án nhẹ hơn**: sổ cái append-only (bảng `ledger_entries`) cộng cột số dư cập nhật trong cùng transaction. Có lịch sử, có audit, truy vấn bằng SQL, không cần projection bất đồng bộ. Phần lớn hệ thống "cần lịch sử" dừng ở đây là đủ.
- **Framework Java**: Axon Framework (`@Aggregate`, `@CommandHandler`, `@EventSourcingHandler`, `AggregateLifecycle.apply`) làm sẵn phát lại, snapshot, upcaster và projection, đổi lại gắn chặt mô hình code vào framework.
