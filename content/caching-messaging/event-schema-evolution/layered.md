## Quick

**Command** yêu cầu một việc (`ChargePayment`), có một nơi nhận và có thể bị từ chối. **Event** báo một việc **đã xảy ra** (`PaymentCharged`), đặt tên ở thì quá khứ, không ai từ chối được, và có thể có nhiều bên nghe. Event là **hợp đồng** giữa các đội: producer và consumer deploy vào những lúc khác nhau, và event cũ nằm lại trong topic nhiều ngày. Vì vậy mọi thay đổi schema phải **tương thích**. Dùng **[[schema-registry|schema registry]]** với Avro hay Protobuf để kiểm tra tương thích ngay khi đăng ký schema. Thay đổi phá vỡ thì tạo phiên bản hoặc topic mới.

## Interview

**[[event-carried-state|Event mang đủ dữ liệu]] hay chỉ báo hiệu**:
- Đủ dữ liệu (event-carried state transfer): consumer không phải gọi lại producer, chạy được khi producer chết. Đổi lại event to hơn, và schema là hợp đồng lớn hơn.
- Chỉ báo hiệu (`OrderUpdated{orderId}`): nhỏ, nhưng mọi consumer gọi API lấy chi tiết; tải dồn vào producer, và dữ liệu lấy về có thể mới hơn event.

**Envelope**: `eventId` (khử trùng), `type`, `version`, `occurredAt`, `aggregateId` (làm key để giữ thứ tự), `aggregateVersion` (bỏ event cũ hơn), correlation id và trace context.

**[[schema-compatibility|Tương thích]]** (theo Confluent Schema Registry):
- **BACKWARD** (mặc định): schema mới đọc được dữ liệu cũ. Được thêm trường có giá trị mặc định, xoá trường. **Nâng consumer trước.**
- **FORWARD**: schema cũ đọc được dữ liệu mới. Được thêm trường, xoá trường có mặc định. **Nâng producer trước.**
- **FULL**: cả hai; chỉ được thêm hoặc xoá trường có mặc định, nâng bên nào trước cũng được. Thêm `_TRANSITIVE` để kiểm tra với **mọi** phiên bản cũ, không chỉ phiên bản ngay trước; cần khi consumer có thể đọc lại event từ lâu.

**Quy tắc an toàn**: chỉ thêm trường tuỳ chọn có mặc định; không đổi tên, không đổi kiểu, không tái sử dụng tên hay số trường đã xoá. Consumer bỏ qua trường lạ ([[tolerant-reader|tolerant reader]]).

**Thay đổi phá vỡ**: topic mới (`orders.v2`), producer ghi cả hai trong giai đoạn chuyển, các consumer chuyển dần, rồi dừng topic cũ.

**Không lộ mô hình nội bộ**: event tích hợp nên là hợp đồng được thiết kế, không phải bản chụp bảng database (CDC thô); đổi cột là phá vỡ mọi consumer. Dùng [[cdc|CDC]] trên bảng [[outbox|outbox]] thay vì trên bảng nghiệp vụ.

## Deep

- **Schema registry hoạt động thế nào**:
  - Serializer đăng ký (hoặc tra) schema, nhận một **schema ID**; message mang byte đánh dấu, 4 byte schema ID, rồi payload. Deserializer lấy schema theo ID (có cache).
  - Registry kiểm tra tương thích khi đăng ký phiên bản mới. Tắt `auto.register.schemas` ở production và đăng ký từ CI, để schema sai bị chặn trước khi deploy chứ không phải lúc producer gửi. Khi đó serializer tra ID theo đúng schema của nó, khác một chút là lỗi "schema not found": đặt thêm `use.latest.version=true` và `normalize.schemas=true` theo khuyến nghị của Confluent.
  - Với Protobuf, payload còn có mảng message index sau schema ID. Confluent Platform 8.1.1+ có thể đưa schema ID vào header thay vì đầu payload.
  - Subject mặc định theo topic (`TopicNameStrategy`): một topic một kiểu event. Cần nhiều kiểu event trong một topic (để giữ thứ tự theo aggregate) thì dùng `RecordNameStrategy` hoặc `TopicRecordNameStrategy`, hoặc union/`oneOf`.
