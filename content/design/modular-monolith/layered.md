## Quick

[[modular-monolith|Modular monolith]] là **một đơn vị deploy nhưng chia thành các module có ranh giới rõ**: mỗi module (thường là một [[bounded-context|bounded context]]) có API công khai, phần nội bộ bị che, dữ liệu riêng, và giao tiếp với module khác qua API hoặc event trong process. Nó cho phần lớn lợi ích về tổ chức code của microservices mà không phải trả chi phí hệ phân tán, và để ngỏ đường tách service sau này. **Ranh giới chỉ có giá trị khi được kiểm tra tự động.**

## Interview

**Vì sao không microservices ngay**: mỗi lời gọi qua mạng có thể chậm hoặc lỗi, transaction phân tán cần [[saga]] và [[outbox]], mỗi service cần pipeline, giám sát, tracing riêng. Đội nhỏ hoặc nghiệp vụ còn đổi nhiều thì trả chi phí đó quá sớm. Ranh giới sai giữa các service rất đắt để sửa, còn trong một repo thì chỉ là refactor.

**Thế nào là một module tốt**:
- Ranh giới theo bounded context, không theo tầng kỹ thuật.
- API công khai nhỏ (interface, DTO, event); phần còn lại để package-private hoặc nằm trong package nội bộ.
- Sở hữu dữ liệu: bảng (hoặc schema) riêng, không join và không khoá ngoại sang bảng của module khác.
- Không có phụ thuộc vòng giữa các module.

**Kiểm tra ranh giới**, từ mạnh tới nhẹ:
- Mỗi module một Maven/Gradle module: compiler chặn import sai, nhưng build cấu hình phức tạp hơn.
- Một module build, ranh giới bằng package: [[spring-modulith|Spring Modulith]] coi mỗi package con trực tiếp của package gốc là một module, `ApplicationModules.of(App.class).verify()` làm test đỏ khi có truy cập vào package nội bộ hoặc vòng phụ thuộc. [[archunit|ArchUnit]] làm được việc tương tự với quy tắc tự viết.

**Giao tiếp giữa các module**: gọi đồng bộ qua interface công khai khi cần kết quả ngay; event khi bên phát không cần biết ai nghe (`OrderPlaced` để module điểm thưởng cộng điểm). Event trong process cũng phải tính chuyện mất: khi thêm starter lưu trữ (`spring-modulith-starter-jpa`, `-jdbc`, `-mongodb`), Spring Modulith lưu các lần phát event cho listener transactional vào bảng ([[event-publication-registry|event publication registry]]) để gửi lại sau sự cố.

**Khi nào tách một module thành service**: khi có lý do đo được: cần scale riêng, nhịp release khác hẳn, công nghệ khác, hoặc cần cô lập lỗi. Module đã có API và dữ liệu riêng thì việc tách chủ yếu là đổi lời gọi trong JVM thành HTTP hay message.

## Deep

- **Spring Modulith chi tiết** (1.x dùng với Spring Boot 3, 2.x yêu cầu Spring Boot 4): package gốc của module là API, package con là nội bộ trừ khi đánh dấu `@NamedInterface`. `verify()` kiểm không có vòng, chỉ truy cập qua API, và `@ApplicationModule(allowedDependencies = ...)` nếu khai báo để siết thêm. `@ApplicationModuleTest` mặc định (`STANDALONE`) chỉ khởi động module chứa test; bean của module khác thì mock bằng `@MockitoBean` hoặc chọn `mode = DIRECT_DEPENDENCIES`. Phải mock quá nhiều là dấu hiệu module đang coupling cao. `Documenter` sinh sơ đồ module (PlantUML, C4) từ code.
- **`@ApplicationModuleListener`**: gộp `@Async`, `@Transactional(propagation = REQUIRES_NEW)` và `@TransactionalEventListener` (`AFTER_COMMIT`): listener chạy sau khi bên phát commit, trên thread khác, trong transaction riêng. Lỗi ở listener không rollback bên phát; lần phát đó nằm lại trong event publication registry ở trạng thái chưa hoàn thành, có thể gửi lại khi khởi động (`spring.modulith.events.republish-outstanding-events-on-restart`) hoặc qua API `IncompleteEventPublications`. Listener vì vậy phải [[idempotent-consumer|idempotent]]. Mặc định bản ghi đã hoàn thành vẫn nằm trong bảng `event_publication`, nên bảng phình mãi: đặt `spring.modulith.events.completion-mode` (`DELETE` hoặc `ARCHIVE`) hoặc dọn định kỳ bằng `CompletedEventPublications`. Spring Modulith 2.0 thêm các trạng thái (`PROCESSING`, `FAILED`, `RESUBMITTED`) và phát hiện publication bị treo quá lâu.
- **Đưa event ra ngoài**: `@Externalized` cùng module `spring-modulith-events-kafka` (hoặc AMQP, JMS) gửi event sang broker sau commit, dựa trên cùng registry: gần giống outbox (bản ghi cùng transaction, gửi lại được) nhưng không đảm bảo thứ tự hay tự retry. Từ 2.1 có thể cắm một thư viện outbox thật qua `spring.modulith.events.externalization.mode=outbox`. Đây là bước đầu khi một module sắp tách ra service.
- **Dữ liệu**: schema PostgreSQL riêng cho mỗi module (cùng một database) là cách rẻ để thấy rõ ranh giới; cấp quyền database theo schema để module này không đọc được bảng của module kia. Báo cáo cần dữ liệu nhiều module: dựng read model riêng từ event, hoặc gọi API của từng module rồi ghép, không join chéo.
- **Transaction xuyên module**: cùng database thì kỹ thuật vẫn mở được một transaction cho nhiều module, nhưng làm vậy là dính chúng lại, và khi tách service thì không còn dùng được. Thiết kế như thể đã tách: mỗi use case một module, phối hợp bằng event và bù trừ.
- **Quy trình tách một module ra service**: (1) chuyển schema của module sang database riêng (dữ liệu đã không bị join chéo nên chủ yếu là sao chép và đổi kết nối); (2) bật `@Externalized` cho các event của module, để module còn lại nghe qua broker bằng consumer idempotent; (3) dựng service mới chạy song song, chuyển dần lời gọi đồng bộ sang HTTP sau một interface ([[strangler-fig|strangler fig]]); (4) tránh dual-write (ghi cả hai nơi từ ứng dụng), vì một bên lỗi là lệch dữ liệu; dùng event hoặc CDC để đồng bộ trong thời gian chuyển.
- **[[jpms|JPMS]]**: module của Java (`module-info.java`) cho ranh giới mạnh nhất lúc biên dịch và chạy, nhưng ít được dùng với Spring vì reflection, classpath scanning và thư viện chưa hỗ trợ đầy đủ. Hầu hết nhóm chọn Spring Modulith, ArchUnit hoặc build nhiều module.
- **Quyền sở hữu**: mỗi module có đội chủ quản ghi trong `CODEOWNERS`; thay đổi API công khai cần đội chủ quản review. Thiếu điều này, ranh giới bị bào mòn dù có test.
- **Giới hạn**: vẫn chung một lần deploy, một JVM, một heap: module rò bộ nhớ làm sập cả ứng dụng; module nặng CPU không scale riêng được. Build và test toàn bộ ứng dụng chậm dần, cần chạy test theo module thay đổi.
- **Dấu hiệu modular monolith đang thành [[big-ball-of-mud|big ball of mud]]**: số vi phạm bị `@Disabled` hay đưa vào danh sách bỏ qua tăng dần, module `common` hay `shared` phình to, nhiều thay đổi phải sửa đồng thời ba module.
