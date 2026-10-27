## Quick

[[java-serialization|Java serialization]] (`Serializable`, `ObjectOutputStream`) ghi cả tên class lẫn dữ liệu, và khi đọc thì **dữ liệu quyết định class nào được tạo**, đồng thời chạy các hook như `readObject`. Vì vậy deserialize dữ liệu không tin cậy có thể dẫn tới [[remote-code-execution|chạy code từ xa]]. **Không dùng Java serialization cho dữ liệu đi qua biên giới tin cậy; dùng JSON/Protobuf với schema rõ ràng, và nếu buộc phải dùng thì đặt [[object-input-filter|`ObjectInputFilter`]] chỉ cho phép đúng các class cần.**

## Interview

**Cơ chế**: `writeObject` duyệt đồ thị object, ghi tên class, [[serial-version-uid|`serialVersionUID`]] và giá trị field (trừ `transient` và `static`). `readObject` đọc tên class, nạp class đó, tạo object **không gọi constructor** của class (chỉ gọi constructor không tham số của lớp cha đầu tiên không `Serializable`), gán field, rồi gọi các hook `readObject`, `readResolve` nếu class có.

**`serialVersionUID`**: không khai báo thì JVM tính từ cấu trúc class (field, method, interface). Thêm một field là đổi UID, và dữ liệu cũ đọc ra `InvalidClassException: local class incompatible`. Hay gặp nhất với session HTTP hoặc cache Redis dùng Java serialization (`JdkSerializationRedisSerializer` mặc định của Spring Data Redis): deploy bản mới là mọi session cũ hỏng.

**Lỗ hổng**: vì luồng byte chọn class và hook chạy tự động, kẻ tấn công gửi một đồ thị object gồm các class có sẵn trên classpath mà `readObject` của chúng gọi `hashCode`, `compare`, `invoke` của nhau, cuối cùng tới `Runtime.exec`: đó là [[gadget-chain|gadget chain]]. Vụ nổi tiếng: Apache Commons Collections (2015) với `InvokerTransformer`, ảnh hưởng WebLogic, JBoss, Jenkins.

**Phòng thủ** (thứ tự ưu tiên):

1. Không deserialize Java object từ nguồn không tin cậy; dùng định dạng dữ liệu thuần (JSON, Protobuf) ánh xạ vào DTO cố định.
2. Nếu bắt buộc: `ObjectInputFilter` (JEP 290, Java 9 và backport 8u121) với allowlist class, giới hạn độ sâu, số phần tử mảng, số byte; Java 17 có filter theo ngữ cảnh (JEP 415).
3. Gỡ thư viện có gadget đã biết, nâng phiên bản, quét dependency.

**Cùng lớp lỗi ở định dạng khác**: Jackson [[default-typing|default typing]] (bài JSON & Jackson), SnakeYAML `new Yaml()` trước 2.0 cho tạo class bất kỳ qua global tag (CVE-2022-1471; 2.0 từ chối global tag mặc định), XStream trước 1.4.18, `XMLDecoder`. Quy tắc chung: định dạng nào cho dữ liệu chọn class Java là nguy hiểm.

## Deep

- **Đã chạy JDK 27 (lab)**: class không khai báo UID, ghi object rồi thêm field `voucher` và đọc lại: `InvalidClassException: CartSession; local class incompatible: stream classdesc serialVersionUID = 5240751688771244621, local class serialVersionUID = -265360969532042105`. Một class giả lập gadget có `readObject` in thông báo: thông báo in ra **trước** khi dòng ép kiểu `(String)` ném `ClassCastException`. Filter `java.util.HashMap;java.lang.String;!*` chặn với `filter status: REJECTED`.
- **Khai báo `serialVersionUID` cố định** giữ tương thích khi thêm field (field mới nhận giá trị mặc định, field bị xoá trong dữ liệu bị bỏ qua), nhưng không cứu được khi đổi kiểu field hay đổi cây kế thừa. Đổi tên class hay package thì không đọc được dù cùng UID.
- **Filter toàn JVM**: `-Djdk.serialFilter=...` hoặc file `java.security`; RMI có filter riêng. Filter allowlist an toàn hơn blocklist, vì gadget mới xuất hiện liên tục.
- **Record được deserialize qua canonical constructor**, nên validate trong compact constructor vẫn chạy; class thường thì không, phải tự kiểm trong `readObject` (Effective Java: viết `readObject` phòng thủ, chép lại field mutable).
- **Singleton và enum**: deserialization tạo instance mới trừ khi có `readResolve`; enum thì JVM tự đảm bảo (bài Creational patterns).
- **Spring Data Redis**: thay serializer mặc định bằng serializer JSON gắn với DTO cố định (như lab). `GenericJackson2JsonRedisSerializer` ghi tên class (`@class`) bằng default typing, nên chỉ dùng khi giới hạn được class cho phép, nếu không là lặp lại lỗi của Java serialization.
- **Giao thức dùng Java serialization ngầm**: RMI, JMX qua RMI, JMS `ObjectMessage`, Hazelcast/Ehcache cũ, session replication của Tomcat, Spring HttpInvoker (đã bị gỡ ở Spring 6). Port JMX/RMI mở ra mạng là bề mặt tấn công. Cùng lớp lỗi "dữ liệu chọn class" nhưng không qua `ObjectInputStream`: ActiveMQ OpenWire (CVE-2023-46604, RCE năm 2023).
- **Phát hiện**: luồng Java serialization bắt đầu bằng byte `AC ED 00 05`, base64 là `rO0AB...`; thấy chuỗi này trong cookie, tham số hay message là dấu hiệu. Tìm `ObjectInputStream`/`readObject` trong code bằng SAST, và bật JFR event `jdk.Deserialization` (JDK 17+) để biết class nào đang được deserialize ở production. Gắn filter cho một luồng: `in.setObjectInputFilter(ObjectInputFilter.Config.createFilter("com.shop.dto.*;java.util.*;!*"));`.
- **XXE** là họ hàng ở XML: parser mặc định của JDK xử lý external entity, có thể đọc file trên server; tắt DTD (`disallow-doctype-decl`) khi parse XML không tin cậy.
- **Tương lai**: trong OpenJDK đang có thảo luận về serialization dựa trên constructor và record thay cho cơ chế hiện tại; chưa có JEP hay mốc thời gian, chưa có trong JDK 27. Không nên thiết kế hệ thống mới dựa vào Java serialization.
