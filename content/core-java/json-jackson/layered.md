## Quick

Jackson chuyển JSON sang object Java và ngược lại qua [[object-mapper|`ObjectMapper`]] (Jackson 3: `JsonMapper`). Phần lớn lỗi production không nằm ở cú pháp mà ở **mặc định**: trường lạ, trường thiếu, ngày giờ, số thập phân. **Tạo một mapper đã cấu hình rõ, dùng chung toàn ứng dụng; ghi tiền bằng `BigDecimal`/chuỗi; không bật default typing cho dữ liệu bên ngoài.** Jackson 3 (Spring Boot 4) đổi nhiều mặc định so với Jackson 2.

## Interview

**Jackson 2 và 3**: Jackson 3 đổi package sang `tools.jackson` (annotation vẫn ở `com.fasterxml.jackson.annotation`), mapper bất biến tạo qua builder, exception thành unchecked (`JacksonException` kế thừa `RuntimeException`), hỗ trợ `java.time` sẵn và ghi ngày giờ dạng ISO. Khác biệt hay gặp (đã chạy 2.22.4 và 3.2.4):

| Hành vi | Jackson 2 | Jackson 3 |
|---|---|---|
| Trường lạ trong JSON | ném `UnrecognizedPropertyException` | bỏ qua |
| `Instant` không cấu hình gì | ném lỗi, cần module `jsr310` | `"2026-03-15T02:00:00Z"` |
| `null` vào field primitive | gán 0 | ném lỗi |

Spring Boot (2.x, 3.x) cấu hình sẵn mapper Jackson 2 để bỏ qua trường lạ và ghi ngày dạng ISO, nên `new ObjectMapper()` tự tạo trong code cho hành vi khác bean của Spring.

**Trường thiếu**: cả hai bản gán giá trị mặc định (0, `null`) cho trường không có trong JSON, kể cả field primitive. Kết hợp với bỏ qua trường lạ, client gửi `amount_vnd` thay vì `amount` sẽ ra `amount = 0` mà không có lỗi nào. Chặn bằng kiểu wrapper + `@NotNull`, hoặc `FAIL_ON_MISSING_CREATOR_PROPERTIES` cho record/constructor.

**Số**: đọc số thập phân vào `Object`/`Map` ra `Double` (`12.50` thành `12.5`); bật `USE_BIG_DECIMAL_FOR_FLOATS`, hoặc khai báo field `BigDecimal`. Ghi `BigDecimal` dùng `toString()` nên `1E+2` lọt ra JSON; bật `WRITE_BIGDECIMAL_AS_PLAIN` (Jackson 3: `StreamWriteFeature`). Số nguyên lớn hơn 2^53 bị JavaScript làm tròn, gửi dạng chuỗi (bài Thiết kế REST API).

**[[polymorphic-deserialization|Polymorphic type]]**: JSON không mang kiểu Java. `@JsonTypeInfo(use = Id.NAME, property = "type")` + `@JsonSubTypes` ghi tên logic và chỉ nhận đúng các lớp khai báo. Khi đã có `@JsonTypeInfo`, Jackson 3 tự nhận lớp con của interface `sealed` mà không cần `@JsonSubTypes`; Jackson 2.22 thì không (đã chạy: `known type ids = []`); tên mặc định là tên class bỏ package (lớp lồng ra `Outer$Card`), nên khai báo `@JsonTypeName` rõ ràng.

**Mapper dùng chung**: `ObjectMapper` thread-safe sau khi cấu hình xong và cache serializer theo class; tạo mới mỗi lần mất cache.

Cách làm đúng: inject mapper của Spring hoặc một `JsonMapper` cấu hình tập trung; test hợp đồng JSON (snapshot) để thấy ngay khi nâng phiên bản Jackson đổi output.

## Deep

- **Đã chạy**: Jackson 2.22.4 ghi `Instant` sau khi thêm `JavaTimeModule` ra `1773540000.000000000` (giây thập phân, vì `WRITE_DATES_AS_TIMESTAMPS` bật mặc định), tắt cờ thì ra ISO. Jackson 3.2.4 ghi ISO ngay; cờ ngày giờ chuyển sang `DateTimeFeature`. Cả hai ghi `new BigDecimal("1E+2")` thành `1E+2`.
- **[[record-class|Record]]**: Jackson 2.12+ đọc ghi record qua canonical constructor, dùng tên component; nên dùng 2.15+ vì các bản trước có lỗi đặt tên property. Validate trong compact constructor chạy cả khi deserialize, nên lỗi dữ liệu thành lỗi 400 rõ ràng.
- **`@JsonInclude(NON_NULL)` và `NON_ABSENT`**: bỏ trường `null`/`Optional.empty()` khỏi output, làm JSON gọn nhưng client không phân biệt được "không có" với "bằng null". PATCH cần phân biệt hai trường hợp này (JSON Merge Patch ở bài Thiết kế REST API).
- **Enum**: giá trị lạ ném `InvalidFormatException`; `READ_UNKNOWN_ENUM_VALUES_USING_DEFAULT_VALUE` (Jackson 3: `EnumFeature`) kết hợp `@JsonEnumDefaultValue` cho client chịu được giá trị mới. Ghi enum bằng tên, đổi tên hằng là phá API.
- **Vòng tham chiếu**: entity JPA hai chiều (`Order` ↔ `OrderLine`) serialize ra `StackOverflowError` hoặc nạp lười hàng loạt; không serialize entity trực tiếp, dùng DTO/record. `@JsonManagedReference`/`@JsonIdentityInfo` chỉ là vá tạm.
- **Lớp con gadget**: default typing với `Object`, `Serializable` hay `Comparable` làm kiểu cơ sở cho phép JSON chọn bất kỳ class nào trên classpath. Từ Jackson 2.10, `activateDefaultTyping` bắt buộc truyền `PolymorphicTypeValidator` để giới hạn class được phép; `enableDefaultTyping` cũ không có giới hạn này: deprecated từ 2.10 nhưng vẫn còn trong 2.x (có ở 2.22.4), bị bỏ ở Jackson 3.
- **Generic và erasure**: `readValue(json, List.class)` ra `List<LinkedHashMap>`, ép sang `List<Order>` rồi lấy phần tử ném `ClassCastException`; dùng `new TypeReference<List<Order>>() {}` (bài Generics & type erasure). JSON kiểu `snake_case` thì đặt `PropertyNamingStrategies.SNAKE_CASE` thay vì `@JsonProperty` cho từng field.
- **Streaming**: `JsonParser`/`JsonGenerator` đọc ghi từng token, cho file vài GB mà không nạp hết vào bộ nhớ; `readTree` dựng cả cây `JsonNode` nên tốn bộ nhớ gấp nhiều lần kích thước JSON.
- **Hiệu năng**: đo trên JDK 27 với Jackson 2.22.4, 2.000 lần serialize với mapper mới mỗi lần mất 199 ms, dùng chung 1 ms. Lần serialize đầu tiên của mỗi class tốn thời gian dựng serializer (reflection); afterburner/blackbird module của Jackson 2 dùng sinh bytecode để giảm chi phí truy cập property. `ObjectMapper.copy()` (Jackson 2) hoặc `JsonMapper.rebuild()` (Jackson 3) để có biến thể cấu hình riêng mà không sửa mapper dùng chung.
- **Nâng Spring Boot 3 lên 4**: Jackson 3 là mặc định, đổi import `com.fasterxml.jackson.databind` sang `tools.jackson.databind`, `JsonProcessingException` (checked) sang `JacksonException` (unchecked), và kiểm lại mọi chỗ dựa vào mặc định cũ trong bảng trên.
