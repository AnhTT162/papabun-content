## Quick

[[layered-architecture|Kiến trúc phân lớp]] chia ứng dụng thành **controller** (nhận HTTP, validate định dạng, chuyển đổi dữ liệu), **service** (nghiệp vụ và ranh giới transaction) và **repository** (truy cập dữ liệu), và **phụ thuộc chỉ đi xuống**. API nhận và trả [[dto|DTO]], không nhận và trả entity. Ở codebase lớn, chia package theo tính năng trước rồi mới tới tầng.

## Interview

**Mỗi tầng giữ một trách nhiệm**:
- Controller: map URL, đọc tham số, `@Valid` cho định dạng, gọi một method service, map kết quả ra response và status code. Không có `if` nghiệp vụ.
- Service: quy tắc nghiệp vụ, phối hợp nhiều repository, `@Transactional`. Một use case là một method service, nên transaction bao trọn use case đó.
- Repository: query, không quyết định nghiệp vụ.

**Vì sao không dùng entity làm request/response**:
- Bảo mật: client gửi thêm `role` là ghi được ([[mass-assignment|mass assignment]]); trả entity là lộ `passwordHash` hay field nội bộ.
- Mất dữ liệu: bind request vào entity rồi `save()` thì field client không gửi bị ghi `null`.
- Coupling: đổi tên cột là đổi hợp đồng API, làm hỏng client.
- [[lazy-loading|Lazy loading]]: Jackson serialize sau khi transaction đã đóng. Proxy lazy làm lỗi `No serializer found for class ...ByteBuddyInterceptor` (property `hibernateLazyInitializer`); bỏ qua được lỗi đó thì gặp `LazyInitializationException`, hoặc thêm query ngoài ý muốn nếu [[open-session-in-view|Open Session in View]] đang bật.

**[[package-by-feature|Package-by-feature]] và package-by-layer**: `controller/`, `service/`, `repository/` dễ hiểu lúc đầu, nhưng một tính năng nằm rải ở ba package, và mọi class phải `public` để gọi được nhau. `order/`, `payment/` gom thứ đổi cùng nhau, và cho phép để class nội bộ ở mức package-private: `OrderPricing` không `public` thì `payment` không gọi tắt được.

**Bẫy hay gặp**:
- Controller gọi thẳng repository "cho nhanh": nghiệp vụ bắt đầu rơi vào controller, và không có transaction bao quanh.
- [[architecture-sinkhole|Architecture sinkhole]]: phần lớn request đi qua service chỉ để chuyển tiếp xuống repository. Vài method như vậy là bình thường; khi đa số như vậy, có thể nới lỏng tầng cho phần đọc.

## Deep

- **Tầng chặt và tầng nới**: chặt (strict) chỉ cho gọi tầng ngay dưới; nới (relaxed) cho gọi xuống bất kỳ tầng nào bên dưới. Dự án Spring thường dùng kiểu chặt cho phần ghi; phần đọc đơn giản có thể đi controller → repository projection nếu nhóm đã thống nhất.
- **Service trả gì khi nhiều nơi cùng dùng**: trả DTO hoặc object nghiệp vụ của use case, không trả entity cho controller tự đi tiếp các quan hệ. Mỗi controller có thể map tiếp sang response riêng. Service cũng không cần interface riêng nếu chỉ có một cài đặt (bài Coupling, cohesion).
- **Service gọi service**: `OrderService` gọi `CustomerService` (qua API của module) thay vì `CustomerRepository` của module khác, để quy tắc của khách hàng nằm một chỗ. Hai service gọi nhau qua lại là [[circular-dependency|circular dependency]], dấu hiệu cần tách phần chung hoặc dùng event.
- **`@Transactional` đặt ở service, không ở controller**: đặt ở controller thì transaction bao cả việc của tầng web (gọi HTTP ra ngoài, mapping), và use case gọi từ Kafka listener hay batch job không có cùng ranh giới transaction. Nó cũng không cứu được lazy loading: proxy commit khi method controller trả về, rồi Spring MVC mới gọi Jackson ghi response. Đặt ở repository thì một use case gồm nhiều transaction nhỏ, lỗi giữa chừng để lại dữ liệu dở dang. Xem bài `@Transactional` cơ bản.
- **Open Session in View**: `spring.jpa.open-in-view` mặc định `true`, và Boot in cảnh báo lúc khởi động. Nó giữ `EntityManager` (và connection) tới khi response viết xong, nên lazy loading trong controller vẫn chạy, nhưng mỗi quan hệ được chạm tới là thêm query, và connection pool cạn nhanh hơn khi tải cao. Tắt nó, rồi map DTO bên trong transaction của service, dùng [[fetch-join|fetch join]] hoặc [[entity-graph|entity graph]] cho thứ cần tải.
- **Map DTO ở đâu**: service trả DTO (hoặc object nghiệp vụ không gắn JPA) là cách an toàn nhất, vì mapping chạy khi transaction còn mở. [[mapstruct|MapStruct]] sinh code mapping lúc biên dịch và báo field chưa map (`unmappedTargetPolicy = ERROR`); thư viện map bằng reflection lúc chạy (ModelMapper, `BeanUtils.copyProperties`) map nhầm hoặc bỏ sót mà không báo (ModelMapper chỉ báo khi gọi `validate()`, và chỉ phát hiện lúc chạy).
- **DTO dạng record**: `record UpdateProfileRequest(@NotBlank String displayName, @Email String email)` là bất biến, không có setter cho field thừa. Jackson 2.12+ hỗ trợ record.
- **Validate ở hai chỗ, hai mục đích**: Bean Validation ở controller cho định dạng (rỗng, email hợp lệ, độ dài); quy tắc nghiệp vụ (email chưa ai dùng, đơn chưa giao mới được huỷ) ở service hoặc trong entity, vì chúng cần dữ liệu và phải đúng cả khi được gọi từ Kafka listener hay batch job, không chỉ từ HTTP.
- **[[anemic-domain-model|Anemic domain model]]**: entity chỉ có getter/setter, mọi quy tắc nằm trong service. Với CRUD đơn giản thì không sao; khi quy tắc nhiều, logic bị lặp giữa các service. Đưa bất biến vào entity (`order.cancel()` tự kiểm tra trạng thái) là bước đầu tới DDD chiến thuật.
- **Kiểm tra bằng test**: [[archunit|ArchUnit]] có sẵn `layeredArchitecture()` để chặn controller gọi repository hay repository gọi service. [[spring-modulith|Spring Modulith]] kiểm tra ranh giới giữa các module tính năng và chặn truy cập vào package con nội bộ của module khác.
- **Khi phân lớp không còn đủ**: nghiệp vụ phụ thuộc trực tiếp vào JPA và Kafka thì khó test và khó đổi hạ tầng. Clean và Hexagonal Architecture đảo chiều phụ thuộc đó, xem bài riêng.
