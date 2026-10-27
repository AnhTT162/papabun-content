## Quick

[[classpath|Classpath]] là danh sách jar và thư mục JVM tìm class, **theo thứ tự, lấy bản đầu tiên tìm thấy**. JVM không biết khái niệm phiên bản: hai jar cùng chứa `com.x.Foo` thì jar đứng trước thắng, bất kể cái nào mới hơn. Vì vậy xung đột dependency hiện ra **lúc chạy** (`NoSuchMethodError`, `NoClassDefFoundError`), không lúc biên dịch. Phòng bằng một phiên bản cho mỗi thư viện ([[dependency-mediation|chọn phiên bản]] ở bài Maven, Gradle & quản lý dependency), cấm class trùng giữa các jar, và [[shading]] có relocation khi buộc phải nhúng thư viện.

## Interview

**Ba lỗi lúc chạy và ý nghĩa**:

- `NoSuchMethodError`/`NoSuchFieldError`/`AbstractMethodError` (con của `LinkageError`): code biên dịch với phiên bản A, lúc chạy nạp phiên bản B thiếu hoặc khác chữ ký. Gần như luôn là xung đột phiên bản.
- `NoClassDefFoundError`: class có lúc biên dịch nhưng lúc chạy không nạp được (thiếu jar, scope `provided`/`optional` sai), hoặc static initializer đã từng ném lỗi.
- `ClassNotFoundException`: nạp động theo tên (`Class.forName`, driver JDBC, plugin) không thấy.

**Tìm class đến từ jar nào**: `java -verbose:class` (in `source: file:...jar` cho mỗi class nạp), hoặc `Foo.class.getProtectionDomain().getCodeSource().getLocation()`. `mvn dependency:tree` chỉ nói **artifact** nào có mặt, không thấy class trùng nằm trong hai artifact khác tên.

**Class trùng giữa các jar**: một thư viện tự nhúng bản sao của Guava, Protobuf, Jackson mà không đổi package; hai artifact khác tọa độ chứa cùng package (`javax.annotation` của `jsr250-api` và `jakarta.annotation-api` bản cũ). Maven không phát hiện vì nó chỉ so `groupId:artifactId`; Enforcer với `banDuplicateClasses` (extra-enforcer-rules) hoặc plugin duplicate-finder thì có.

**[[shading|Shading]]** gói thư viện vào jar của mình; **relocation** đổi package (`com.google.protobuf` thành `com.vendor.shaded.protobuf`) để không đụng bản của ứng dụng. Shading không relocation là nguồn xung đột, không phải lời giải.

**[[jpms|JPMS]]** (Java 9): `module-info.java` khai báo `requires`, `exports` (cho phép dùng public API ở cả lúc biên dịch lẫn lúc chạy), `opens` (cho phép reflection sâu). Module path kiểm tra lúc khởi động: thiếu module là lỗi ngay, [[split-package|split package]] (hai module cùng chứa một package) là lỗi. Jar thường đặt trên module path thành automatic module. Phần lớn ứng dụng Spring vẫn chạy trên classpath (unnamed module), nhưng vẫn chịu [[strong-encapsulation|đóng gói chặt]] của JDK.

Cách làm đúng: một BOM cho cả repo, CI chặn class trùng và phiên bản không hội tụ, thư viện nội bộ nhúng dependency thì relocation; khi gặp `LinkageError` thì tìm jar thật bằng `-verbose:class` trước khi đoán.

## Deep

- **Đã chạy JDK 27**: hai jar `money-util` 1.0 và 2.0 cùng trên classpath; đặt 2.0 trước thì chạy đúng, đặt 1.0 trước thì `NoSuchMethodError`. `-verbose:class` (cú pháp mới `-Xlog:class+load`) in `[0.015s][info][class,load] demo.MoneyFormat source: file:.../money-util-1.0.jar`. Static initializer ném lỗi: lần đầu `ExceptionInInitializerError`, lần sau `NoClassDefFoundError: Could not initialize class Cfg`. Xoá file class đã biên dịch: `NoClassDefFoundError: Dep`. Hai module cùng export `com.shop.util`: javac báo `module app reads package com.shop.util from both liba and libb`.
- **Thứ tự classpath khác nhau giữa các cách chạy**: IDE, `mvn exec`, Spring Boot fat jar (thứ tự cố định trong `BOOT-INF/classpath.idx`) và image Jib (mặc định wildcard `/app/libs/*`, thứ tự do filesystem; tuỳ chọn `expandClasspathDependencies` ghi classpath tường minh) có thể xếp jar khác nhau. Có class trùng là có lỗi "chỉ xảy ra trên môi trường X".
- **Spring Boot [[fat-jar|fat jar]]** giữ jar gốc trong `BOOT-INF/lib` và nạp bằng [[classloader]] riêng, nên class trùng vẫn là class trùng; chi tiết classloader ở bài ClassLoader.
- **`provided` mà runtime không có**: build ra war chạy trên Tomcat ngoài thì đúng, chuyển sang fat jar nhúng Tomcat mà còn để `provided` cho thư viện không phải container API thì `NoClassDefFoundError` lúc chạm tới.
- **Shading có giá**: jar to, mỗi lỗ hổng trong thư viện bị nhúng phải đợi tác giả phát hành lại, công cụ quét dependency khó thấy bản bị relocation, và resource (`META-INF/services`) phải được gộp đúng (transformer `ServicesResourceTransformer`), nếu không `ServiceLoader` mất provider.
- **JPMS trong thực tế**: thư viện nên khai báo `Automatic-Module-Name` trong manifest để có tên module ổn định. `--add-opens`/`--add-exports` mở ngoại lệ (bài Java 17 → 21). `jlink` dựng runtime chỉ gồm module cần (image nhỏ hơn) nhưng yêu cầu mọi thứ là module thật hoặc tự xử lý automatic module.
- **Nhiều phiên bản cùng lúc**: classpath không chứa được hai bản của cùng class. Cần thật thì classloader cô lập (OSGi, plugin loader riêng, cách Elasticsearch và Jenkins nạp plugin) hoặc tách thành service riêng. Đây là lựa chọn kiến trúc, không phải cấu hình build.
- **Công cụ**: `jdeps` liệt kê phụ thuộc giữa jar và package, `jar --describe-module` xem module, `jcmd <pid> VM.classloaders` xem cây classloader của process đang chạy. Với JPMS, `ServiceLoader` dùng `provides ... with` và `uses` trong `module-info` thay cho `META-INF/services`.
- **Multi-release jar** (`META-INF/versions/17/...`) cho thư viện chứa bản class khác nhau theo phiên bản JDK; công cụ shading cũ có thể làm hỏng cấu trúc này.
- **`LinkageError` do hai classloader**: cùng một class nạp bởi hai classloader là hai kiểu khác nhau; `ClassCastException: com.x.Foo cannot be cast to com.x.Foo` là dấu hiệu, hay gặp với DevTools restart classloader của Spring Boot hoặc app server.
