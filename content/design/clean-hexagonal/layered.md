## Quick

[[hexagonal-architecture|Hexagonal Architecture]] (port và adapter) đặt nghiệp vụ ở lõi, không phụ thuộc framework, database hay HTTP: lõi định nghĩa [[port|port]] (interface), hạ tầng là adapter cài đặt hoặc gọi port. [[clean-architecture|Clean Architecture]] phát biểu cùng ý bằng [[dependency-rule|dependency rule]]: **phụ thuộc trong code chỉ hướng vào trong**. Được: test nghiệp vụ không cần hạ tầng, đổi hạ tầng không chạm nghiệp vụ. Mất: thêm lớp và mapping, **quá tay với CRUD**.

## Interview

**Hai loại port**:
- *Driving* (primary, inbound): use case mà bên ngoài gọi vào, như `PlaceOrderUseCase`. REST controller, Kafka listener, job định kỳ đều là adapter gọi cùng một use case.
- *Driven* (secondary, outbound): thứ lõi cần từ bên ngoài, như `OrderRepository`, `PaymentGateway`, `OrderEventPublisher`. Adapter JPA, HTTP client, Kafka cài đặt chúng.

**Khác kiến trúc phân lớp ở đâu**: trong layered, service phụ thuộc repository JPA, nên nghiệp vụ biết về hạ tầng. Trong hexagonal, interface `OrderRepository` nằm trong lõi và nói ngôn ngữ nghiệp vụ; adapter JPA phụ thuộc vào lõi. Đây là [[dependency-inversion|Dependency Inversion]] áp cho cả kiến trúc.

**Cấu trúc package thường gặp**: `order/domain` (entity, value object, quy tắc), `order/application` (use case, port), `order/adapter/in/web`, `order/adapter/out/persistence`. Lõi không import `org.springframework.web`, `jakarta.persistence` hay `org.apache.kafka`.

**Test**: use case được test bằng fake trong bộ nhớ cho các driven port, chạy trong mili giây, không cần Spring hay Testcontainers. Adapter được test riêng với hạ tầng thật.

**Khi nào quá tay**:
- Service CRUD gần như không có quy tắc: mỗi trường đi qua ba lớp model và hai mapper mà không thêm giá trị.
- Interface cho mọi thứ, kể cả thứ không bao giờ có cài đặt thứ hai.
- Lõi trống trơn, logic thật nằm trong adapter: cấu trúc hexagonal nhưng domain vẫn [[anemic-domain-model|anemic]].

Câu trả lời tốt: áp hexagonal cho module có nghiệp vụ phức tạp và nhiều tích hợp, giữ layered đơn giản cho phần CRUD.

## Deep

- **Domain model và JPA entity**: tách hẳn thì lõi sạch nhưng phải map hai chiều, và mất [[dirty-checking|dirty checking]] (phải load entity rồi chép thay đổi). Dùng chung một class có annotation JPA thì đơn giản hơn, đổi lại lõi phụ thuộc `jakarta.persistence` và gặp các vấn đề của JPA (constructor không tham số, lazy proxy, `equals`). Nhiều nhóm chọn cách thực dụng: chấp nhận annotation JPA trong domain, nhưng không để `EntityManager` hay Spring Data lọt vào.
- **Transaction đặt ở đâu**: thực dụng nhất là `@Transactional` trên application service (use case). Bản thuần hơn bọc use case bằng một decorator transaction ở tầng cấu hình, để lõi không có annotation Spring. Ranh giới transaction vẫn là một use case.
- **Bean được tạo ở đâu**: muốn lõi không có `@Service`, khai báo use case bằng method `@Bean` trong class `@Configuration` ở module ứng dụng. Cái giá là thêm cấu hình tay; nhiều nhóm chấp nhận `@Service` trong application layer.
- **Port to hay nhỏ**: một port `OrderRepository` 15 method so với nhiều port nhỏ theo use case (`LoadOrderPort`, `SaveOrderPort`). Port nhỏ đúng [[interface-segregation|Interface Segregation]] và dễ fake, nhưng nhiều file hơn. Bắt đầu với một port mỗi aggregate (bài DDD chiến thuật), tách khi có use case chỉ cần một phần.
- **Dữ liệu đi qua ranh giới**: controller không truyền DTO web vào use case; adapter map request sang một command của use case (`PlaceOrderCommand`, record tự validate), và use case trả về output model riêng hoặc id, không trả entity để adapter tự đi tiếp. Mapper nằm ở adapter, vì adapter biết cả hai phía.
- **Lỗi đi qua ranh giới**: lõi ném exception nghiệp vụ (`InsufficientStockException`); adapter web map sang HTTP status bằng `@RestControllerAdvice` và [[problem-detail|`ProblemDetail`]] (Spring 6 / Boot 3). Lõi không biết tới status code.
- **Validate ở hai nơi**: adapter kiểm tra định dạng input (rỗng, sai kiểu); lõi giữ bất biến nghiệp vụ trong constructor hoặc method của entity, nên đúng với mọi adapter gọi vào.
- **Event ra ngoài**: lõi gọi port `OrderEventPublisher.orderPlaced(...)`; adapter có thể ghi vào bảng [[outbox]] trong cùng transaction rồi relay sang Kafka. Đổi broker chỉ đổi adapter.
- **Kiểm tra quy tắc tự động**: [[archunit|ArchUnit]] có `onionArchitecture()` (domain model, domain service, application service, adapter) để chặn lõi phụ thuộc vào adapter và chặn các adapter phụ thuộc lẫn nhau. Nó không tự chặn import framework; muốn vậy thêm quy tắc riêng: `noClasses().that().resideInAPackage("..domain..").should().dependOnClassesThat().resideInAnyPackage("jakarta.persistence..", "org.springframework..")`. Không có test này, quy tắc phụ thuộc thường bị phá trong vài tháng.
- **Clean, Onion, Hexagonal**: khác nhau chủ yếu ở tên và số vòng (Clean có entities, use cases, interface adapters, frameworks & drivers). Cùng một ý: phụ thuộc hướng vào nghiệp vụ. Khi phỏng vấn, nói được ý chung quan trọng hơn thuộc tên từng vòng.
- **Chuyển dần từ layered**: bắt đầu ở một use case quan trọng: đưa quy tắc vào entity, tạo port cho các phụ thuộc hạ tầng, giữ adapter cũ làm cài đặt. Không cần viết lại cả service một lần.
