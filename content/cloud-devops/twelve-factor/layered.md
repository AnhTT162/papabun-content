## Quick

[[twelve-factor-app|Twelve-Factor App]] là 12 quy tắc để một app chạy tốt trên cloud: **build một lần, cấu hình theo môi trường, process [[stateless|stateless]] và khởi động, tắt nhanh**, log ra stdout, dev giống prod. Vi phạm hay gặp nhất là giữ trạng thái trên máy app: chạy một instance thì không sao, scale lên hai là hỏng.

## Interview

Twelve-Factor do Heroku viết năm 2011 từ kinh nghiệm chạy rất nhiều app trên nền tảng của họ; từ 2024 là dự án mã nguồn mở. Ý chung: app có hợp đồng rõ ràng với môi trường chạy, nên nền tảng có thể tạo, nhân bản và giết process bất kỳ lúc nào.

Tôi nhóm 12 quy tắc thành bốn ý. Một là **artifact và cấu hình tách nhau**: một codebase, dependency khai báo đầy đủ, cấu hình thay đổi theo môi trường (URL database, credential, cờ tính năng) không nằm trong artifact. Pipeline build ra một jar hay image, gắn với cấu hình của từng môi trường thành một [[release-twelve-factor|release]] bất biến; rollback là chạy lại release cũ, không build lại.

Hai là **process stateless, share-nothing**: session, file upload, cache cần đúng đều ở [[backing-service|backing service]] như Redis, S3, database, gắn qua URL trong cấu hình. Scale là thêm process, tách loại process: web nhận request, worker xử lý hàng đợi.

Ba là **[[disposability|disposability]]**: khởi động nhanh, nhận SIGTERM thì ngừng nhận việc mới, làm xong việc dở rồi thoát; chết đột ngột cũng không mất việc vì job nằm trong queue.

Bốn là **vận hành**: log ghi ra stdout như một dòng sự kiện, nền tảng gom đi; tác vụ một lần như migration chạy với cùng release; dev, staging, prod dùng cùng loại backing service.

Spring Boot lo sẵn phần lớn: [[fat-jar|fat jar]] tự mở port, đọc cấu hình từ biến môi trường, log mặc định ra console, tắt êm khi nhận SIGTERM (mặc định từ Boot 3.4; bản cũ phải đặt `server.shutdown=graceful`). Bẫy là những thứ nằm ngoài framework: ghi file vào ổ cục bộ, `@Scheduled` chạy ở mọi replica, cache local dùng như nguồn đúng, profile chọn lúc build. Các lỗi này không lộ ra trên máy dev vì dev chỉ chạy một instance, đó là lý do [[dev-prod-parity|dev/prod parity]] quan trọng.

## Deep

- **12 quy tắc** (theo 12factor.net):
  1. Codebase: một repo cho mỗi app, nhiều lần deploy. Code dùng chung giữa các app tách thành thư viện có phiên bản.
  2. Dependencies: khai báo tường minh và cô lập; không dựa vào công cụ có sẵn trên máy (`curl`, `ImageMagick`) mà không khai báo. Image container là cách cô lập phổ biến (bài Docker & container).
  3. Config: lưu trong môi trường. Phép thử của tài liệu gốc: có thể mở mã nguồn ngay bây giờ mà không lộ credential nào không?
  4. Backing services: database, queue, SMTP là tài nguyên gắn vào qua URL; đổi PostgreSQL tự chạy sang RDS chỉ đổi cấu hình.
  5. Build, release, run tách bạch: build ra artifact, release = artifact + config (có id riêng, bất biến), run chạy release.
  6. Processes: stateless, share-nothing; [[sticky-session|sticky session]] là vi phạm.
  7. [[port-binding|Port binding]]: app tự mở port HTTP (Tomcat nhúng trong fat jar) thay vì được deploy vào application server.
  8. Concurrency: scale ngang bằng mô hình process, theo loại process (web, worker).
  9. Disposability: khởi động nhanh, tắt êm khi nhận SIGTERM, chịu được chết đột ngột.
  10. [[dev-prod-parity|Dev/prod parity]]: thu hẹp ba khoảng cách: thời gian (deploy sau vài giờ, không phải vài tuần), con người (người viết code cũng deploy), công cụ (cùng loại backing service).
  11. Logs: dòng sự kiện ra stdout, không tự quản lý file.
  12. Admin processes: tác vụ một lần chạy trong cùng môi trường và cùng release với app.
