## Quick

[[reflection|Reflection]] cho phép đọc cấu trúc class và gọi method, đọc field lúc chạy mà không biết trước lúc biên dịch; đó là nền của Spring, Hibernate, Jackson, JUnit. Annotation chỉ là metadata: **chỉ annotation có `@Retention(RUNTIME)` mới thấy được bằng reflection**, và luôn cần một bên (framework, processor) đọc nó thì nó mới có tác dụng. Dynamic proxy tạo object đứng chắn trước object thật để thêm hành vi; [[jdk-dynamic-proxy|JDK proxy]] chỉ làm được với interface, proxy theo class cần sinh lớp con ([[cglib|CGLIB]], ByteBuddy).

## Interview

**Reflection**: `Class.forName`, `getDeclaredMethods`, `Method.invoke`, `Field.get`. Giá phải trả: mất kiểm tra kiểu lúc biên dịch (lỗi thành exception lúc chạy), chậm hơn gọi trực tiếp (từ JDK 18, JEP 416 cài lại reflection bằng [[method-handle|method handle]] nên chênh lệch nhỏ đi), và bị [[strong-encapsulation|đóng gói chặt]] chặn khi vào nội bộ JDK. Ngoại lệ của method được gọi bị bọc trong `InvocationTargetException`; nguyên nhân thật ở `getCause()`.

**[[annotation-retention|Annotation retention]]**: `SOURCE` (chỉ compiler thấy, như `@Override`), `CLASS` (**mặc định**, có trong file `.class` nhưng JVM không đưa ra reflection), `RUNTIME`. Quên `@Retention(RUNTIME)` trên annotation tự viết là lý do kinh điển khiến aspect hay interceptor "không chạy".

**[[annotation-processor|Annotation processor]]** chạy trong javac, đọc annotation và sinh code mới (MapStruct, Dagger, Hibernate metamodel, Spring Boot configuration metadata); không tốn gì lúc chạy.

**JDK dynamic proxy**: `Proxy.newProxyInstance(loader, interfaces, handler)` sinh lúc chạy một class `$ProxyN` implement các interface đó; mọi lời gọi (kể cả `toString`, `equals`, `hashCode`) đi vào `InvocationHandler.invoke`. Proxy không phải lớp con của class thật nên ép kiểu sang class cài đặt ném `ClassCastException`.

**Proxy lớp con** (CGLIB, ByteBuddy): sinh lớp con override các method; không chặn được method `final`, `private`, `static`, và class `final`. Lời gọi bên trong object (`this.method()`) không đi qua proxy ở cả hai loại.

Bẫy hay gặp: `InvocationHandler` gọi `method.invoke(target, args)` mà không gỡ `InvocationTargetException`, nên exception nghiệp vụ biến thành `UndeclaredThrowableException`; cache `Method` không làm, tra mỗi lần gọi; dùng reflection để đọc field `private` của thư viện.

Cách làm đúng: reflection để ở tầng framework và hạ tầng, có cache; code nghiệp vụ dùng interface và đa hình. Annotation tự viết luôn khai báo `@Retention` và `@Target`.

## Deep

- **Đã chạy JDK 27**: annotation không ghi retention: `isAnnotationPresent` là `false`, có `RUNTIME` là `true`. Proxy có tên `$Proxy2`, `proxy instanceof RealPayment` là `false`, `toString()` cũng đi qua handler. Handler không gỡ exception: bên gọi nhận `UndeclaredThrowableException` với cause là `InvocationTargetException`. Gọi `invoke` sai kiểu tham số ném `IllegalArgumentException: argument type mismatch`.
- **Hiệu năng (đo thô, không JMH, 5 triệu lần gọi sau khi ấm máy)**: gọi trực tiếp 21–44 ms, `Method.invoke` 47–75 ms, `MethodHandle` 29–59 ms. Phần đắt thật là **tra cứu** (`getMethod`, `getDeclaredFields` tạo mảng và object mới mỗi lần); framework cache kết quả tra cứu theo class. Chênh lệch khoảng 1,5–2 lần, không phải hàng chục lần. `MethodHandle` lưu trong field `static final` mới được JIT inline gần như gọi trực tiếp (phép đo trên dùng biến local nên chưa thể hiện điều này).
- **Proxy và default method**: handler muốn chạy cài đặt `default` của interface thì gọi `InvocationHandler.invokeDefault(proxy, method, args)` (Java 16). Interface không public thì class proxy được sinh trong cùng package với interface.
- **Proxy và exception checked**: handler ném checked exception mà method interface không khai báo thì JDK bọc vào `UndeclaredThrowableException`. Đúng cách: `catch (InvocationTargetException e) { throw e.getCause(); }`.
- **Annotation và kế thừa**: `@Inherited` chỉ có tác dụng với annotation trên class, không áp dụng cho method hay interface. Spring dùng `AnnotatedElementUtils`/`MergedAnnotations` để tìm annotation trên interface, lớp cha, và meta-annotation (annotation trên annotation như `@RestController` chứa `@Controller`), thứ `Method.getAnnotation` không làm.
- **Đọc generic qua reflection**: `Method.getGenericReturnType()` trả `ParameterizedType` nên Spring biết `List<Order>`; đó là cơ sở của type token (bài Generics & type erasure).
- **Tên tham số**: reflection chỉ có `arg0`, `arg1` trừ khi biên dịch với `-parameters` (Spring Boot plugin bật sẵn). Spring 6.1 bỏ việc đọc tên tham số từ debug info, nên thiếu `-parameters` thì `@PathVariable` không ghi tên sẽ lỗi.
- **Sinh class lúc chạy**: CGLIB không còn được phát triển và không theo kịp class file mới; Spring giữ một bản fork trong `spring-core`, Mockito và Hibernate dùng ByteBuddy. Từ JDK 15, `MethodHandles.Lookup.defineHiddenClass` (JEP 371) là cách chuẩn để framework định nghĩa class tạm.
- **GraalVM native image** không hỗ trợ reflection và proxy tuỳ ý: phải khai báo trước (reflect-config, proxy-config) hoặc để Spring AOT sinh sẵn lúc build.
- **Bảo mật**: `setAccessible(true)` phá vỡ đóng gói; trong module có `opens` mới được. Code nhận tên class hay tên method từ input người dùng rồi gọi bằng reflection mở đường cho tấn công (cùng gốc với lỗ hổng deserialization).