- **Avro**:
  - Đọc bằng **hai schema**: schema người ghi (theo ID) và schema người đọc; trường thiếu lấy giá trị mặc định, trường thừa bị bỏ. Thêm trường **không có mặc định** là phá vỡ BACKWARD.
  - Trường tuỳ chọn: `["null", "string"]` với `default: null`. Avro tới 1.11 yêu cầu default khớp nhánh đầu của union; 1.12 nới thành nhánh bất kỳ, nhưng vẫn nên đặt `null` đầu cho client và công cụ cũ.
  - Đổi tên bằng `aliases`, nhưng chỉ có tác dụng khi schema của người đọc khai báo alias, nên trên thực tế vẫn coi đổi tên là phá vỡ. Thêm giá trị enum: consumer cũ lỗi khi gặp giá trị lạ, trừ khi enum có `default` (Avro 1.9+).
  - Tiền: logical type `decimal` hoặc số nguyên đơn vị nhỏ nhất cộng mã tiền tệ; không dùng `double`.
- **Protobuf**:
  - Trên dây chỉ có **số trường**, không có tên: đổi tên không phá dạng nhị phân, nhưng phá ánh xạ JSON. Xoá trường thì đánh dấu `reserved` cả số và tên để không ai dùng lại.
  - proto3 không phân biệt "không gửi" với giá trị mặc định (0, chuỗi rỗng) trừ khi khai báo `optional`. `amount = 0` hay thiếu `amount`? Với editions (2023+), trường scalar mặc định có presence tường minh.
  - Confluent khuyên `BACKWARD_TRANSITIVE` cho Protobuf; thêm một message type mới vào schema không tương thích FORWARD.
  - Enum: giá trị đầu tiên phải là 0, nên đặt `..._UNSPECIFIED = 0`. Consumer cũ nhận giá trị mới thì thấy số không có tên; code `switch` cần nhánh mặc định.
- **JSON không có schema**:
  - Jackson 2.x: `new ObjectMapper()` mặc định **lỗi khi gặp trường lạ** (`FAIL_ON_UNKNOWN_PROPERTIES=true`); `ObjectMapper` của Spring Boot 3 và `JsonDeserializer` của Spring Kafka 3 thì tắt cấu hình này. Producer thêm một trường là consumer dùng mapper tự tạo bị vỡ.
  - Jackson 3 (Spring Boot 4) đổi mặc định thành `false`, nhưng bật `FAIL_ON_NULL_FOR_PRIMITIVES` và `FAIL_ON_TRAILING_TOKENS`: `null` cho trường `int` giờ là lỗi. Spring Kafka 4.0 thay `JsonDeserializer` bằng `JacksonJsonDeserializer`.
  - Không có kiểm tra tương thích tự động: dùng JSON Schema với registry, hoặc contract test giữa các đội (Pact, Spring Cloud Contract).
- **Thứ tự nâng cấp trong thực tế**: event được lưu lâu và đọc lại (retention dài, compacted topic, event sourcing) thì gần như cần `FULL_TRANSITIVE`, vì consumer mới phải đọc event của mọi phiên bản cũ, và consumer cũ có thể gặp event mới.
- **Event sourcing và upcasting**: event đã lưu không được sửa. Khi schema đổi, một **upcaster** chuyển event phiên bản cũ sang phiên bản mới lúc đọc (Axon có sẵn cơ chế này).
- **Thời gian và định danh**: `occurredAt` là thời điểm theo UTC (ISO-8601 có offset hoặc epoch millis), khác thời điểm publish; id dạng [[uuid-v7|UUID v7]] sắp xếp được theo thời gian.
- **Dữ liệu cá nhân trong event**:
  - Event giữ lâu và bị sao chép sang nhiều hệ thống; quyền được xoá theo GDPR hay quy định bảo vệ dữ liệu cá nhân của Việt Nam khó thực hiện.
  - Giữ PII ngoài event (chỉ gửi id), hoặc mã hoá trường PII bằng khoá riêng cho mỗi người và xoá khoá khi cần xoá dữ liệu (crypto-shredding).
- **Event lớn**: đặt payload ở object storage, event chỉ mang đường dẫn và checksum (claim check). Giới hạn mặc định của message Kafka khoảng 1MB.
- **Ownership**: mỗi topic có một đội sở hữu schema; thay đổi đi qua review như thay đổi API, kèm tài liệu (AsyncAPI) và danh sách consumer.