- **Config không phải mọi cấu hình**: định tuyến URL, bean wiring giống nhau ở mọi môi trường thì nằm trong code. Chỉ thứ khác nhau giữa các lần deploy mới đưa ra ngoài.
- **Biến môi trường không phải cách duy nhất**: tinh thần là cấu hình nằm ngoài artifact. ConfigMap mount thành file cũng đạt. Riêng secret, biến môi trường dễ lộ (`/proc/<pid>/environ`, process con, crash report); mount file hoặc secret manager an toàn hơn (bài Quản lý secret). Thứ tự ưu tiên nguồn cấu hình của Spring Boot ở bài Auto-configuration & cấu hình.
- **Profile chọn lúc build là vi phạm**: Maven profile `-Pprod` lọc resource để nhúng URL prod vào jar, thì artifact đã test ở staging không phải artifact chạy prod. `application-prod.yml` trong jar chứa giá trị mặc định không nhạy cảm thì chấp nhận được; giá trị riêng mỗi lần deploy và secret vẫn đến từ bên ngoài. Tài liệu gốc cũng cảnh báo gom cấu hình theo tên môi trường (`dev`, `staging`, `prod`) không mở rộng được khi số môi trường tăng.
- **Release bất biến**: không sửa file trong container đang chạy bằng `kubectl exec`; pod bị thay là thay đổi biến mất, và không ai biết prod đang chạy gì. Tag image theo commit SHA, không dùng `latest` (bài CI/CD pipeline).
- **Stateless ở từng chỗ hay bị quên**:
  - File upload, file xuất báo cáo ghi vào ổ cục bộ: request sau tới instance khác thì 404, pod bị thay thì mất. Đưa vào [[object-storage|object storage]] và cho tải bằng [[presigned-url|presigned URL]] (bài Thiết kế lưu trữ file / video).
  - Session trong bộ nhớ: dùng Spring Session với Redis hoặc token.
  - Cache local chỉ để tăng tốc, không làm nguồn đúng; mỗi instance một bản thì dữ liệu lệch nhau (bài Local & multi-level cache).
  - Job `@Scheduled` chạy ở mọi replica: tách thành worker riêng hoặc dùng khoá (bài Distributed lock & fencing token).
  - Counter rate limit trong bộ nhớ: ba replica thì giới hạn thực tế gấp ba.
- **Concurrency với JVM**: tài liệu gốc không cấm thread; một JVM dùng thread pool hay virtual thread bên trong là bình thường. Ý chính là scale ngang bằng thêm process, và tách loại process: pod web và pod worker scale theo hai thước đo khác nhau (request/giây và độ dài hàng đợi).
- **Disposability với JVM**: khởi động chậm (30–60 giây) làm autoscale phản ứng chậm và rolling update kéo dài. Bẫy hay gặp: script entrypoint gọi `java -jar` mà không có `exec`, nên shell nhận SIGTERM còn JVM thì không, và process bị SIGKILL khi hết thời gian chờ (bài Docker & container). Cách giảm ở bài Khởi động nhanh: CDS, CRaC, GraalVM native. Tắt êm (SIGTERM, `preStop`, rút connection) ở bài Graceful shutdown & vòng đời process.
- **Log**: ghi ra stdout, không tự xoay file trong container; Logback dùng `ConsoleAppender`, log có cấu trúc JSON. Pipeline gom log và bẫy stdout bị chặn ở bài Log cho production.
- **Admin process và migration**: Flyway/Liquibase chạy lúc app khởi động là cách đơn giản; nhiều replica cùng khởi động thì công cụ dùng khoá trong database để chỉ một instance chạy migration. Migration lâu làm mọi pod chờ và có thể bị liveness probe giết; khi đó tách thành Job chạy trước khi deploy, dùng đúng image của release đó nhưng không mở web server (`spring.main.web-application-type=none`). `CREATE INDEX CONCURRENTLY` của PostgreSQL không chạy được trong transaction, nên script đó phải tắt transaction của Flyway (`executeInTransaction=false`).
- **Dev/prod parity**: H2 trong test thay cho PostgreSQL trên prod là khoảng cách công cụ; khác biệt về SQL, khoá, thứ tự NULL chỉ lộ trên prod. Dùng [[testcontainers|Testcontainers]] (bài Testcontainers).
- **Mở rộng sau 12 quy tắc**: Kevin Hoffman (*Beyond the Twelve-Factor App*, O'Reilly 2016) thêm API first, telemetry, authentication và authorization thành 15 quy tắc. Bản mã nguồn mở hiện đang được cộng đồng cập nhật cho container và Kubernetes, nơi nhiều quy tắc đã thành mặc định: ConfigMap/Secret cho config, Service cho backing service, SIGTERM rồi SIGKILL cho disposability, stdout cho log.
- **Khi nào không áp dụng nguyên văn**: database, broker, cache tự vận hành là ứng dụng stateful; chúng chạy bằng StatefulSet hay dịch vụ managed, không theo quy tắc stateless. Twelve-Factor nói về app nghiệp vụ dùng các backing service đó.
